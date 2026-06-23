import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import os
import subprocess
import sys
import json
import base64
from datetime import datetime
import io
import plotly.express as px
import plotly.graph_objects as go
from src.web.rag_chat import esegui_query_rag_core

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(
    page_title="Albo Pretorio Intelligence - Piattaforma Audit", 
    page_icon="🏛️", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS PERSONALIZZATO (v2.0) ---
st.markdown("""
    <style>
    .main-header { font-size: 2.5rem; color: #1E3A8A; font-weight: bold; margin-bottom: 0.5rem; }
    .sub-header { font-size: 1.2rem; color: #4B5563; margin-bottom: 2rem; }
    .kpi-card { 
        background-color: #ffffff; 
        padding: 25px; 
        border-radius: 12px; 
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        border-left: 5px solid #1E3A8A; 
        margin-bottom: 20px;
    }
    .kpi-value { font-size: 2rem; font-weight: bold; color: #111827; }
    .kpi-label { font-size: 0.9rem; color: #6B7280; text-transform: uppercase; letter-spacing: 0.05em; }
    .status-active { color: #10B981; font-weight: bold; }
    .status-low { color: #EF4444; font-weight: bold; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; font-weight: 600; }
    </style>
""", unsafe_allow_html=True)

# --- UTILITIES ---
def get_pdf_display(pdf_path):
    """Genera un iframe per visualizzare il PDF in Streamlit."""
    try:
        with open(pdf_path, "rb") as f:
            base64_pdf = base64.b64encode(f.read()).decode('utf-8')
        return f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf"></iframe>'
    except Exception as e:
        return f"Impossibile caricare il PDF: {e}"

@st.cache_data
def get_enti():
    data_dir = Path("data")
    if data_dir.exists():
        return sorted([d.name for d in data_dir.iterdir() if d.is_dir()])
    return ["avella"]

# --- SIDEBAR DI CONTROLLO ---
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/0/03/Repubblica_Italiana_emblem.svg/512px-Repubblica_Italiana_emblem.svg.png", width=80)
st.sidebar.title("RegTech Intelligence")

enti_disponibili = get_enti()
ente_selezionato = st.sidebar.selectbox("🏛️ Ente in Analisi", enti_disponibili)

# Centralizzazione Percorsi
BASE_PATH = Path(f"data/{ente_selezionato}/albo_download")
if not BASE_PATH.exists(): BASE_PATH = Path("albo_download")

st.sidebar.markdown("---")
menu = st.sidebar.radio("📌 Navigazione:", [
    "📊 Dashboard Direzionale",
    "🔎 Esploratore Atti (Audit)",
    "💬 Assistente RAG (IA)",
    "🕸️ Knowledge Graph Relazionale",
    "🕵️ Analisi Antifrode & Anomalie",
    "📈 Benchmarking Comuni",
    "🕵️ Audit HITL & Validazione",
    "⚙️ Intelligence & Manutenzione"
])

st.sidebar.markdown("---")
st.sidebar.subheader("🎯 Focus Dominio")
focus_domain = st.sidebar.radio(
    "Filtra ambito di analisi:", 
    ["📊 Tutti gli Atti", "💰 Solo Contabilità & Appalti", "👥 Solo Competenze Personale"],
    help="Selezionando Contabilità, l'intero sistema escluderà gli atti non rilevanti per l'audit finanziario."
)

# --- CARICAMENTO E PRE-PROCESSING DATI ---
@st.cache_data
def load_and_clean_data(base_path):
    csv_path = base_path / "allegati_parsed.csv"
    if not csv_path.exists(): return pd.DataFrame()
    
    df = pd.read_csv(csv_path)
    
    # 1. Normalizzazione Date
    df['data_parsed'] = pd.to_datetime(df['data_atto'], format='%d/%m/%Y', errors='coerce')
    
    # 2. Normalizzazione Importi
    importo_col = 'importo_xai' if 'importo_xai' in df.columns else 'importo_max'
    df['importo_clean'] = pd.to_numeric(df[importo_col], errors='coerce').fillna(0)
    
    # 3. Normalizzazione Confidenza
    def parse_conf(val):
        if pd.isna(val): return 0.40
        v_str = str(val).lower()
        if v_str == 'high': return 0.95
        if v_str == 'ml_predicted': return 0.85
        if v_str == 'ambiguous': return 0.50
        if v_str == 'human_reviewed': return 1.0
        try: return float(val)
        except ValueError: return 0.40
        
    df['conf_numeric'] = df['classification_confidence'].apply(parse_conf)
    
    # 4. Arricchimento Mese/Anno per Time Series
    df['anno_mese'] = df['data_parsed'].dt.to_period('M').astype(str)
    
    return df

df_all = load_and_clean_data(BASE_PATH)

if focus_domain == "💰 Solo Contabilità & Appalti":
    df_all = df_all[df_all.get('accounting_relevant', False) == True].copy()
elif focus_domain == "👥 Solo Competenze Personale":
    df_all = df_all[df_all.get('is_personnel_competence_relevant', False) == True].copy()

if df_all.empty:
    st.error(f"❌ Database non trovato per {ente_selezionato}.")
    st.stop()

# Dataset Certificato (Filtro Forense > 0.85)
df_certified = df_all[
    (df_all['conf_numeric'] >= 0.85) | (df_all['classification_confidence'] == 'ml_predicted')
].copy()

# ==========================================
# 1. MODULO: DASHBOARD DIREZIONALE
# ==========================================
if menu == "📊 Dashboard Direzionale":
    st.markdown('<p class="main-header">📊 Dashboard Direzionale Intelligence</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="sub-header">Analisi Forense degli Atti per il Comune di {ente_selezionato.upper()}</p>', unsafe_allow_html=True)
    
    # --- KPI TOP ROW ---
    c1, c2, c3, c4 = st.columns(4)
    
    spesa_totale = df_certified['importo_clean'].sum()
    spesa_outliers = df_certified[df_certified['importo_clean'] > 1000000]['importo_clean'].sum()
    
    c1.markdown(f"""<div class="kpi-card"><div class="kpi-label">Spesa Certificata</div><div class="kpi-value">€ {spesa_totale:,.2f}</div></div>""", unsafe_allow_html=True)
    c2.markdown(f"""<div class="kpi-card"><div class="kpi-label">Atti Analizzati</div><div class="kpi-value">{len(df_all)}</div></div>""", unsafe_allow_html=True)
    c3.markdown(f"""<div class="kpi-card"><div class="kpi-label">Fornitori Unici</div><div class="kpi-value">{df_certified['piva_beneficiario'].nunique()}</div></div>""", unsafe_allow_html=True)
    
    conf_media = df_all['conf_numeric'].mean()
    status_cls = "status-active" if conf_media > 0.8 else "status-low"
    c4.markdown(f"""<div class="kpi-card"><div class="kpi-label">Indice Veridicità</div><div class="kpi-value {status_cls}">{conf_media:.1%}</div></div>""", unsafe_allow_html=True)

    st.markdown("---")
    
    # --- GRAPHS ---
    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        st.subheader("📈 Trend Temporale della Spesa")
        df_trend = df_certified.groupby('anno_mese')['importo_clean'].sum().reset_index()
        fig_trend = px.line(df_trend, x='anno_mese', y='importo_clean', markers=True, 
                            title='Spesa Mensile Certificata', labels={'importo_clean': 'Euro', 'anno_mese': 'Mese'})
        fig_trend.update_layout(height=400)
        st.plotly_chart(fig_trend, use_container_width=True)
        
    with col_right:
        st.subheader("📁 Distribuzione Categorie")
        df_cat = df_all['category'].value_counts().reset_index()
        fig_pie = px.pie(df_cat, names='category', values='count', hole=0.4)
        fig_pie.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("---")
    
    c_ben, c_rup, c_cap = st.columns(3)
    with c_ben:
        st.subheader("🏆 Top 5 Beneficiari (Volume)")
        top_ben = df_certified[df_certified['beneficiario'] != 'NON IDENTIFICATO'].groupby('beneficiario')['importo_clean'].sum().sort_values(ascending=False).head(5)
        st.bar_chart(top_ben)
    with c_rup:
        st.subheader("👤 Top 5 RUP (N. Atti)")
        # Pulizia RUP per il grafico, in attesa che la pipeline venga ri-eseguita
        df_rup_chart = df_certified.copy()
        df_rup_chart['responsabile_clean'] = df_rup_chart['responsabile'].replace('DI ADOTTARE GLI ATTI', np.nan)
        top_rup = df_rup_chart.dropna(subset=['responsabile_clean'])['responsabile_clean'].value_counts().head(5)
        st.bar_chart(top_rup)
    with c_cap:
        st.subheader("💰 Top 5 Capitoli di Spesa")
        df_capitoli = df_certified[df_certified['capitolo'].notna() & (df_certified['capitolo'] != 'NON IDENTIFICATO')].copy()
        if not df_capitoli.empty:
            df_capitoli['capitolo_str'] = df_capitoli['capitolo'].astype(str)
            top_cap = df_capitoli.groupby('capitolo_str')['importo_clean'].sum().sort_values(ascending=False).head(5)
            st.bar_chart(top_cap)
        else:
            st.write("Nessun dato sui capitoli di spesa disponibile.")

# ==========================================
# 2. MODULO: ESPLORATORE ATTI (DATA EXPLORER)
# ==========================================
elif menu == "🔎 Esploratore Atti (Audit)":
    st.markdown('<p class="main-header">🔎 Data Explorer Avanzato</p>', unsafe_allow_html=True)
    
    # Filtri Dinamici
    with st.expander("🛠️ Filtri di Audit", expanded=True):
        f1, f2, f3 = st.columns(3)
        with f1:
            q_search = st.text_input("Cerca per Oggetto, Fornitore o CIG:")
        with f2:
            sel_cat = st.multiselect("Filtra per Categoria:", df_all['category'].unique())
        with f3:
            min_amt, max_amt = st.slider("Range Importo (€):", 0, int(df_all['importo_clean'].max()), (0, 100000))
            
    # Applicazione Filtri
    df_filtered = df_all.copy()
    if q_search:
        df_filtered = df_filtered[
            df_filtered['oggetto'].str.contains(q_search, case=False, na=False) |
            df_filtered['beneficiario'].str.contains(q_search, case=False, na=False) |
            df_filtered['cig'].str.contains(q_search, case=False, na=False)
        ]
    if sel_cat:
        df_filtered = df_filtered[df_filtered['category'].isin(sel_cat)]
    
    df_filtered = df_filtered[(df_filtered['importo_clean'] >= min_amt) & (df_filtered['importo_clean'] <= max_amt)]

    st.markdown(f"Trovati **{len(df_filtered)}** atti corrispondenti.")
    
    # Tabella Interattiva
    cols_to_show = ['data_atto', 'doc_type', 'category', 'oggetto', 'beneficiario', 'importo_clean', 'cig', 'responsabile']
    st.dataframe(df_filtered[cols_to_show], use_container_width=True)
    
    if st.button("📥 Esporta Selezione in Excel"):
        output_excel = f"export_audit_{ente_selezionato}_{datetime.now().strftime('%Y%m%d')}.xlsx"
        df_filtered[cols_to_show].to_excel(output_excel, index=False)
        st.success(f"File esportato: {output_excel}")

# ==========================================
# 3. MODULO: ASSISTENTE RAG (INTEGRATED)
# ==========================================
elif menu == "💬 Assistente RAG (IA)":
    st.markdown('<p class="main-header">💬 Assistente Ispettivo Integrato</p>', unsafe_allow_html=True)
    st.info(f"L'intelligenza artificiale è connessa al corpus di **{ente_selezionato.upper()}**.")

    filter_rag = st.sidebar.radio(
        "Filtro di ricerca:",
        ["Nessuno", "Solo Contabilità & Appalti", "Solo Competenze Personale"],
        index=1
    )
    only_accounting = filter_rag == "Solo Contabilità & Appalti"
    only_personnel = filter_rag == "Solo Competenze Personale"

    chat_key = f"messages_{ente_selezionato}"
    if chat_key not in st.session_state:
        st.session_state[chat_key] = []

    for msg in st.session_state[chat_key]:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])

    if prompt := st.chat_input("Fai una domanda ispettiva (es. Quali sono gli affidamenti sotto i 40k euro?)"):
        st.session_state[chat_key].append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        
        with st.spinner("L'auditor virtuale sta analizzando i documenti..."):
            risposta = esegui_query_rag_core(query=prompt, ente=ente_selezionato, only_accounting=only_accounting, only_personnel_competence=only_personnel)
            
            with st.chat_message("assistant"):
                st.markdown(risposta)
            st.session_state[chat_key].append({"role": "assistant", "content": risposta})

# ==========================================
# 4. MODULO: KNOWLEDGE GRAPH
# ==========================================
elif menu == "🕸️ Knowledge Graph Relazionale":
    st.markdown('<p class="main-header">🕸️ Knowledge Graph Network</p>', unsafe_allow_html=True)
    
    graph_path = BASE_PATH / "report/knowledge_graph.html"
    if graph_path.exists():
        with open(graph_path, 'r', encoding='utf-8') as f:
            st.components.v1.html(f.read(), height=800, scrolling=True)
    else:
        st.error("Grafo non trovato. Generalo nella sezione Manutenzione.")

# ==========================================
# 5. MODULO: ANTIFRODE & BENCHMARKING
# ==========================================
elif menu == "🕵️ Analisi Antifrode & Anomalie":
    st.markdown('<p class="main-header">🕵️ Investigazione Antifrode</p>', unsafe_allow_html=True)
    
    # Mostriamo il report generato
    alert_path = BASE_PATH / "report/alert_antifrode.md"
    if alert_path.exists():
        with open(alert_path, 'r', encoding='utf-8') as f:
            st.markdown(f.read())
            
    st.markdown("---")
    st.subheader("🚨 Radar Anomalie Dinamico")
    c1, c2 = st.columns(2)
    with c1:
        st.info("**Sindrome della Soglia**")
        borderline = df_certified[(df_certified['importo_clean'] >= 39000) & (df_certified['importo_clean'] < 40000)]
        st.write(f"Atti borderline soglia 40k: {len(borderline)}")
        st.dataframe(borderline[['pdf_name', 'importo_clean', 'beneficiario']])
        
    with c2:
        st.info("**Rischio Frazionamento**")
        # Identifichiamo ditte con > 3 atti dallo stesso RUP nello stesso mese
        fraz_df = df_certified.groupby(['beneficiario', 'responsabile', 'anno_mese']).size().reset_index(name='count')
        suspicious = fraz_df[fraz_df['count'] > 2]
        st.write(f"Pattern sospetti rilevati: {len(suspicious)}")
        st.dataframe(suspicious)

elif menu == "📈 Benchmarking Comuni":
    st.markdown('<p class="main-header">📈 Benchmarking Multi-Comune</p>', unsafe_allow_html=True)
    
    # Carichiamo tutti gli enti per il confronto
    stats = []
    for ente in enti_disponibili:
        e_path = Path(f"data/{ente}/albo_download")
        if not e_path.exists(): e_path = Path("albo_download")
        d = load_and_clean_data(e_path)
        if not d.empty:
            stats.append({
                "Comune": ente.upper(),
                "Totale Spesa": d[d['conf_numeric'] >= 0.85]['importo_clean'].sum(),
                "N. Atti": len(d),
                "Confidenza Media": d['conf_numeric'].mean()
            })
    
    df_bench = pd.DataFrame(stats)
    st.subheader("Confronto Totale Spesa Certificata")
    fig_bench = px.bar(df_bench, x='Comune', y='Totale Spesa', color='Comune', text_auto='.2s')
    st.plotly_chart(fig_bench, use_container_width=True)
    
    st.dataframe(df_bench)

# ==========================================
# 7. MODULO: AUDIT HITL E VALIDAZIONE
# ==========================================
elif menu == "🕵️ Audit HITL & Validazione":
    st.markdown('<p class="main-header">🕵️ Audit HITL & Validazione (Active Learning)</p>', unsafe_allow_html=True)
    st.info("Correggi gli errori di estrazione o classifica i falsi positivi. Il sistema imparerà dai tuoi feedback.")
    
    col1, col2 = st.columns([1, 1])

    with col1:
        # Seleziona l'Atto
        df_valid = df_all.dropna(subset=['pdf_name', 'oggetto'])
        if not df_valid.empty:
            opzioni_atti = df_valid['pdf_name'].astype(str) + " - " + df_valid['oggetto'].astype(str).str[:100] + "..."
            atto_selezionato = st.selectbox("Seleziona l'Atto o la Determina da correggere:", opzioni_atti, key="hitl_selector")
            
            if atto_selezionato:
                nome_pdf = atto_selezionato.split(" - ")[0]
                riga_atto = df_all[df_all['pdf_name'] == nome_pdf].iloc[0]
                
                st.write(f"**Valori attuali per {nome_pdf}:**")
                st.write(f"- RUP: `{riga_atto.get('responsabile', 'N/A')}`")
                st.write(f"- Beneficiario: `{riga_atto.get('beneficiario', 'N/A')}`")
                st.write(f"- Categoria: `{riga_atto.get('category', 'N/A')}`")
                
                with st.form("feedback_form"):
                    nuovo_rup = st.text_input("Modifica RUP (Responsabile):", value=str(riga_atto.get('responsabile', '')))
                    nuovo_benef = st.text_input("Modifica Beneficiario:", value=str(riga_atto.get('beneficiario', '')))
                    
                    categorie_uniche = sorted(list(df_all['category'].dropna().unique()))
                    cat_corrente = str(riga_atto.get('category', ''))
                    idx_cat = categorie_uniche.index(cat_corrente) if cat_corrente in categorie_uniche else 0
                    nuova_cat = st.selectbox("Modifica Categoria:", categorie_uniche, index=idx_cat)
                    
                    falso_positivo = st.checkbox("Segnala questo Alert Antifrode come FALSO POSITIVO")
                    
                    submit = st.form_submit_button("Archivia Correzione")
                    
                    if submit:
                        report_dir = BASE_PATH / "report"
                        report_dir.mkdir(exist_ok=True, parents=True)
                        feedback_file = report_dir / "feedback_operatore.csv"
                        
                        nuova_riga = f'"{nome_pdf}","{nuovo_rup}","{nuovo_benef}","{nuova_cat}","{"SI" if falso_positivo else "NO"}","{datetime.now().isoformat()}"\n'
                        
                        if not feedback_file.exists():
                            feedback_file.write_text("pdf_name,responsabile,beneficiario,category,falso_positivo,timestamp\n", encoding="utf-8")
                            
                        with open(feedback_file, "a", encoding="utf-8") as f:
                            f.write(nuova_riga)
                        
                        st.success("✅ Correzione archiviata con successo! Esegui lo script di cleanup per applicarla.")

    with col2:
        if 'atto_selezionato' in locals() and atto_selezionato:
            st.subheader("📄 Visualizzatore Documento")
            nome_pdf = atto_selezionato.split(" - ")[0]
            riga_atto = df_all[df_all['pdf_name'] == nome_pdf].iloc[0]
            pdf_path = Path(riga_atto['pdf_path'])
            if pdf_path.exists():
                st.markdown(get_pdf_display(pdf_path), unsafe_allow_html=True)
            else:
                st.error(f"File PDF non trovato al percorso: {pdf_path}")

# ==========================================
# 6. MODULO: MANUTENZIONE
# ==========================================
elif menu == "⚙️ Intelligence & Manutenzione":
    st.markdown('<p class="main-header">⚙️ Gestione Sistema</p>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 Rigenera Tutti i Report (Grafo, Topologia, Anomalie)"):
            with st.spinner("Elaborazione massiva in corso..."):
                subprocess.run([sys.executable, "build_knowledge_graph.py", "--base", str(BASE_PATH)])
                subprocess.run([sys.executable, "analyze_topology.py", "--base", str(BASE_PATH)])
                subprocess.run([sys.executable, "detect_anomalies.py", "--base", str(BASE_PATH)])
                st.success("Tutti i report sono stati aggiornati!")
    
    with col2:
        st.markdown("**Sincronizza Feedback Umano**")
        uploaded_excel = st.file_uploader("Carica il file Excel revisionato (albo_analisi.xlsx)", type=['xlsx'])
        
        if st.button("🧼 Sincronizza Feedback (Active Learning)"):
            if uploaded_excel is not None:
                with st.spinner("Aggiornamento del database principale in corso..."):
                    csv_path = BASE_PATH / "allegati_parsed.csv"
                    if csv_path.exists():
                        df_main = pd.read_csv(csv_path)
                        updates = 0
                        
                        # 1. Sincronizzazione Categorie (Machine Learning Review)
                        try:
                            uploaded_excel.seek(0)
                            df_rev_ml = pd.read_excel(uploaded_excel, sheet_name="revisione_ml")
                            df_rev_ml_valid = df_rev_ml.dropna(subset=['categoria_corretta'])
                            for _, row in df_rev_ml_valid.iterrows():
                                mask = df_main['pdf_name'] == row['pdf_name']
                                df_main.loc[mask, 'category'] = row['categoria_corretta']
                                df_main.loc[mask, 'classification_confidence'] = 'human_reviewed'
                                updates += 1
                        except Exception:
                            pass
                            
                        # 2. Sincronizzazione Anomalie (Falsi Positivi)
                        try:
                            uploaded_excel.seek(0)
                            df_anomalies = pd.read_excel(uploaded_excel, sheet_name="anomalie_da_addestrare")
                            df_anomalies_valid = df_anomalies.dropna(subset=['conferma_anomalia'])
                            for _, row in df_anomalies_valid.iterrows():
                                if str(row['conferma_anomalia']).strip().upper() == 'NO':
                                    mask = df_main['pdf_name'] == row['pdf_name']
                                    df_main.loc[mask, 'anomalie'] = "Falso Positivo (Validato Umanamente)"
                                    updates += 1
                        except Exception:
                            pass
                            
                        if updates > 0:
                            df_main.to_csv(csv_path, index=False)
                            st.cache_data.clear() # Svuota la cache di Streamlit per ricaricare i grafici
                            st.success(f"✅ Sincronizzazione completata! Applicati {updates} aggiornamenti.")
                            st.rerun() # Ricarica l'interfaccia istantaneamente
                        else:
                            st.info("Nessuna correzione trovata nei fogli 'revisione_ml' o 'anomalie_da_addestrare'.")
                    else:
                        st.error("Database allegati_parsed.csv non trovato.")
            else:
                st.warning("⚠️ Carica prima il file Excel revisionato per procedere.")

    st.markdown("---")
    st.subheader("📥 Export Certificati")
    
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        REPORTLAB_AVAILABLE = True
    except ImportError:
        REPORTLAB_AVAILABLE = False

    if not REPORTLAB_AVAILABLE:
        st.warning("⚠️ Per generare il certificato PDF è necessario installare la libreria (esegui `pip install reportlab`).")
    else:
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(100, 800, f"CERTIFICATO DI AUDIT - COMUNE DI {ente_selezionato.upper()}")
        c.setFont("Helvetica", 12)
        c.drawString(100, 770, f"Data di generazione: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        c.drawString(100, 740, f"Totale Atti Analizzati: {len(df_all)}")
        c.drawString(100, 720, f"Atti Certificati (Veridicità > 85%): {len(df_certified)}")
        c.drawString(100, 700, f"Volume Spesa Certificata: Euro {df_certified['importo_clean'].sum():,.2f}")
        c.drawString(100, 650, "Sistema di Audit: Albo Pretorio Intelligence")
        c.save()
        buffer.seek(0)
        
        st.download_button(
            label="📜 Scarica Certificato di Audit (PDF)",
            data=buffer,
            file_name=f"Certificato_Audit_{ente_selezionato}.pdf",
            mime="application/pdf"
        )
    
    if st.button("📂 Scarica Linked Open Data (JSON-LD)"):
        lod_path = BASE_PATH / "report/albo_linked_data.jsonld"
        if lod_path.exists():
            with open(lod_path, "rb") as f:
                st.download_button("Download JSON-LD", f, file_name=f"LOD_{ente_selezionato}.jsonld")
        else:
            st.error("File LOD non trovato. Generalo nella pipeline.")
