"""
Tabular data visualization components for the web dashboard.
"""

import streamlit as st
import pandas as pd
from typing import List
from ...models.administrative_event import AdministrativeEvent


def render_tabular_view(events: List[AdministrativeEvent]):
    """
    Render tabular view of administrative events.
    
    Args:
        events: List of AdministrativeEvent objects
    """
    st.subheader("🗂️ Vista Tabellare - Atti & Procedure")
    st.markdown("Esplora il dataset filtrando per procedure o RUP.")

    # Build DataFrame from standardized events
    table_data = []
    for event in events:
        row = {
            'pdf_name': event.document_id,
            'doc_type': str(event.document_type),
            'veridicità_score': event.confidence * 100,  # Convert to percentage
            'cig': event.cig or 'N/A',
            'importo_max': event.economic_value,
            'beneficiario': '',
            'tipo_procedura': str(event.event_type),
            'capitolo': '',  # This would need to be extracted from metadata
            'responsabile': '',
            'anomalie': event.metadata.get('anomalie', '') if event.metadata else ''
        }
        
        # Extract beneficiary and responsible from actors
        for actor in event.actors:
            if hasattr(actor.actor_type, 'value') and actor.actor_type.value == "BENEFICIARIO":
                row['beneficiario'] = actor.name
            elif hasattr(actor.actor_type, 'value') and actor.actor_type.value == "RUP":
                row['responsabile'] = actor.name
        
        table_data.append(row)

    df_for_display = pd.DataFrame(table_data)

    # Select columns most useful for admin audit
    cols_to_show = ['pdf_name', 'doc_type', 'veridicità_score', 'cig', 'importo_max', 'beneficiario', 'tipo_procedura', 'capitolo', 'responsabile', 'anomalie']
    available_cols = [c for c in cols_to_show if c in df_for_display.columns]

    st.dataframe(df_for_display[available_cols].sort_values(by='veridicità_score', ascending=False, na_position='last'), use_container_width=True, hide_index=True)


def filter_events_by_criteria(events: List[AdministrativeEvent], filter_field: str, filter_value: str) -> List[AdministrativeEvent]:
    """
    Filter events based on a specific field and value.
    
    Args:
        events: List of AdministrativeEvent objects
        filter_field: Field to filter on
        filter_value: Value to filter for
        
    Returns:
        Filtered list of AdministrativeEvent objects
    """
    filtered_events = []
    
    for event in events:
        if filter_field == 'beneficiario':
            for actor in event.actors:
                if hasattr(actor.actor_type, 'value') and actor.actor_type.value == "BENEFICIARIO" and filter_value.lower() in actor.name.lower():
                    filtered_events.append(event)
                    break
        elif filter_field == 'responsabile':
            for actor in event.actors:
                if hasattr(actor.actor_type, 'value') and actor.actor_type.value == "RUP" and filter_value.lower() in actor.name.lower():
                    filtered_events.append(event)
                    break
        elif filter_field == 'doc_type' and filter_value.lower() in str(event.document_type).lower():
            filtered_events.append(event)
        elif filter_field == 'tipo_procedura' and filter_value.lower() in str(event.event_type).lower():
            filtered_events.append(event)
    
    return filtered_events