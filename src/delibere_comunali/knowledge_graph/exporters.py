"""
Knowledge Graph Exporters for albo-pretorio-audit-delivery.

This module provides export functionality for knowledge graphs in multiple standard formats:
- GEXF: For Gephi and other network analysis tools
- HTML: Interactive visualization using PyVis
- GraphML: Standard XML format for graph exchange
- RDF/Turtle: For semantic web and triple stores

This ensures interoperability and auditability as required by E.N.I.A. standards.
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, Union

import networkx as nx

from .models import NodeType, RelationType


# =============================================================================
# COLOR MAP (From original script)
# =============================================================================

COLOR_MAP = {
    NodeType.ATTO: "#1E3A8A",      # Blu scuro
    NodeType.RUP: "#10B981",       # Verde
    NodeType.BENEFICIARIO: "#F59E0B", # Arancione
    NodeType.CIG: "#EF4444",        # Rosso
    NodeType.CAPITOLO: "#6366F1",  # Viola
    NodeType.ENTE: "#8B5CF6",      # Viola chiaro
    NodeType.PROCEDIMENTO: "#06B6D4", # Ciano
}


# =============================================================================
# PYVIS EXPORTER (Interactive HTML)
# =============================================================================

def save_interactive_html(
    G: nx.MultiDiGraph,
    output_path: Union[str, Path],
    height: str = "750px",
    width: str = "100%",
    bgcolor: str = "#ffffff",
    font_color: str = "#000000",
    directed: bool = True,
) -> None:
    """
    Generate an interactive HTML visualization of the graph using PyVis.
    
    This is the EXACT logic from the original build_knowledge_graph.py script.
    Preserved for backward compatibility.
    
    Args:
        G: NetworkX graph to visualize
        output_path: Path to save the HTML file
        height: Height of the visualization
        width: Width of the visualization
        bgcolor: Background color
        font_color: Font color
        directed: Whether the graph is directed
    """
    try:
        from pyvis.network import Network
    except ModuleNotFoundError as e:
        raise ImportError("PyVis is required for HTML export. Install with: pip install pyvis") from e
    
    net = Network(
        height=height,
        width=width,
        bgcolor=bgcolor,
        font_color=font_color,
        directed=directed
    )
    
    # Add nodes with colors based on type
    for node, attrs in G.nodes(data=True):
        node_type = attrs.get('type', 'Unknown')
        label = attrs.get('label', str(node))
        
        # Special formatting for Atto nodes
        if node_type == NodeType.ATTO.value:
            doc_type = attrs.get('doc_type', 'N/D')
            importo = attrs.get('importo', 0)
            label = f"Atto: {doc_type}\n€{importo:,.2f}"
        
        color = COLOR_MAP.get(node_type, "#999999")
        net.add_node(
            node,
            label=label,
            title=label,
            color=color
        )
    
    # Add edges with relation labels
    for source, target, data in G.edges(data=True):
        relation = data.get('relation', '')
        net.add_edge(source, target, title=relation)
    
    # Enable physics for interactive layout
    net.toggle_physics(True)
    
    # Save to file
    net.save_graph(str(output_path))


# =============================================================================
# GEXF EXPORTER
# =============================================================================

def save_gexf(
    G: nx.MultiDiGraph,
    output_path: Union[str, Path],
    version: str = "1.3",
) -> None:
    """
    Export graph to GEXF format (for Gephi).
    
    GEXF is an XML-based file format for representing complex networks.
    It is widely supported by network analysis tools like Gephi.
    
    Args:
        G: NetworkX graph to export
        output_path: Path to save the GEXF file
        version: GEXF version (1.3 is widely supported)
    """
    nx.write_gexf(G, str(output_path), version=version)


# =============================================================================
# GRAPHML EXPORTER
# =============================================================================

def save_graphml(
    G: nx.MultiDiGraph,
    output_path: Union[str, Path],
) -> None:
    """
    Export graph to GraphML format.
    
    GraphML is an XML-based file format for graphs that supports:
    - Directed and undirected graphs
    - Hypergraphs
    - Nested graphs
    - Attributes on nodes and edges
    - Custom data types
    
    This format is supported by many graph tools including yEd and Gephi.
    
    Args:
        G: NetworkX graph to export
        output_path: Path to save the GraphML file
    """
    nx.write_graphml(G, str(output_path))


# =============================================================================
# RDF/TURTLE EXPORTER
# =============================================================================

def _node_to_rdf_subject(node_id: str, node_type: str) -> str:
    """Convert a node ID to an RDF subject URI."""
    # Simple URI scheme: use the node type and ID
    return f"http://example.org/albo-pretorio/{node_type}/{node_id}"


def _relation_to_rdf_predicate(relation_type: str) -> str:
    """Convert a relation type to an RDF predicate URI."""
    # Use a standard vocabulary or custom URIs
    predicate_map = {
        RelationType.FIRMA_O_GESTISCE.value: "http://example.org/albo-pretorio/firmaOGestisce",
        RelationType.LIQUIDA.value: "http://example.org/albo-pretorio/liquida",
        RelationType.AFFIDA.value: "http://example.org/albo-pretorio/affida",
        RelationType.RIFERISCE_A.value: "http://example.org/albo-pretorio/riferisceA",
        RelationType.GRAVA_SU.value: "http://example.org/albo-pretorio/gravaSu",
        RelationType.APPROVATO_DA.value: "http://example.org/albo-pretorio/approvatoDa",
        RelationType.FINANZIATO_CON.value: "http://example.org/albo-pretorio/finanziatoCon",
        RelationType.RIFERITO_A.value: "http://example.org/albo-pretorio/riferitoA",
    }
    return predicate_map.get(relation_type, f"http://example.org/albo-pretorio/{relation_type}")


def _literal_value(value: Any) -> str:
    """Convert a value to an RDF literal."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        # Escape quotes and special characters
        escaped = value.replace("\", "\\\").replace("\"", "\\\"").replace("\n", "\\n")
        return f"\"{escaped}\""
    return str(value)


def save_rdf_turtle(
    G: nx.MultiDiGraph,
    output_path: Union[str, Path],
    base_uri: str = "http://example.org/albo-pretorio/",
) -> None:
    """
    Export graph to RDF/Turtle format.
    
    Turtle (Terse RDF Triple Language) is a syntax for representing RDF data.
    It is widely used in semantic web applications and triple stores.
    
    This format enables:
    - Interoperability with semantic web technologies
    - Querying with SPARQL
    - Integration with linked data
    - Long-term preservation and auditability
    
    Args:
        G: NetworkX graph to export
        output_path: Path to save the Turtle file
        base_uri: Base URI for the RDF graph
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        # Write Turtle header
        f.write(f"@prefix : <{base_uri}> .\n")
        f.write(f"@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .\n")
        f.write(f"@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n")
        f.write(f"@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n")
        f.write("\n")
        
        # Write node definitions
        for node, attrs in G.nodes(data=True):
            node_type = attrs.get('type', 'Unknown')
            node_uri = _node_to_rdf_subject(node, node_type)
            
            f.write(f"# Node: {node}\n")
            f.write(f"{node_uri} a :{node_type} ;\n")
            
            # Add label
            label = attrs.get('label', str(node))
            if label:
                f.write(f"    rdfs:label {_literal_value(label)} ;\n")
            
            # Add type-specific attributes
            if node_type == NodeType.ATTO.value:
                doc_type = attrs.get('doc_type')
                importo = attrs.get('importo')
                data_atto = attrs.get('data_atto')
                oggetto = attrs.get('oggetto')
                
                if doc_type:
                    f.write(f"    :docType {_literal_value(doc_type)} ;\n")
                if importo is not None:
                    f.write(f"    :importo {_literal_value(importo)} ;\n")
                if data_atto:
                    f.write(f"    :dataAtto \"{data_atto}\"^^xsd:date ;\n")
                if oggetto:
                    f.write(f"    :oggetto {_literal_value(oggetto)} ;\n")
            
            elif node_type == NodeType.RUP.value:
                area = attrs.get('area')
                ruolo = attrs.get('ruolo')
                codice_fiscale = attrs.get('codice_fiscale')
                
                if area:
                    f.write(f"    :area {_literal_value(area)} ;\n")
                if ruolo:
                    f.write(f"    :ruolo {_literal_value(ruolo)} ;\n")
                if codice_fiscale:
                    f.write(f"    :codiceFiscale {_literal_value(codice_fiscale)} ;\n")
            
            elif node_type == NodeType.BENEFICIARIO.value:
                tipo_soggetto = attrs.get('tipo_soggetto')
                partita_iva = attrs.get('partita_iva')
                
                if tipo_soggetto:
                    f.write(f"    :tipoSoggetto {_literal_value(tipo_soggetto)} ;\n")
                if partita_iva:
                    f.write(f"    :partitaIva {_literal_value(partita_iva)} ;\n")
            
            elif node_type == NodeType.CIG.value:
                codice = attrs.get('codice')
                if codice:
                    f.write(f"    :codice {_literal_value(codice)} ;\n")
            
            elif node_type == NodeType.CAPITOLO.value:
                codice = attrs.get('codice')
                descrizione = attrs.get('descrizione')
                
                if codice:
                    f.write(f"    :codice {_literal_value(codice)} ;\n")
                if descrizione:
                    f.write(f"    :descrizione {_literal_value(descrizione)} ;\n")
            
            # Add metadata if present
            metadata = attrs.get('metadata')
            if metadata and isinstance(metadata, dict):
                for key, value in metadata.items():
                    if value is not None:
                        f.write(f"    :{key} {_literal_value(value)} ;\n")
            
            f.write("    .\n\n")
        
        # Write edges (triples)
        f.write("# Edges (Triples)\n")
        for source, target, data in G.edges(data=True):
            relation_type = data.get('relation', 'Unknown')
            source_uri = _node_to_rdf_subject(source, G.nodes[source].get('type', 'Unknown'))
            target_uri = _node_to_rdf_subject(target, G.nodes[target].get('type', 'Unknown'))
            predicate_uri = _relation_to_rdf_predicate(relation_type)
            
            f.write(f"{source_uri} {predicate_uri} {target_uri} .\n")
            
            # Add edge attributes if present
            for attr_key, attr_value in data.items():
                if attr_key != 'relation' and attr_value is not None:
                    f.write(f"    :{attr_key} {_literal_value(attr_value)} ;\n")
            f.write("\n")


# =============================================================================
# EXPORT FUNCTION (Unified interface)
# =============================================================================

def export_graph(
    G: nx.MultiDiGraph,
    output_dir: Union[str, Path],
    formats: Optional[List[str]] = None,
) -> Dict[str, Path]:
    """
    Export a graph to multiple formats.
    
    Args:
        G: NetworkX graph to export
        output_dir: Directory to save exported files
        formats: List of formats to export ('gexf', 'html', 'graphml', 'turtle')
              If None, exports all formats.
    
    Returns:
        Dictionary mapping format names to output paths
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True, parents=True)
    
    if formats is None:
        formats = ['gexf', 'html', 'graphml', 'turtle']
    
    exported_files = {}
    
    for fmt in formats:
        fmt_lower = fmt.lower()
        output_path = output_dir / f"knowledge_graph.{fmt_lower}"
        
        if fmt_lower == 'gexf':
            save_gexf(G, output_path)
            exported_files['gexf'] = output_path
            print(f"✅ GEXF exported to: {output_path}")
        
        elif fmt_lower == 'html':
            try:
                save_interactive_html(G, output_path)
                exported_files['html'] = output_path
                print(f"✅ HTML exported to: {output_path}")
            except ImportError:
                print(f"⚠️  HTML export skipped (PyVis not installed)")
        
        elif fmt_lower == 'graphml':
            save_graphml(G, output_path)
            exported_files['graphml'] = output_path
            print(f"✅ GraphML exported to: {output_path}")
        
        elif fmt_lower == 'turtle' or fmt_lower == 'ttl':
            save_rdf_turtle(G, output_path)
            exported_files['turtle'] = output_path
            print(f"✅ RDF/Turtle exported to: {output_path}")
        
        else:
            print(f"⚠️  Unknown format: {fmt}")
    
    return exported_files