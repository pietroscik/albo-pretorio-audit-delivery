"""
Knowledge Graph visualization components for the web dashboard.
"""

import streamlit as st
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
from pyvis.network import Network
from typing import List, Dict, Any
from ...models.administrative_event import AdministrativeEvent, Actor


def render_knowledge_graph(events: List[AdministrativeEvent], width: str = "100%", height: int = 600):
    """
    Render an interactive Knowledge Graph from administrative events.
    
    Args:
        events: List of AdministrativeEvent objects
        width: Width of the graph visualization
        height: Height of the graph visualization in pixels
    """
    st.subheader("🌐 Knowledge Graph Interattivo")
    st.markdown("Visualizzazione del grafo delle relazioni tra entità (RUP, beneficiari, documenti).")

    # Create a NetworkX graph
    G = nx.Graph()
    
    # Add nodes and edges based on events
    for event in events:
        # Add document node
        doc_node_id = f"DOC_{event.document_id}"
        G.add_node(doc_node_id, label=event.document_id, type="document", title=event.title)
        
        # Add actor nodes and connect them to the document
        for actor in event.actors:
            actor_node_id = f"ACTOR_{actor.name}_{actor.actor_type.value}"
            G.add_node(actor_node_id, label=actor.name, type=actor.actor_type.value, title=actor.role or "")
            
            # Add edge between document and actor
            G.add_edge(doc_node_id, actor_node_id, relationship=actor.actor_type.value)
    
    # If the graph is not empty, render it
    if G.nodes():
        # Create PyVis network
        net = Network(height=f"{height}px", width=width, bgcolor="#ffffff", font_color="black")
        
        # Add nodes to the network
        for node_id in G.nodes():
            node_attrs = G.nodes[node_id]
            node_type = node_attrs.get('type', 'unknown')
            
            # Color nodes based on type
            color_map = {
                'document': '#3498db',      # Blue for documents
                'RUP': '#e74c3c',           # Red for RUP
                'BENEFICIARIO': '#2ecc71',  # Green for beneficiaries
                'unknown': '#95a5a6'        # Gray for unknown
            }
            
            net.add_node(
                node_id, 
                label=node_attrs.get('label', ''),
                title=node_attrs.get('title', ''),
                color=color_map.get(node_type, color_map['unknown']),
                shape='dot' if node_type == 'document' else 'diamond' if node_type in ['RUP', 'BENEFICIARIO'] else 'circle'
            )
        
        # Add edges to the network
        for edge in G.edges():
            net.add_edge(edge[0], edge[1])
        
        # Generate HTML for the network
        net_html = net.generate_html()
        
        # Embed the network in Streamlit
        st.components.v1.html(net_html, height=height+50, scrolling=True)
    else:
        st.info("Nessuna relazione trovata da visualizzare. Esegui prima l'analisi del Knowledge Graph.")


def extract_entities_for_graph(events: List[AdministrativeEvent]) -> Dict[str, Any]:
    """
    Extract entities and relationships for knowledge graph analysis.
    
    Args:
        events: List of AdministrativeEvent objects
        
    Returns:
        Dictionary containing entities and relationships
    """
    entities = {
        'documents': [],
        'actors': [],
        'relationships': []
    }
    
    for event in events:
        # Add document
        doc_info = {
            'id': event.document_id,
            'title': event.title,
            'date': event.document_date,
            'type': str(event.document_type),
            'economic_value': event.economic_value
        }
        entities['documents'].append(doc_info)
        
        # Add actors and relationships
        for actor in event.actors:
            actor_info = {
                'name': actor.name,
                'type': actor.actor_type.value,
                'role': actor.role,
                'area': actor.area
            }
            
            if actor_info not in entities['actors']:
                entities['actors'].append(actor_info)
            
            # Add relationship
            relationship = {
                'document_id': event.document_id,
                'actor_name': actor.name,
                'actor_type': actor.actor_type.value,
                'relationship_type': actor.actor_type.value
            }
            entities['relationships'].append(relationship)
    
    return entities


def render_entity_statistics(events: List[AdministrativeEvent]):
    """
    Render statistics about entities in the knowledge graph.
    
    Args:
        events: List of AdministrativeEvent objects
    """
    st.subheader("📊 Statistiche Entità del Knowledge Graph")
    
    # Count unique entities
    unique_rups = set()
    unique_beneficiaries = set()
    unique_documents = set()
    
    for event in events:
        unique_documents.add(event.document_id)
        
        for actor in event.actors:
            if hasattr(actor.actor_type, 'value'):
                if actor.actor_type.value == "RUP":
                    unique_rups.add(actor.name)
                elif actor.actor_type.value == "BENEFICIARIO":
                    unique_beneficiaries.add(actor.name)
    
    # Display statistics
    stats_col1, stats_col2, stats_col3 = st.columns(3)
    
    stats_col1.metric("Documenti Unici", len(unique_documents))
    stats_col2.metric("RUP Unici", len(unique_rups))
    stats_col3.metric("Beneficiari Unici", len(unique_beneficiaries))
    
    # Show top entities
    st.subheader("📈 Entità Più Attive")
    
    # Count activity by RUP
    rup_activity = {}
    for event in events:
        for actor in event.actors:
            if hasattr(actor.actor_type, 'value') and actor.actor_type.value == "RUP":
                current = rup_activity.get(actor.name, 0)
                rup_activity[actor.name] = current + 1
    
    # Count activity by Beneficiary
    beneficiary_activity = {}
    for event in events:
        for actor in event.actors:
            if hasattr(actor.actor_type, 'value') and actor.actor_type.value == "BENEFICIARIO":
                current = beneficiary_activity.get(actor.name, 0)
                beneficiary_activity[actor.name] = current + 1
    
    top_rups = dict(sorted(rup_activity.items(), key=lambda x: x[1], reverse=True)[:5])
    top_beneficiaries = dict(sorted(beneficiary_activity.items(), key=lambda x: x[1], reverse=True)[:5])
    
    top_col1, top_col2 = st.columns(2)
    
    with top_col1:
        st.write("**Top 5 RUP per Numero di Documenti:**")
        for rup, count in top_rups.items():
            st.write(f"- {rup}: {count} documenti")
    
    with top_col2:
        st.write("**Top 5 Beneficiari per Numero di Documenti:**")
        for beneficiary, count in top_beneficiaries.items():
            st.write(f"- {beneficiary}: {count} documenti")