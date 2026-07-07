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
from delibere_comunali.web.rag_chat import esegui_query_rag_core
import re
import warnings

# Suppressione avvisi specifici di PyTorch
warnings.filterwarnings("ignore", message=".*torch.classes.*")

# Definizione di PROJECT_ROOT
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

def _norm_pdf_key(v):
    if pd.isna(v):
        return ""
    s = str(v).strip().lower().replace("\\", "/")
    s = s.split("/")[-1]              # basename
    s = re.sub(r"\.pdf$", "", s)      # senza estensione
    s = re.sub(r"\s+", " ", s).strip()
    return s

try:
    import matplotlib  # noqa: F401
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

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
def load_and_clean_data(base_path):
    csv_path = base_path / "allegati_parsed.csv"
    if not csv_path.exists(): return pd.DataFrame()
    
    df = pd.read_csv(csv_path)

    # chiave documento robusta
    if 'pdf_name' in df.columns:
        df['pdf_key'] = df['pdf_name'].apply(_norm_pdf_key)
    elif 'pdf_path' in df.columns:
        df['pdf_key'] = df['pdf_path'].apply(_norm_pdf_key)
    else:
        df['pdf_key'] = ""
    
    # 1. Normalizzazione Date
    df['data_parsed'] = pd.to_datetime(df['data_atto'], format='%d/%m/%Y', errors='coerce')
    
    # 2. Normalizzazione Importi (robusta)
    candidate_cols = [c for c in ["importo_clean", "importo_xai", "importo_max", "importo", "importo_euro"] if c in df.columns]
    if candidate_cols:
        src = candidate_cols[0]
        numeric_try = pd.to_numeric(df[src], errors='coerce')
        if numeric_try.notna().any():
            df['importo_clean'] = numeric_try.fillna(0)
        else:
            normalized = (
                df[src].astype(str)
                .str.replace(r"[^\d,.\-]", "", regex=True)
                .str.replace(".", "", regex=False)
                .str.replace(",", ".", regex=False)
            )
            df['importo_clean'] = pd.to_numeric(normalized, errors='coerce').fillna(0)
    else:
        df['importo_clean'] = 0.0
    
    # 3. Normalizzazione Confidenza - AGGIORNATA PER RIFLETTERE I MIGLIORAMENTI
    def parse_conf(val):
        if pd.isna(val): return 0.40
        v_str = str(val).lower()
        if v_str == 'high': return 0.95
        if v_str == 'ml_predicted': return 0.85
        if v_str == 'ambiguous': return 0.10  # Ridotto da 0.50 a 0.10 per riflettere l'effettiva scarsa affidabilità
        if v_str == 'human_reviewed': return 1.0
        try: return float(val)
        except ValueError: return 0.40
        
    df['conf_numeric'] = df['classification_confidence'].apply(parse_conf)
    
    # 3.B. Calcolo confidenza combinata usando veridicità_score e solidità_globale (scala 0-100 convertita a 0-1)
    if 'veridicità_score' in df.columns and 'solidità_globale' in df.columns:
        # Convertiamo i punteggi da 0-100 a 0-1 e calcoliamo una media ponderata
        veridicita_scaled = pd.to_numeric(df['veridicità_score'], errors='coerce') / 100.0
        solidita_scaled = pd.to_numeric(df['solidità_globale'], errors='coerce') / 100.0
        
        # Media ponderata: veridicità 60%, solidità 40% (può essere aggiustata in base alle esigenze)
        combined_score = (veridicita_scaled * 0.6) + (solidita_scaled * 0.4)
        
        # Riempire i valori NaN con la confidenza basata su classification_confidence
        df['conf_combined'] = combined_score.fillna(df['conf_numeric'])
    else:
        df['conf_combined'] = df['conf_numeric']
    
    # 4. Arricchimento Mese/Anno per Time Series
    df['anno_mese'] = df['data_parsed'].dt.to_period('M').astype(str)
    # 5. Arricchimento opzionale con i dati del Motore Audit (se esiste)
    audit_path = base_path / "atti_audited.csv"
    if audit_path.exists():
        try:
            df_audit_raw = pd.read_csv(audit_path)

            if 'pdf_name' in df_audit_raw.columns:
                df_audit_raw['pdf_key'] = df_audit_raw['pdf_name'].apply(_norm_pdf_key)
            elif 'pdf_path' in df_audit_raw.columns:
                df_audit_raw['pdf_key'] = df_audit_raw['pdf_path'].apply(_norm_pdf_key)
            else:
                df_audit_raw['pdf_key'] = ""

            keep = [c for c in ['pdf_key', 'risk_score', 'anomalie_rilevate'] if c in df_audit_raw.columns]
            if 'pdf_key' in keep:
                df_audit = df_audit_raw[keep].copy()
                if 'risk_score' in df_audit.columns:
                    df_audit['risk_score'] = pd.to_numeric(df_audit['risk_score'], errors='coerce').fillna(0.0)
                # dedup per documento
                agg_map = {}
                if 'risk_score' in df_audit.columns:
                    agg_map['risk_score'] = 'max'
                if 'anomalie_rilevate' in df_audit.columns:
                    agg_map['anomalie_rilevate'] = lambda s: " | ".join(sorted(set([str(x) for x in s.dropna() if str(x).strip()])))
                df_audit = df_audit.groupby('pdf_key', as_index=False).agg(agg_map)

                df = pd.merge(df, df_audit, on='pdf_key', how='left', suffixes=('', '_audit'))
        except Exception as e:
            st.warning(f"⚠️ Attenzione: impossibile caricare il file atti_audited.csv: {str(e)[:100]}...")

    if 'risk_score' not in df.columns:
        df['risk_score'] = 0.0
    else:
        df['risk_score'] = pd.to_numeric(df['risk_score'], errors='coerce').fillna(0.0)

    if 'anomalie_rilevate' not in df.columns:
        df['anomalie_rilevate'] = ""
    else:
        df['anomalie_rilevate'] = df['anomalie_rilevate'].fillna("")

    return df

df_all = load_and_clean_data(BASE_PATH)

# fallback finale di sicurezza
if 'importo_clean' not in df_all.columns:
    df_all['importo_clean'] = 0.0

if focus_domain == "💰 Solo Contabilità & Appalti":
    df_all = df_all[df_all.get('accounting_relevant', False) == True].copy()
elif focus_domain == "👥 Solo Competenze Personale":
    df_all = df_all[df_all.get('is_personnel_competence_relevant', False) == True].copy()

if df_all.empty:
    st.error(f"❌ Database non trovato per {ente_selezionato}.")
    st.stop()
# --- FIX: Inizializzazione sicura delle colonne di confidenza ---
if 'conf_numeric' not in df_all.columns:
    if 'confidence' in df_all.columns:
        df_all['conf_numeric'] = pd.to_numeric(df_all['confidence'], errors='coerce').fillna(1.0)
    else:
        df_all['conf_numeric'] = 1.0

if 'classification_confidence' not in df_all.columns:
    df_all['classification_confidence'] = 'rules'

# ----------------------------------------------------------------
# Dataset Certificato (Filtro Forense > 0.85) - AGGIORNATO PER USARE conf_combined
df_certified = df_all[
    (df_all['conf_combined'] >= 0.85) | (df_all['classification_confidence'] == 'ml_predicted')
].copy()

# ==========================================
# 1. MODULO: DASHBOARD DIREZIONALE
# ==========================================
if menu == "📊 Dashboard Direzionale":
    st.markdown('<p class="main-header">📊 Dashboard Direzionale Intelligence</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="sub-header">Analisi Forense degli Atti per il Comune di {ente_selezionato.upper()}</p>', unsafe_allow_html=True)
    
    # --- KPI TOP ROW ---
    c1, c2, c3, c4 = st.columns(4)
    
    spesa_totale = pd.to_numeric(df_certified["importo_clean"], errors="coerce").fillna(0).sum()
    spesa_outliers = df_certified[df_certified['importo_clean'] > 1000000]['importo_clean'].sum()
    
    c1.markdown(f"""<div class="kpi-card"><div class="kpi-label">Spesa Certificata</div><div class="kpi-value">€ {spesa_totale:,.2f}</div></div>""", unsafe_allow_html=True)
    c2.markdown(f"""<div class="kpi-card"><div class="kpi-label">Atti Analizzati</div><div class="kpi-value">{len(df_all)}</div></div>""", unsafe_allow_html=True)
    c3.markdown(f"""<div class="kpi-card"><div class="kpi-label">Fornitori Unici</div><div class="kpi-value">{df_certified['piva_beneficiario'].nunique()}</div></div>""", unsafe_allow_html=True)
    
    # Calcolo aggiornato dell'indice di veridicità basato sui valori effettivi di veridicità_score
    if 'veridicità_score' in df_all.columns:
        # Calcoliamo la percentuale di documenti con veridicità_score sufficientemente alto
        # (es. sopra una soglia ragionevole, ad esempio 50 su 100)
        threshold_veridicita = 50
        alta_veridicita = (df_all['veridicità_score'] >= threshold_veridicita).sum()
        quota_certificata = alta_veridicita / len(df_all) if len(df_all) > 0 else 0.0
    else:
        # Fallback al vecchio metodo se non esiste veridicità_score
        quota_certificata = (len(df_certified) / len(df_all)) if len(df_all) else 0.0
    
    status_cls = "status-active" if quota_certificata >= 0.85 else "status-low"
    c4.markdown(
        f"""<div class="kpi-card"><div class="kpi-label">Indice Veridicità</div><div class="kpi-value {status_cls}">{quota_certificata:.1%}</div></div>""",
        unsafe_allow_html=True
    )

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
    # (Aggiunto 'risk_score' all'inizio della lista per vederlo subito)
    cols_to_show = ['risk_score', 'data_atto', 'doc_type', 'category', 'oggetto', 'beneficiario', 'importo_clean', 'cig', 'responsabile']
    available_cols = [c for c in cols_to_show if c in df_filtered.columns]
    table_df = df_filtered[available_cols]

    if MATPLOTLIB_AVAILABLE and 'risk_score' in available_cols:
        st.dataframe(
            table_df.style.background_gradient(subset=['risk_score'], cmap='Reds', vmin=0, vmax=100),
            use_container_width=True
        )
    else:
        st.dataframe(table_df, use_container_width=True)
    
    if st.button("📥 Esporta Selezione in Excel"):
        output_excel = f"export_audit_{ente_selezionato}_{datetime.now().strftime('%Y%m%d')}.xlsx"
        table_df.to_excel(output_excel, index=False)
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
            try:
                # tentativo completo (nuove versioni)
                risposta = esegui_query_rag_core(
                    query=prompt,
                    ente=ente_selezionato,
                    only_accounting=only_accounting,
                    only_personnel_competence=only_personnel
                )
            except TypeError:
                # fallback compatibilità (versioni chain che non accettano only_personnel_competence)
                risposta = esegui_query_rag_core(
                    query=prompt,
                    ente=ente_selezionato,
                    only_accounting=only_accounting
                )
            
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
    st.markdown('<p class="main-header">🕵️ Investigazione Antifrode Dinamica (Z-Score)</p>', unsafe_allow_html=True)
    st.info("Il motore di Audit calcola un Risk Score (0-100) basato su distribuzioni statistiche dinamiche, adattandosi alla spesa storica dell'ente.")
    
    # Carica il dataset arricchito dal nuovo motore
    audit_file_path = BASE_PATH / "atti_audited.csv"
    
    if audit_file_path.exists():
        try:
            df_audit = pd.read_csv(audit_file_path)
            
            # Verifica che il DataFrame non sia vuoto
            if df_audit.empty:
                st.warning("⚠️ Nessun dato disponibile nel file atti_audited.csv")
            else:
                # Filtriamo solo gli atti con anomalie (Risk Score > 0)
                df_anomalies = df_audit[df_audit['risk_score'] > 0].copy()
                
                if not df_anomalies.empty:
                    # --- KPI DIREZIONALI ---
                    c1, c2, c3 = st.columns(3)
                    c1.markdown(f"""<div class="kpi-card"><div class="kpi-label">Atti Sospetti (Hit Rate)</div><div class="kpi-value status-low">{len(df_anomalies)} / {len(df_audit)}</div></div>""", unsafe_allow_html=True)
                    c2.markdown(f"""<div class="kpi-card"><div class="kpi-label">Rischio Medio (Anomalie)</div><div class="kpi-value">{df_anomalies['risk_score'].mean():.1f}/100</div></div>""", unsafe_allow_html=True)
                    c3.markdown(f"""<div class="kpi-card"><div class="kpi-label">Valore Economico Sospetto</div><div class="kpi-value">€ {df_anomalies['importo_clean'].sum():,.2f}</div></div>""", unsafe_allow_html=True)
                    
                    st.markdown("---")
                    
                    # --- GRAFICI INTERATTIVI ---
                    col_chart1, col_chart2 = st.columns(2)
                    
                    with col_chart1:
                        st.subheader("📊 Distribuzione Tipologie Anomalie")
                        # Espandiamo le stringhe per contare le anomalie (es. "Smurfing | CIG Fantasma")
                        anomalie_list = (
                            df_anomalies['anomalie_rilevate']
                            .str.split(' | ', regex=False, expand=True)
                            .stack()
                            .value_counts()
                            .reset_index()
                        )
                        anomalie_list.columns = ['Tipo Anomalia', 'Frequenza']
                        
                        fig_anomalie = px.bar(anomalie_list, x='Frequenza', y='Tipo Anomalia', orientation='h', 
                                              color='Frequenza', color_continuous_scale='Reds')
                        fig_anomalie.update_layout(height=350, yaxis={'categoryorder':'total ascending'})
                        st.plotly_chart(fig_anomalie, use_container_width=True)
                        
                    with col_chart2:
                        st.subheader("🎯 Entità a Maggior Rischio")
                        # I 5 fornitori con i Risk Score più alti
                        top_risk_ben = df_anomalies.groupby('beneficiario_norm')['risk_score'].max().sort_values(ascending=False).head(5).reset_index()
                        fig_risk = px.bar(top_risk_ben, x='beneficiario_norm', y='risk_score', 
                                          title="Top 5 Beneficiari (Score Massimo)", color='risk_score', color_continuous_scale='Reds')
                        fig_risk.update_layout(height=350)
                        st.plotly_chart(fig_risk, use_container_width=True)
                        
                    st.markdown("---")
                    
                    # --- TABELLA ESPLORATIVA CON SLIDER ---
                    st.subheader("🔍 Esploratore Atti Sospetti")
                    
                    # Slider dinamico per filtrare il rumore
                    min_risk = st.slider("🎯 Filtra per Risk Score Minimo:", min_value=0, max_value=100, value=25, step=5)
                    df_filtered = df_anomalies[df_anomalies['risk_score'] >= min_risk].sort_values('risk_score', ascending=False)
                    
                    st.write(f"Mostrando **{len(df_filtered)}** atti che superano la soglia di rischio.")
                    
                    # Colonne da visualizzare
                    cols_to_display = ['risk_score', 'anomalie_rilevate', 'beneficiario_norm', 'importo_clean', 'data_atto', 'pdf_name', 'cig']
                    cols_to_display = [c for c in cols_to_display if c in df_filtered.columns]
                    table_anom = df_filtered[cols_to_display]

                    if MATPLOTLIB_AVAILABLE and 'risk_score' in cols_to_display:
                        st.dataframe(
                            table_anom.style.background_gradient(subset=['risk_score'], cmap='Reds', vmin=0, vmax=100)
                            .format({'importo_clean': '€ {:.2f}', 'risk_score': '{:.1f}'}),
                            use_container_width=True,
                            height=400
                        )
                    else:
                        st.dataframe(table_anom, use_container_width=True, height=400)
                    
                else:
                    st.success("🎉 Ottime notizie! Nessuna anomalia statistica è stata rilevata nel dataset.")
        except Exception as e:
            st.error(f"⚠️ Errore nel caricamento del file atti_audited.csv: {str(e)[:100]}...")
    else:
        st.warning("⚠️ File atti_audited.csv non trovato. Eseguire prima il modulo di audit.")

# ==========================================
# 6. MODULO: MANUTENZIONE
# ==========================================
elif menu == "⚙️ Intelligence & Manutenzione":
    st.markdown('<p class="main-header">⚙️ Gestione Sistema</p>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 Rigenera Tutti i Report (Grafo, Topologia, Audit)"):
            with st.spinner("Motori di elaborazione massiva in esecuzione..."):
                # Passiamo tutto tramite il nuovo orchestratore run.py
                try:
                    subprocess.run(
                        [sys.executable, str(PROJECT_ROOT / "run.py"), "build-kg", "--base", str(BASE_PATH)],
                        check=True,
                        cwd=str(PROJECT_ROOT),
                    )
                    subprocess.run(
                        [sys.executable, str(PROJECT_ROOT / "run.py"), "analyze-topology", "--base", str(BASE_PATH)],
                        check=True,
                        cwd=str(PROJECT_ROOT),
                    )
                    subprocess.run(
                        [sys.executable, str(PROJECT_ROOT / "run.py"), "audit", "--base", str(BASE_PATH)],
                        check=True,
                        cwd=str(PROJECT_ROOT),
                    )
                    st.success("✅ Tutti i report e i grafi sono stati aggiornati con successo!")
                    st.rerun() # Forza l'aggiornamento della UI per mostrare i nuovi dati
                except subprocess.CalledProcessError as e:
                    st.error(f"❌ Errore durante la rigenerazione. Codice: {e.returncode}")
    
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
            # ORDINAMENTO PER CRITICITÀ: i documenti più problematici devono apparire per primi
            # 1. Calcoliamo un punteggio di criticità combinato
            df_ordered = df_valid.copy()
            
            # Invertiamo i punteggi di confidenza (meno è la confidenza, maggiore è la criticità)
            if 'conf_combined' in df_ordered.columns:
                confidence_score = 1 - df_ordered['conf_combined']
            elif 'conf_numeric' in df_ordered.columns:
                confidence_score = 1 - df_ordered['conf_numeric']
            else:
                confidence_score = pd.Series([0.5] * len(df_ordered))
            
            # Invertiamo i punteggi di veridicità (meno è la veridicità, maggiore è la criticità)
            veridicita_score = 0
            if 'veridicità_score' in df_ordered.columns:
                veridicita_score = (100 - df_ordered['veridicità_score']) / 100.0
            
            # Invertiamo i punteggi di solidità (meno è la solidità, maggiore è la criticità)
            solidita_score = 0
            if 'solidità_globale' in df_ordered.columns:
                solidita_score = (100 - df_ordered['solidità_globale']) / 100.0
            
            # I risk score alti indicano maggiore criticità
            risk_score = 0
            if 'risk_score' in df_ordered.columns:
                risk_score = df_ordered['risk_score'] / 100.0  # Normalizziamo a 0-1
            
            # Calcoliamo il punteggio complessivo di criticità
            # Usiamo pesi per dare priorità ai diversi fattori
            df_ordered['criticality_score'] = (
                confidence_score * 0.4 +    # 40% per bassa confidenza
                veridicita_score * 0.2 +   # 20% per bassa veridicità
                solidita_score * 0.2 +     # 20% per bassa solidità
                risk_score * 0.2           # 20% per alto rischio
            )
            
            # Ordiniamo per punteggio di criticità decrescente
            df_ordered = df_ordered.sort_values(by='criticality_score', ascending=False)
            
            # Creiamo le opzioni per il selectbox, mostrando prima i documenti più critici
            opzioni_atti = df_ordered['pdf_name'].astype(str) + " - " + df_ordered['oggetto'].astype(str).str[:100] + "..."
            atto_selezionato = st.selectbox("Seleziona l'Atto o la Determina da correggere (ordinati per criticità):", opzioni_atti, key="hitl_selector")
            
            if atto_selezionato:
                nome_pdf = atto_selezionato.split(" - ")[0]
                # Cerchiamo la riga nel DataFrame ordinato
                riga_atto = df_ordered[df_ordered['pdf_name'] == nome_pdf].iloc[0]
                
                st.write(f"**Valori attuali per {nome_pdf}:**")
                st.write(f"- Tipo Doc: `{riga_atto.get('doc_type', 'N/A')}`")
                st.write(f"- Categoria: `{riga_atto.get('category', 'N/A')}`")
                st.write(f"- RUP: `{riga_atto.get('responsabile', 'N/A')}`")
                st.write(f"- Beneficiario: `{riga_atto.get('beneficiario', 'N/A')}`")
                st.write(f"- Importo Max: `{riga_atto.get('importo_max', 'N/A')}`")
                st.write(f"- CIG: `{riga_atto.get('cig', 'N/A')}`")
                st.write(f"- CUP: `{riga_atto.get('cup', 'N/A')}`")
                st.write(f"- Oggetto: `{riga_atto.get('oggetto', 'N/A')}`")
                st.write(f"- Data Atto: `{riga_atto.get('data_atto', 'N/A')}`")
                st.write(f"- Numero Atto: `{riga_atto.get('numero_atto', 'N/A')}`")
                st.write(f"- IBAN: `{riga_atto.get('iban', 'N/A')}`")
                st.write(f"- P.IVA Beneficiario: `{riga_atto.get('piva_beneficiario', 'N/A')}`")
                
                with st.form("feedback_form"):
                    # Parametri principali
                    nuova_cat = st.selectbox("Modifica Categoria:", 
                                           sorted(list(df_ordered['category'].dropna().unique())), 
                                           index=sorted(list(df_ordered['category'].dropna().unique())).index(str(riga_atto.get('category', ''))) if pd.notna(riga_atto.get('category', '')) and str(riga_atto.get('category', '')) in df_ordered['category'].dropna().unique() else 0)
                    
                    nuovo_tipo_doc = st.text_input("Modifica Tipo Documento:", value=str(riga_atto.get('doc_type', '')))
                    nuovo_rup = st.text_input("Modifica RUP (Responsabile):", value=str(riga_atto.get('responsabile', '')))
                    nuovo_benef = st.text_input("Modifica Beneficiario:", value=str(riga_atto.get('beneficiario', '')))
                    nuovo_piva = st.text_input("Modifica P.IVA Beneficiario:", value=str(riga_atto.get('piva_beneficiario', '')))
                    nuovo_importo = st.text_input("Modifica Importo Max:", value=str(riga_atto.get('importo_max', '')))
                    nuovo_cig = st.text_input("Modifica CIG:", value=str(riga_atto.get('cig', '')))
                    nuovo_cup = st.text_input("Modifica CUP:", value=str(riga_atto.get('cup', '')))
                    nuova_data = st.text_input("Modifica Data Atto (gg/mm/aaaa):", value=str(riga_atto.get('data_atto', '')))
                    nuovo_numero = st.text_input("Modifica Numero Atto:", value=str(riga_atto.get('numero_atto', '')))
                    nuovo_iban = st.text_input("Modifica IBAN:", value=str(riga_atto.get('iban', '')))
                    nuovo_oggetto = st.text_area("Modifica Oggetto:", value=str(riga_atto.get('oggetto', '')), height=100)
                    
                    falso_positivo = st.checkbox("Segnala questo Alert Antifrode come FALSO POSITIVO")
                    
                    submit = st.form_submit_button("Archivia Correzione")
                    
                    if submit:
                        report_dir = BASE_PATH / "report"
                        report_dir.mkdir(exist_ok=True, parents=True)
                        feedback_file = report_dir / "feedback_operatore.csv"
                        
                        nuova_riga = f'"{nome_pdf}","{nuovo_tipo_doc}","{nuovo_rup}","{nuovo_benef}","{nuovo_piva}","{nuovo_importo}","{nuovo_cig}","{nuovo_cup}","{nuova_data}","{nuovo_numero}","{nuovo_iban}","{nuovo_oggetto}","{nuova_cat}","{"SI" if falso_positivo else "NO"}","{datetime.now().isoformat()}"\n'
                        
                        if not feedback_file.exists():
                            feedback_file.write_text("pdf_name,doc_type,responsabile,beneficiario,piva_beneficiario,importo_max,cig,cup,data_atto,numero_atto,iban,oggetto,category,falso_positivo,timestamp\n", encoding="utf-8")
                            
                        with open(feedback_file, "a", encoding="utf-8") as f:
                            f.write(nuova_riga)
                        
                        st.success("✅ Correzione archiviata con successo! Esegui lo script di cleanup per applicarla.")

    with col2:
        if 'atto_selezionato' in locals() and atto_selezionato:
            st.subheader("📄 Visualizzatore Documento")
            nome_pdf = atto_selezionato.split(" - ")[0]
            # Cerchiamo la riga nel DataFrame ordinato
            riga_atto = df_ordered[df_ordered['pdf_name'] == nome_pdf].iloc[0]
            pdf_path = Path(riga_atto['pdf_path'])
            if pdf_path.exists():
                st.markdown(get_pdf_display(pdf_path), unsafe_allow_html=True)
            else:
                st.error(f"File PDF non trovato al percorso: {pdf_path}")

