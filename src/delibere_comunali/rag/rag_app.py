import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import json
import logging
from typing import Dict, List, Any, Optional

# Fix relative import issue by adding the src directory to path
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from delibere_comunali.utils.config import get_config
from delibere_comunali.utils.logger import get_logger
from delibere_comunali.rag.semantic_rag_engine import SemanticRAGEngine

logger = get_logger(__name__)


def main(args_obj=None):
    """Main function for the RAG Streamlit app.
    
    Args:
        args_obj: Optional Args object from orchestrator for headless operation
    """
    if args_obj is not None and hasattr(args_obj, 'ente'):
        # Called from orchestrator with Args object - for headless operation
        # We'll just initialize and potentially perform batch operations
        ente = getattr(args_obj, 'ente', 'avella')
        print(f"RAG initialized for entity: {ente}")
        # Perform any headless RAG operations here if needed
        # For now, we just acknowledge initialization
        return
    else:
        # Normal Streamlit UI operation
        st.set_page_config(
            page_title="RAG System - Albo Pretorio Audit",
            page_icon="🏛️",
            layout="wide"
        )
    
    st.title("🏛️ RAG System - Albo Pretorio Audit")
    st.markdown("""
    Interagisci semanticamente con i documenti pubblici elaborati dal sistema di audit.
    Questa interfaccia consente di porre domande in linguaggio naturale sui documenti comunali.
    """)
    
    # Initialize session state
    if 'rag_engine' not in st.session_state:
        st.session_state.rag_engine = None
    if 'search_results' not in st.session_state:
        st.session_state.search_results = []
    if 'current_ente' not in st.session_state:
        st.session_state.current_ente = None
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("🔧 Configurazione")
        
        # Entity selection
        ente = st.selectbox(
            "Seleziona ente:",
            options=get_available_entities(),
            index=0
        )
        
        # Initialize RAG engine if needed
        if ente and (st.session_state.current_ente != ente or st.session_state.rag_engine is None):
            with st.spinner(f"Inizializzazione RAG engine per {ente}..."):
                try:
                    st.session_state.rag_engine = SemanticRAGEngine(ente)
                    st.session_state.current_ente = ente
                    st.success(f"RAG engine inizializzato per {ente}")
                except Exception as e:
                    st.error(f"Errore nell'inizializzazione: {e}")
                    st.session_state.rag_engine = None
        
        # Search parameters
        k_results = st.slider("Numero di risultati", 1, 10, 5)
        category_filter = st.selectbox(
            "Filtra per categoria (opzionale)",
            options=["Tutte", "Deliberazioni", "Determinazioni", "Bandi", "Avvisi", "Altro"],
            index=0
        )
        
        # Show statistics
        if st.session_state.rag_engine:
            with st.expander("📊 Statistiche RAG"):
                stats = st.session_state.rag_engine.get_statistics()
                st.json(stats)
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("💬 Interazione Semantica")
        
        # Query input
        query = st.text_input(
            "Poni una domanda sui documenti comunali:",
            placeholder="Es: Quali sono le deliberazioni recenti sul bilancio? Chi è il responsabile del procedimento per le opere pubbliche?"
        )
        
        # Search button
        search_clicked = st.button("🔍 Cerca Semanticamente", type="primary")
        
        if search_clicked and query and st.session_state.rag_engine:
            with st.spinner("Ricerca semantica in corso..."):
                try:
                    filter_cat = category_filter if category_filter != "Tutte" else None
                    results = st.session_state.rag_engine.search(
                        query=query,
                        k=k_results,
                        filter_by_category=filter_cat
                    )
                    
                    st.session_state.search_results = results
                    
                    if results:
                        st.success(f"Trovati {len(results)} risultati rilevanti")
                    else:
                        st.info("Nessun risultato trovato per la query specificata.")
                        
                except Exception as e:
                    st.error(f"Errore durante la ricerca: {e}")
                    logger.error(f"RAG search error: {e}")
    
    with col2:
        st.header("📈 Panoramica")
        
        if st.session_state.rag_engine:
            stats = st.session_state.rag_engine.get_statistics()
            st.metric("Documenti Indicizzati", stats.get('total_documents', 0))
            st.metric("Vettori nell'Indice", stats.get('indexed_vectors', 0))
            st.metric("Ente Selezionato", st.session_state.current_ente or "Nessuno")
        else:
            st.info("Seleziona un ente per iniziare")
    
    # Display results
    if st.session_state.search_results:
        st.header("🎯 Risultati della Ricerca")
        
        for i, result in enumerate(st.session_state.search_results):
            with st.container():
                col_left, col_right = st.columns([3, 1])
                
                with col_left:
                    st.subheader(f"Documento #{i+1} (Score: {result['score']:.3f})")
                    
                    # Document details
                    doc = result['document']
                    st.write(f"**Categoria:** {doc.get('categoria', 'N/A')}")
                    st.write(f"**Data:** {doc.get('data_documento', 'N/A')}")
                    st.write(f"**Oggetto:** {doc.get('oggetto', 'N/A')[:100]}...")
                    
                    # Text snippet
                    with st.expander("📄 Testo completo"):
                        st.write(result['text_snippet'])
                
                with col_right:
                    # Action buttons
                    if st.button(f"🔍 Dettagli #{i+1}", key=f"details_{i}"):
                        # Show more details in expander
                        with st.expander("Dettagli Documento"):
                            st.json(doc)
                    
                    if st.button(f"📋 Genera Risposta #{i+1}", key=f"answer_{i}"):
                        with st.spinner("Generazione risposta..."):
                            answer = st.session_state.rag_engine.generate_answer(
                                query=query,
                                context_docs=[result],
                                model_type="local"
                            )
                            
                            with st.expander("💬 Risposta Generata"):
                                st.write(answer)
                
                st.divider()
    
    # Additional features
    st.header("⚙️ Funzionalità Avanzate")
    
    with st.expander("🔄 Aggiorna Indice"):
        st.write("Carica nuovi documenti per aggiornare l'indice RAG")
        uploaded_files = st.file_uploader(
            "Seleziona file JSON di documenti da aggiungere",
            type=['json'],
            accept_multiple_files=True
        )
        
        if uploaded_files and st.button("Aggiungi al Sistema"):
            new_docs = []
            for uploaded_file in uploaded_files:
                try:
                    content = uploaded_file.read().decode('utf-8')
                    docs = json.loads(content)
                    if isinstance(docs, list):
                        new_docs.extend(docs)
                    else:
                        new_docs.append(docs)
                except Exception as e:
                    st.error(f"Errore nel caricamento di {uploaded_file.name}: {e}")
            
            if new_docs and st.session_state.rag_engine:
                with st.spinner(f"Aggiornamento indice con {len(new_docs)} documenti..."):
                    try:
                        st.session_state.rag_engine.update_index(new_docs)
                        st.success(f"Indice aggiornato con {len(new_docs)} nuovi documenti")
                    except Exception as e:
                        st.error(f"Errore nell'aggiornamento dell'indice: {e}")
    
    with st.expander("📥 Esporta Risultati"):
        if st.session_state.search_results:
            df_results = pd.DataFrame([
                {
                    'score': result['score'],
                    'categoria': result['document'].get('categoria', ''),
                    'data_documento': result['document'].get('data_documento', ''),
                    'oggetto': result['document'].get('oggetto', '')[:100],
                    'fonte': result['document'].get('fonte', '')
                }
                for result in st.session_state.search_results
            ])
            
            csv = df_results.to_csv(index=False).encode('utf-8')
            st.download_button(
                label=" scarica risultati CSV",
                data=csv,
                file_name=f"risultati_rag_{st.session_state.current_ente}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime='text/csv'
            )


def get_available_entities() -> List[str]:
    """Get list of available entities from data directory."""
    # Look directly in the data directory for entities
    data_dir = Path("data")  # Look in the data directory where entities are stored
    
    entities = []
    if data_dir.exists():
        for item in data_dir.iterdir():
            if item.is_dir():
                # Check if this entity has albo_download directory which indicates a valid entity
                albo_dir = item / "albo_download"
                if albo_dir.exists():
                    entities.append(item.name)
    
    # If no entities found, return a default option
    return sorted(entities) if entities else ["avella", "seleziona_ente"]  # Added default entity 'avella'


if __name__ == "__main__":
    main()