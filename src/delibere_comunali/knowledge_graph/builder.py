"""
Knowledge Graph Builder for albo-pretorio-audit-delivery.

This module contains the logic for building knowledge graphs from parsed CSV data
(allegati_parsed.csv or atti_parsed.csv). It preserves the original logic from
scripts/build_knowledge_graph.py while adding entity resolution capabilities.
"""

import argparse
import pandas as pd
import networkx as nx
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from .models import (
    AttoNode,
    RupNode,
    BeneficiarioNode,
    CigNode,
    CapitoloNode,
    NodeType,
    RelationType,
    GraphEdge,
    KnowledgeGraph,
    NodeMetadata,
    create_node_metadata,
)


# =============================================================================
# ENTITY RESOLUTION (Deduplication)
# =============================================================================

class EntityResolver:
    """
    Handles entity deduplication and resolution for the knowledge graph.
    
    This is critical for Albo Pretorio data where the same entity (e.g., "Comune di Baiano")
    may appear with slightly different names ("Comune Baiano", "Comune di Baiano", etc.).
    """
    
    def __init__(self):
        self.entity_map: Dict[str, str] = {}  # canonical_name -> entity_id
        self.aliases: Dict[str, List[str]] = {}  # entity_id -> list of aliases
    
    def normalize_entity_name(self, name: str) -> str:
        """
        Normalize entity name for comparison.
        
        This removes common variations like:
        - "Comune di X" vs "Comune X"
        - Case differences
        - Extra whitespace
        - Common abbreviations
        """
        if not name or not isinstance(name, str):
            return ""
        
        # Lowercase and strip
        normalized = name.strip().lower()
        
        # Remove common prefixes/suffixes
        prefixes_suffixes = [
            "comune di", "comune", "di", "del", "della", "dell'",
            "s.p.a.", "s.r.l.", "srl", "spa",
            "snc", "cooperativa", "consorzio",
        ]
        for ps in prefixes_suffixes:
            normalized = normalized.replace(ps, "").strip()
        
        # Remove extra whitespace
        normalized = " ".join(normalized.split())
        
        return normalized
    
    def resolve_entity(self, name: str, entity_type: NodeType) -> str:
        """
        Resolve an entity name to its canonical ID.
        
        If the entity has been seen before (with any variation), return the
        canonical ID. Otherwise, create a new canonical ID.
        """
        if not name:
            return ""
        
        normalized = self.normalize_entity_name(name)
        
        if normalized in self.entity_map:
            # Entity already exists, return canonical ID
            return self.entity_map[normalized]
        
        # New entity, create canonical ID
        canonical_id = f"{entity_type.value}_{len(self.entity_map) + 1}"
        self.entity_map[normalized] = canonical_id
        
        # Track the original name as the first alias
        if canonical_id not in self.aliases:
            self.aliases[canonical_id] = []
        self.aliases[canonical_id].append(name)
        
        return canonical_id
    
    def get_canonical_name(self, entity_id: str) -> Optional[str]:
        """Get the first (canonical) name for an entity ID."""
        if entity_id in self.aliases and self.aliases[entity_id]:
            return self.aliases[entity_id][0]
        return None
    
    def get_all_aliases(self, entity_id: str) -> List[str]:
        """Get all known aliases for an entity ID."""
        return self.aliases.get(entity_id, [])


# Global entity resolver instance
entity_resolver = EntityResolver()


# =============================================================================
# UTILITY FUNCTIONS (From original script)
# =============================================================================

def clean_node(val: Any) -> Optional[str]:
    """
    Clean node values: handle NaN, None, empty strings.
    
    This is the EXACT logic from the original build_knowledge_graph.py script.
    Preserved for backward compatibility and data consistency.
    """
    if pd.isna(val):
        return None
    v = str(val).strip()
    return v if v else None


def filter_boilerplate_importo(importo: Optional[float]) -> float:
    """
    Filter out boilerplate import values.
    
    Original logic: importi > 5.000.000 are considered boilerplate and set to 0.
    This prevents "crazy" values from appearing in the graph.
    """
    if importo is None or pd.isna(importo):
        return 0.0
    if importo > 5_000_000:
        return 0.0
    return float(importo)


# =============================================================================
# GRAPH BUILDING FUNCTIONS
# =============================================================================

def build_graph_from_csv(
    csv_path: Path,
    base_dir: Optional[Path] = None,
    source_file: Optional[str] = None,
    file_hash: Optional[str] = None,
) -> KnowledgeGraph:
    """
    Build a knowledge graph from a parsed CSV file.
    
    This is the core function that replaces the original build_knowledge_graph.py logic.
    It reads CSV data, creates nodes and edges, and returns a validated KnowledgeGraph.
    
    Args:
        csv_path: Path to the CSV file (allegati_parsed.csv or atti_parsed.csv)
        base_dir: Base directory for relative paths
        source_file: Original source file path for metadata
        file_hash: SHA-256 hash of the source file
    
    Returns:
        KnowledgeGraph: Validated graph structure
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    
    # Read CSV
    df_atti = pd.read_csv(csv_path)
    
    # Parse dates (original logic)
    df_atti['data_parsed'] = pd.to_datetime(
        df_atti['data_atto'],
        format='%d/%m/%Y',
        errors='coerce'
    )
    df_atti = df_atti.sort_values(by='data_parsed', na_position='last')
    
    # Prepare metadata
    extraction_date = datetime.now()
    metadata = create_node_metadata(
        source_file=source_file,
        file_hash=file_hash,
        extraction_date=extraction_date
    )
    
    # Build nodes and edges
    nodes: List = []
    edges: List = []
    
    for _, row in df_atti.iterrows():
        # Extract and clean data
        atto_id = clean_node(row.get('pdf_name'))
        if not atto_id:
            continue
        
        doc_type = clean_node(row.get('doc_type')) or "unknown"
        importo_raw = row.get('importo_max')
        importo = filter_boilerplate_importo(importo_raw)
        data_atto = row['data_parsed'].date() if pd.notna(row['data_parsed']) else None
        oggetto = clean_node(row.get('oggetto'))
        
        # Create Atto node
        atto_node = AttoNode(
            node_id=atto_id,
            label=f"{doc_type}: {oggetto}" if oggetto else doc_type,
            doc_type=doc_type,
            importo=importo,
            data_atto=data_atto,
            oggetto=oggetto,
            metadata=create_node_metadata(
                source_file=source_file,
                file_hash=file_hash,
                extraction_date=extraction_date
            )
        )
        nodes.append(atto_node)
        
        # --- RUP (Responsabile Unico del Procedimento) ---
        rup_name = clean_node(row.get('responsabile'))
        if rup_name and rup_name != "NON IDENTIFICATO":
            # Use entity resolution for deduplication
            rup_id = entity_resolver.resolve_entity(rup_name, NodeType.RUP)
            
            rup_node = RupNode(
                node_id=rup_id,
                label=entity_resolver.get_canonical_name(rup_id) or rup_name,
                area=clean_node(row.get('rup_area')),
                ruolo=clean_node(row.get('rup_ruolo')),
                metadata=create_node_metadata(
                    source_file=source_file,
                    file_hash=file_hash,
                    extraction_date=extraction_date
                )
            )
            nodes.append(rup_node)
            
            # Add edge: RUP -> Atto
            edges.append(GraphEdge(
                source=rup_id,
                target=atto_id,
                relation_type=RelationType.FIRMA_O_GESTISCE,
                attributes={},
                metadata={"source_row": row.name if hasattr(row, 'name') else None}
            ))
        
        # --- Beneficiario ---
        ben_name = clean_node(row.get('beneficiario'))
        if ben_name and ben_name != "NON IDENTIFICATO":
            ben_id = entity_resolver.resolve_entity(ben_name, NodeType.BENEFICIARIO)
            
            ben_node = BeneficiarioNode(
                node_id=ben_id,
                label=entity_resolver.get_canonical_name(ben_id) or ben_name,
                tipo_soggetto=clean_node(row.get('tipo_beneficiario')),
                partita_iva=clean_node(row.get('partita_iva')),
                metadata=create_node_metadata(
                    source_file=source_file,
                    file_hash=file_hash,
                    extraction_date=extraction_date
                )
            )
            nodes.append(ben_node)
            
            # Determine relation type based on doc_type
            if doc_type in ["Determinazione", "VistoContabile"]:
                relation = RelationType.LIQUIDA
            else:
                relation = RelationType.AFFIDA
            
            edges.append(GraphEdge(
                source=atto_id,
                target=ben_id,
                relation_type=relation,
                attributes={"importo": importo},
                metadata={"source_row": row.name if hasattr(row, 'name') else None}
            ))
        
        # --- CIG (Codice Identificativo Gara) ---
        cig = clean_node(row.get('cig'))
        if cig:
            cig_id = f"CIG_{cig}"
            cig_node = CigNode(
                node_id=cig_id,
                label=cig,
                codice=cig,
                metadata=create_node_metadata(
                    source_file=source_file,
                    file_hash=file_hash,
                    extraction_date=extraction_date
                )
            )
            nodes.append(cig_node)
            
            edges.append(GraphEdge(
                source=atto_id,
                target=cig_id,
                relation_type=RelationType.RIFERISCE_A,
                attributes={},
                metadata={"source_row": row.name if hasattr(row, 'name') else None}
            ))
        
        # --- Capitolo ---
        capitolo = clean_node(row.get('capitolo'))
        if capitolo and str(capitolo).upper() not in ["NON IDENTIFICATO", "NONE", "NAN"]:
            capitolo_id = f"CAP_{capitolo}"
            capitolo_node = CapitoloNode(
                node_id=capitolo_id,
                label=str(capitolo),
                codice=str(capitolo),
                metadata=create_node_metadata(
                    source_file=source_file,
                    file_hash=file_hash,
                    extraction_date=extraction_date
                )
            )
            nodes.append(capitolo_node)
            
            edges.append(GraphEdge(
                source=atto_id,
                target=capitolo_id,
                relation_type=RelationType.GRAVA_SU,
                attributes={},
                metadata={"source_row": row.name if hasattr(row, 'name') else None}
            ))
    
    # Create and return the validated graph
    return KnowledgeGraph(
        nodes=nodes,
        edges=edges,
        metadata={
            "source_file": str(csv_path),
            "extraction_date": extraction_date.isoformat(),
            "node_count": len(nodes),
            "edge_count": len(edges),
            "entity_resolution_stats": {
                "total_entities": len(entity_resolver.entity_map),
                "deduplicated_count": sum(len(v) - 1 for v in entity_resolver.aliases.values()),
            }
        }
    )


def find_csv_file(base: Path) -> Path:
    """
    Find the appropriate CSV file (allegati_parsed.csv or atti_parsed.csv).
    
    This preserves the original fallback logic.
    """
    # Preferiamo allegati_parsed.csv che e' quello arricchito dall'LLM
    atti_path = base / "allegati_parsed.csv"
    if atti_path.exists():
        return atti_path
    
    # Fallback to atti_parsed.csv
    atti_path = base / "atti_parsed.csv"
    if atti_path.exists():
        return atti_path
    
    raise FileNotFoundError(f"No CSV file found in {base}. Expected allegati_parsed.csv or atti_parsed.csv")


# =============================================================================
# MAIN FUNCTION (CLI Entry Point)
# =============================================================================

def main():
    """
    Main entry point for building knowledge graph from CLI.
    
    This replicates the original script's CLI interface.
    """
    parser = argparse.ArgumentParser(
        description='Build knowledge graph from parsed Albo Pretorio data'
    )
    parser.add_argument("--base", default='albo_download', help='Base directory containing CSV files')
    parser.add_argument("--output", default=None, help='Output directory (default: <base>/report)")
    args = parser.parse_args()
    
    base = Path(args.base)
    
    # Find CSV file
    csv_path = find_csv_file(base)
    
    # Determine output directory
    if args.output:
        report_dir = Path(args.output)
    else:
        report_dir = base / "report"
    report_dir.mkdir(exist_ok=True, parents=True)
    
    # Build graph
    kg = build_graph_from_csv(
        csv_path=csv_path,
        base_dir=base,
        source_file=str(csv_path),
    )
    
    # Convert to NetworkX for export
    G = kg.as_networkx
    
    # Export GEXF
    gexf_path = report_dir / "knowledge_graph.gexf"
    nx.write_gexf(G, str(gexf_path))
    print(f"✅ GEXF graph saved to: {gexf_path}")
    
    # Export HTML (using original PyVis logic)
    try:
        from .exporters import save_interactive_html
        html_path = report_dir / "knowledge_graph.html"
        save_interactive_html(G, html_path)
        print(f"✅ Interactive HTML graph saved to: {html_path}")
    except ImportError as e:
        print(f"⚠️  PyVis not available for HTML export: {e}")
    except Exception as e:
        print(f"❌ Error generating HTML graph: {e}")
    
    # Return the graph for programmatic use
    return kg


if __name__ == "__main__":
    main()