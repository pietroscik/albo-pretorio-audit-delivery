import streamlit as st
import pandas as pd
from pathlib import Path
import json
import os

# Configurazione della pagina
st.set_page_config(page_title="Validazione Albo AI", layout="wide", page_icon="📊")

@st.cache_data
def get_available_enti():
    data_dir = Path("data")
    if not data_dir.exists(): return []
    # Trova le cartelle degli enti che contengono dati analizzati
    return [d.name for d in data_dir.iterdir() if d.is_dir() and (d / "albo_download" / "allegati_parsed.csv").exists()]

@st.cache_data
def load_data(ente):
    """Carica i dati dal CSV in modo efficiente."""
    csv_path = Path(f"data/{ente}/albo_download/allegati_parsed.csv")
    if not csv_path.exists():
        return None
    return pd.read_csv(csv_path)

@st.cache_data
def load_graph_metrics(ente):
    metrics_path = Path(f"data/{ente}/albo_download/report/graph_metrics.json")
    if metrics_path.exists():
        with open(metrics_path, "r") as f:
            return json.load(f)
    return None

st.title("📊 Dashboard Antifrode & Trasparenza AGID - Albo Pretorio")
st.markdown("Esplora i dati estratti con il framework olistico. Il sistema ora valida gli atti incrociando i Visti Contabili e costruisce un Knowledge Graph per l'analisi delle anomalie.")

enti = get_available_enti()
if not enti:
    st.error("Nessun dato trovato. Esegui prima `python run_pipeline.py --ente nome_ente`.")
    st.stop()

st.sidebar.header("Impostazioni")
selected_ente = st.sidebar.selectbox("Seleziona Ente da analizzare", enti)

df = load_data(selected_ente)

if df is None:
    st.error(f"Dati non trovati per l'ente {selected_ente}.")
    st.stop()

# --- SEZIONE KPI (Metriche in evidenza) ---
graph_metrics = load_graph_metrics(selected_ente)

st.subheader(f"📈 Indicatori di Trasparenza - Comune di {selected_ente.capitalize()}")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Totale Documenti Analizzati", len(df))
c2.metric("Beneficiari Identificati", df['beneficiario'].notna().sum())
c3.metric("Affidamenti D.Lgs 36/2023", df['tipo_procedura'].notna().sum())
c4.metric("Atti con Visto Contabile (Cross-Validati)", (df['veridicità_score'] > 50).sum() if 'veridicità_score' in df.columns else 0)

if graph_metrics:
    st.info(f"🧠 **Cervello Relazionale Attivo (Knowledge Graph):** Rilevati **{graph_metrics.get('nodes_count', 0)} nodi** (di cui {graph_metrics.get('rup_count', 0)} RUP e {graph_metrics.get('capitoli_count', 0)} Capitoli di Bilancio) connessi da **{graph_metrics.get('edges_count', 0)} sinapsi**.")

anomalies_count = df['anomalie'].notna().sum() if 'anomalie' in df.columns else 0
if anomalies_count > 0:
    st.warning(f"⚠️ Attenzione: Il motore NLP ha segnalato **{anomalies_count} documenti con criticità** (Dati poco solidi o anomalie in IBAN/P.IVA). Si consiglia revisione manuale.")

st.divider()

# --- SEZIONE TABELLA INTERATTIVA ---
st.subheader("🗂️ Vista Tabellare - Atti & Procedure")
st.markdown("Esplora il dataset filtrando per procedure o RUP.")

# Selezioniamo le colonne più utili per l'audit amministrativo
cols_to_show = ['pdf_name', 'doc_type', 'veridicità_score', 'cig', 'importo_max', 'beneficiario', 'tipo_procedura', 'capitolo', 'responsabile', 'anomalie']
available_cols = [c for c in cols_to_show if c in df.columns]

st.dataframe(df[available_cols].sort_values(by='veridicità_score', ascending=False, na_position='last'), use_container_width=True, hide_index=True)

st.divider()

# --- SEZIONE ISPEZIONE E VALIDAZIONE (HUMAN-IN-THE-LOOP) ---
st.subheader("🔍 Ispezione e Validazione Umana (Active Learning)")
st.markdown("Come operatore (Decisore Ultimo), puoi validare le estrazioni dell'AI o correggere i falsi positivi per addestrare meglio il sistema.")

# Inizializza il file dei feedback se non esiste
FEEDBACK_FILE = Path(f"data/{selected_ente}/albo_download/feedback_operatore.csv")

# Menu di selezione documento
selected_pdf = st.selectbox("Seleziona l'atto da ispezionare:", df['pdf_name'].tolist())

if selected_pdf:
    doc_data = df[df['pdf_name'] == selected_pdf].iloc[0]
    
    col_dati, col_validazione = st.columns([1, 1])
    
    with col_dati:
        score = doc_data.get('veridicità_score', 0)
        color = "🟢" if score >= 100 else ("🟡" if score > 0 else "🔴")
        st.success(f"**Risultato Estrazione Macchina** (Score di Veridicità: {color} {score}/100)")
        
        # Mostriamo i dati correnti estratti
        st.json({
            "Oggetto": doc_data.get('oggetto'),
            "Classificazione": f"{doc_data.get('category', 'Sconosciuta')} - {doc_data.get('doc_type', '')}",
            "Amministrazione (RUP/Ufficio)": doc_data.get('responsabile'),
            "Beneficiario": doc_data.get('beneficiario'),
            "P.IVA / IBAN": f"P.IVA: {doc_data.get('piva_beneficiario', 'N/D')} - IBAN: {doc_data.get('iban', 'N/D')}",
            "Tracciabilità (CIG/CUP)": f"CIG: {doc_data.get('cig', 'N/D')} - CUP: {doc_data.get('cup', 'N/D')}",
            "Importo Massimo": f"€ {doc_data.get('importo_max')}" if pd.notna(doc_data.get('importo_max')) else "Non rilevato",
        })
        
        if 'anomalie' in doc_data and pd.notna(doc_data['anomalie']):
            st.error(f"**Alert Antifrode/NLP:** {doc_data['anomalie']}")
            
        with st.expander("Vedi Testo Originale Completo (Lettura da disco)", expanded=True):
            # Lazy Loading: Leggiamo il file di testo completo dal disco solo quando serve
            pdf_stem = Path(selected_pdf).stem
            text_file_path = Path(f"data/{selected_ente}/albo_download/texts/{pdf_stem}.txt")
            
            if text_file_path.exists():
                testo_raw = text_file_path.read_text(encoding="utf-8", errors="ignore")
                # Mostriamo tutto il testo senza alcun troncamento
                st.text_area("Testo integrale estratto dall'atto:", value=testo_raw, height=400, disabled=True)
            else:
                # Fallback di sicurezza se il file .txt non esiste
                testo_raw = doc_data.get('text_preview', 'File di testo non trovato sul disco.')
                st.text_area("Testo estratto (Anteprima):", value=testo_raw, height=400, disabled=True)

    with col_validazione:
        st.info("✍️ **Pannello di Validazione e Correzione**")
        
        # Form per raccogliere il feedback umano
        with st.form(key=f"feedback_form_{selected_pdf}"):
            st.write("Modifica i campi in caso di errore della macchina:")
            
            # Correzione Categoria (ML Feedback)
            categorie_disponibili = ["Contabilità", "Lavori Pubblici", "Affari Generali", "Personale", "Sconosciuta"]
            cat_attuale = doc_data.get('category')
            idx_cat = categorie_disponibili.index(cat_attuale) if cat_attuale in categorie_disponibili else 4
            new_cat = st.selectbox("Categoria Corretta:", categorie_disponibili, index=idx_cat)
            
            # Correzione Importo
            val_importo = float(doc_data.get('importo_max')) if pd.notna(doc_data.get('importo_max')) else 0.0
            new_importo = st.number_input("Importo Corretto (€):", value=val_importo, format="%.2f")
            
            # Correzione RUP
            val_rup = str(doc_data.get('responsabile')) if pd.notna(doc_data.get('responsabile')) else ""
            new_rup = st.text_input("RUP Corretto:", value=val_rup)
            
            # Validazione Anomalia
            falso_positivo = False
            if 'anomalie' in doc_data and pd.notna(doc_data['anomalie']):
                falso_positivo = st.checkbox("Segna l'allarme Antifrode come FALSO POSITIVO (ignora)")

            submit_button = st.form_submit_button(label="💾 Approva e Salva Feedback")
            
            if submit_button:
                # Salvataggio su file
                feedback_data = {
                    "pdf_name": selected_pdf,
                    "timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "operatore": "Utente Dashboard",
                    "categoria_corretta": new_cat,
                    "importo_corretto": new_importo,
                    "rup_corretto": new_rup,
                    "is_falso_positivo": falso_positivo
                }
                
                feedback_df = pd.DataFrame([feedback_data])
                if FEEDBACK_FILE.exists():
                    feedback_df.to_csv(FEEDBACK_FILE, mode='a', header=False, index=False)
                else:
                    feedback_df.to_csv(FEEDBACK_FILE, index=False)
                
                st.success("Feedback salvato! Il sistema utilizzerà questi dati al prossimo addestramento.")