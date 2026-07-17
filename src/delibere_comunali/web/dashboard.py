import streamlit as st
import pandas as pd
from pathlib import Path
import json
import os

from delibere_comunali.utils.config import get_tenant_dir
from delibere_comunali.web.data_loader import load_administrative_events, load_parsed_documents
from delibere_comunali.web.components import (
    render_financial_metrics,
    render_tabular_view,
    render_knowledge_graph,
    render_entity_statistics
)

# Configurazione della pagina
st.set_page_config(page_title="Validazione Albo AI", layout="wide", page_icon="📊")

@st.cache_data
def get_available_enti():
    data_dir = Path("data")
    if not data_dir.exists(): return []
    # Trova le cartelle degli enti che contengono dati analizzati
    return [d.name for d in data_dir.iterdir() if d.is_dir() and (d / "albo_download" / "allegati_parsed.csv").exists()]

@st.cache_data
def load_events(ente):
    """Carica i dati come eventi amministrativi standardizzati."""
    return load_administrative_events(ente)

@st.cache_data
def load_documents(ente):
    """Carica i dati come documenti parsati standardizzati."""
    return load_parsed_documents(ente)

@st.cache_data
def load_graph_metrics(ente):
    """Carica le metriche del grafo dal file JSON."""
    tenant_dir = get_tenant_dir(ente)
    metrics_path = tenant_dir / "report" / "graph_metrics.json"
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

events = load_events(selected_ente)
documents = load_documents(selected_ente)

if not events:
    st.error(f"Dati non trovati per l'ente {selected_ente}.")
    st.stop()

# --- SEZIONE KPI (Metriche in evidenza) ---
graph_metrics = load_graph_metrics(selected_ente)

st.subheader(f"📈 Indicatori di Trasparenza - Comune di {selected_ente.capitalize()}")
render_financial_metrics(events, graph_metrics)

st.divider()

# --- SEZIONE TABELLA INTERATTIVA ---
render_tabular_view(events)

st.divider()

# --- SEZIONE KNOWLEDGE GRAPH ---
# Check if we have the required libraries for knowledge graph visualization
try:
    import networkx as nx
    from pyvis.network import Network
    import streamlit.components.v1 as components
    
    # Render knowledge graph statistics
    render_entity_statistics(events)
    
    # Render interactive knowledge graph
    render_knowledge_graph(events)
    
except ImportError:
    st.warning("⚠️ Le librerie per la visualizzazione del Knowledge Graph non sono installate. Esegui: pip install networkx pyvis")
    st.info("Visualizzazione del Knowledge Graph saltata per mancanza di dipendenze.")

st.divider()

# --- SEZIONE ISPEZIONE E VALIDAZIONE (HUMAN-IN-THE-LOOP) ---
st.subheader("🔍 Ispezione e Validazione Umana (Active Learning)")
st.markdown("Come operatore (Decisore Ultimo), puoi validare le estrazioni dell'AI o correggere i falsi positivi per addestrare meglio il sistema.")

# Inizializza il file dei feedback se non esiste
tenant_dir = get_tenant_dir(selected_ente)
FEEDBACK_FILE = tenant_dir / "feedback_operatore.csv"

# Menu di selezione documento
selected_doc_id = st.selectbox("Seleziona l'atto da ispezionare:", [e.document_id for e in events])

if selected_doc_id:
    # Trova l'evento corrispondente
    selected_event = next((e for e in events if e.document_id == selected_doc_id), None)
    selected_doc = next((d for d in documents if Path(d.pdf_name).stem == selected_doc_id), None)
    
    if selected_event:
        col_dati, col_validazione = st.columns([1, 1])
        
        with col_dati:
            score = selected_event.confidence * 100  # Convert to percentage
            color = "🟢" if score >= 80 else ("🟡" if score > 40 else "🔴")
            st.success(f"**Risultato Estrazione Macchina** (Score di Veridicità: {color} {score:.1f}/100)")
            
            # Estrai dati dagli attori dell'evento
            rup_nome = ""
            beneficiario_nome = ""
            for actor in selected_event.actors:
                if hasattr(actor.actor_type, 'value') and actor.actor_type.value == "RUP":
                    rup_nome = actor.name
                elif hasattr(actor.actor_type, 'value') and actor.actor_type.value == "BENEFICIARIO":
                    beneficiario_nome = actor.name
            
            # Mostriamo i dati correnti estratti dall'evento standardizzato
            display_data = {
                "Oggetto": selected_event.title,
                "Classificazione": f"{selected_event.event_type.value} - {selected_event.document_type.value}",
                "Amministrazione (RUP/Ufficio)": rup_nome,
                "Beneficiario": beneficiario_nome,
                "P.IVA / IBAN": f"P.IVA: N/D - IBAN: N/D",  # Would need to be added to metadata
                "Tracciabilità (CIG/CUP)": f"CIG: {selected_event.cig or 'N/D'} - CUP: {selected_event.cup or 'N/D'}",
                "Importo Massimo": f"€ {selected_event.economic_value}" if selected_event.economic_value else "Non rilevato",
            }
            
            st.json(display_data)
            
            # Mostra eventuali anomalie
            if selected_event.metadata and selected_event.metadata.get('anomalie'):
                st.error(f"**Alert Antifrode/NLP:** {selected_event.metadata['anomalie']}")
                
            with st.expander("Vedi Testo Originale Completo (Lettura da disco)", expanded=True):
                # Cerca il testo originale dal documento originale se disponibile
                if selected_doc and selected_doc._text:
                    testo_raw = selected_doc._text
                    st.text_area("Testo integrale estratto dall'atto:", value=testo_raw, height=400, disabled=True)
                else:
                    # Cerca il file di testo originale
                    pdf_stem = Path(selected_doc_id).stem
                    text_file_path = tenant_dir / "texts" / f"{pdf_stem}.txt"
                    
                    if text_file_path.exists():
                        testo_raw = text_file_path.read_text(encoding="utf-8", errors="ignore")
                        # Mostriamo tutto il testo senza alcun troncamento
                        st.text_area("Testo integrale estratto dall'atto:", value=testo_raw, height=400, disabled=True)
                    else:
                        # Fallback se nessun testo è disponibile
                        testo_raw = "Testo non disponibile."
                        st.text_area("Testo estratto (Anteprima):", value=testo_raw, height=400, disabled=True)

        with col_validazione:
            st.info("✍️ **Pannello di Validazione e Correzione**")
            
            # Form per raccogliere il feedback umano
            with st.form(key=f"feedback_form_{selected_doc_id}"):
                st.write("Modifica i campi in caso di errore della macchina:")
                
                # Correzione Categoria (ML Feedback)
                categorie_disponibili = ["Contabilità", "Lavori Pubblici", "Affari Generali", "Personale", "Sconosciuta"]
                cat_attuale = str(selected_event.event_type.value) if selected_event.event_type else "Sconosciuta"
                idx_cat = next((i for i, cat in enumerate(categorie_disponibili) if cat in cat_attuale), len(categorie_disponibili)-1)
                new_cat = st.selectbox("Categoria Corretta:", categorie_disponibili, index=idx_cat)
                
                # Correzione Importo
                val_importo = float(selected_event.economic_value) if selected_event.economic_value else 0.0
                new_importo = st.number_input("Importo Corretto (€):", value=val_importo, format="%.2f")
                
                # Correzione RUP
                val_rup = rup_nome
                new_rup = st.text_input("RUP Corretto:", value=val_rup)
                
                # Validazione Anomalia
                falso_positivo = False
                if selected_event.metadata and selected_event.metadata.get('anomalie'):
                    falso_positivo = st.checkbox("Segna l'allarme Antifrode come FALSO POSITIVO (ignora)")

                submit_button = st.form_submit_button(label="💾 Approva e Salva Feedback")
                
                if submit_button:
                    # Salvataggio su file
                    feedback_data = {
                        "pdf_name": selected_doc_id,
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