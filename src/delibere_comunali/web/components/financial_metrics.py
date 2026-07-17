"""
Financial metrics visualization components for the web dashboard.
"""

import streamlit as st
from typing import List
from ...models.administrative_event import AdministrativeEvent


def render_financial_metrics(events: List[AdministrativeEvent], graph_metrics: dict = None):
    """
    Render financial metrics cards for the dashboard.
    
    Args:
        events: List of AdministrativeEvent objects
        graph_metrics: Dictionary with graph metrics (optional)
    """
    # Calculate metrics from standardized events
    total_docs = len(events)
    
    # Count unique beneficiaries
    beneficiari = set()
    for event in events:
        for actor in event.actors:
            if hasattr(actor.actor_type, 'value') and actor.actor_type.value == "BENEFICIARIO":
                beneficiari.add(actor.name)
    total_beneficiari = len(beneficiari)

    # Count affidamenti and validated acts
    affidamenti = sum(1 for event in events if event.document_type and "LGS_36" in str(event.document_type).upper())
    atti_con_visto = sum(1 for event in events if event.confidence > 0.5)

    # Display metrics in columns
    c1, c2, c3, c4 = st.columns(4)
    
    c1.metric("Totale Documenti Analizzati", total_docs)
    c2.metric("Beneficiari Identificati", total_beneficiari)
    c3.metric("Affidamenti D.Lgs 36/2023", affidamenti)
    c4.metric("Ati con Validazione Cross-Verificata", atti_con_visto)

    # Show graph metrics if available
    if graph_metrics:
        st.info(f"🧠 **Cervello Relazionale Attivo (Knowledge Graph):** Rilevati **{graph_metrics.get('nodes_count', 0)} nodi** (di cui {graph_metrics.get('rup_count', 0)} RUP e {graph_metrics.get('capitoli_count', 0)} Capitoli di Bilancio) connessi da **{graph_metrics.get('edges_count', 0)} sinapsi**.")

    # Count anomalies using standardized events
    anomalies_count = sum(1 for event in events if event.metadata and event.metadata.get('anomalie', '').strip() != '')
    if anomalies_count > 0:
        st.warning(f"⚠️ Attenzione: Il motore NLP ha segnalato **{anomalies_count} documenti con criticità** (Dati poco solidi o anomalie in IBAN/P.IVA). Si consiglia revisione manuale.")


def calculate_financial_summary(events: List[AdministrativeEvent]) -> dict:
    """
    Calculate financial summary statistics from events.
    
    Args:
        events: List of AdministrativeEvent objects
        
    Returns:
        Dictionary with financial summary statistics
    """
    total_spending = sum(event.economic_value or 0 for event in events if event.economic_value)
    
    # Group by document type
    spending_by_type = {}
    for event in events:
        doc_type = str(event.document_type) if event.document_type else "Sconosciuto"
        current = spending_by_type.get(doc_type, 0)
        spending_by_type[doc_type] = current + (event.economic_value or 0)
    
    # Find top beneficiaries
    beneficiary_spending = {}
    for event in events:
        for actor in event.actors:
            if hasattr(actor.actor_type, 'value') and actor.actor_type.value == "BENEFICIARIO":
                current = beneficiary_spending.get(actor.name, 0)
                beneficiary_spending[actor.name] = current + (event.economic_value or 0)
    
    # Sort beneficiaries by spending
    sorted_beneficiaries = dict(sorted(beneficiary_spending.items(), key=lambda x: x[1], reverse=True)[:10])
    
    return {
        'total_spending': total_spending,
        'spending_by_type': spending_by_type,
        'top_beneficiaries': sorted_beneficiaries,
        'average_spending_per_doc': total_spending / len(events) if events else 0
    }