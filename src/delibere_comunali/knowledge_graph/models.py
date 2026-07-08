"""
Knowledge Graph Models for albo-pretorio-audit-delivery.

This module defines the data models for the knowledge graph using Pydantic for validation.
Each entity in the graph (nodes and edges) is validated to ensure data integrity,
which is essential for E.N.I.A. compliance and auditability.
"""

from datetime import datetime, date
from enum import Enum
from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field, field_validator


# =============================================================================
# ENUMS: Node and Relation Types
# =============================================================================

class NodeType(str, Enum):
    """Types of nodes in the knowledge graph."""
    ATTO = "Atto"
    RUP = "RUP"  # Responsabile Unico del Procedimento
    BENEFICIARIO = "Beneficiario"
    CIG = "CIG"  # Codice Identificativo Gara
    CAPITOLO = "Capitolo"
    ENTE = "Ente"
    PROCEDIMENTO = "Procedimento"


class RelationType(str, Enum):
    """Types of relationships between nodes."""
    FIRMA_O_GESTISCE = "FIRMA_O_GESTISCE"
    LIQUIDA = "LIQUIDA"
    AFFIDA = "AFFIDA"
    RIFERISCE_A = "RIFERISCE_A"
    GRAVA_SU = "GRAVA_SU"
    APPROVATO_DA = "APPROVATO_DA"
    FINANZIATO_CON = "FINANZIATO_CON"
    RIFERITO_A = "RIFERITO_A"


# =============================================================================
# NODE MODELS
# =============================================================================

class NodeMetadata(BaseModel):
    """Flexible metadata for nodes, allowing connection to original files via SHA-256 hash.
    
    This is essential for E.N.I.A. compliance as it allows tracing each graph entity
    back to its original source document (PDF/P7M).
    """
    source_file: Optional[str] = Field(default=None, description="Path to the original source file")
    file_hash: Optional[str] = Field(default=None, description="SHA-256 hash of the original file")
    extraction_date: Optional[datetime] = Field(default=None, description="When the data was extracted")
    confidence_score: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Confidence score for the extracted data")
    raw_text: Optional[str] = Field(default=None, description="Original raw text from the document")
    page_number: Optional[int] = Field(default=None, description="Page number in the original document")
    
    @field_validator('file_hash')
    @classmethod
    def validate_hash_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate that the hash is a valid SHA-256 hex string."""
        if v is None:
            return None
        if len(v) != 64 or not all(c in '0123456789abcdef' for c in v.lower()):
            raise ValueError(f"Invalid SHA-256 hash format: {v}")
        return v.lower()


class BaseNode(BaseModel):
    """Base model for all graph nodes with common fields."""
    node_id: str = Field(..., description="Unique identifier for the node")
    node_type: NodeType = Field(..., description="Type of the node")
    label: str = Field(..., description="Human-readable label")
    metadata: NodeMetadata = Field(default_factory=NodeMetadata, description="Flexible metadata container")
    
    class Config:
        use_enum_values = True  # Allow enum values in JSON serialization


class AttoNode(BaseNode):
    """Represents an administrative act (Atto)."""
    node_type: NodeType = NodeType.ATTO
    doc_type: Optional[str] = Field(default=None, description="Type of document (Determinazione, Delibera, etc.)")
    importo: float = Field(default=0.0, description="Amount in euros")
    data_atto: Optional[date] = Field(default=None, description="Date of the act")
    oggetto: Optional[str] = Field(default=None, description="Subject/object of the act")
    
    @field_validator('importo')
    @classmethod
    def validate_importo(cls, v: float) -> float:
        """Ensure importo is non-negative and filter boilerplate values."""
        if v < 0:
            raise ValueError("Importo cannot be negative")
        # Filter out boilerplate values (as in original logic)
        if v > 5_000_000:
            return 0.0
        return v


class RupNode(BaseNode):
    """Represents a Responsabile Unico del Procedimento (RUP)."""
    node_type: NodeType = NodeType.RUP
    area: Optional[str] = Field(default=None, description="Area/Department")
    ruolo: Optional[str] = Field(default=None, description="Role/Position")
    codice_fiscale: Optional[str] = Field(default=None, description="Tax ID")


class BeneficiarioNode(BaseNode):
    """Represents a beneficiary (subject receiving funds)."""
    node_type: NodeType = NodeType.BENEFICIARIO
    tipo_soggetto: Optional[str] = Field(default=None, description="Type of subject (Person, Company, etc.)")
    partita_iva: Optional[str] = Field(default=None, description="VAT number")


class CigNode(BaseNode):
    """Represents a Codice Identificativo Gara (CIG)."""
    node_type: NodeType = NodeType.CIG
    codice: str = Field(..., description="CIG code")
    
    @field_validator('codice')
    @classmethod
    def validate_cig_format(cls, v: str) -> str:
        """Basic validation for CIG format."""
        cleaned = v.strip().upper()
        if not cleaned:
            raise ValueError("CIG cannot be empty")
        return cleaned


class CapitoloNode(BaseNode):
    """Represents a budget chapter (Capitolo)."""
    node_type: NodeType = NodeType.CAPITOLO
    codice: str = Field(..., description="Chapter code")
    descrizione: Optional[str] = Field(default=None, description="Chapter description")


# =============================================================================
# EDGE MODELS
# =============================================================================

class GraphEdge(BaseModel):
    """Represents an edge in the knowledge graph."""
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    relation_type: RelationType = Field(..., description="Type of relationship")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Additional edge attributes")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Edge metadata")
    
    class Config:
        use_enum_values = True


# =============================================================================
# GRAPH MODEL (Complete structure)
# =============================================================================

class KnowledgeGraph(BaseModel):
    """Complete knowledge graph structure."""
    nodes: List[BaseNode] = Field(default_factory=list, description="List of all nodes in the graph")
    edges: List[GraphEdge] = Field(default_factory=list, description="List of all edges in the graph")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Graph-level metadata")
    
    @property
    def as_networkx(self) -> 'nx.MultiDiGraph':
        """Convert to NetworkX graph (lazy import to avoid circular dependencies)."""
        import networkx as nx
        G = nx.MultiDiGraph()
        
        # Add nodes
        for node in self.nodes:
            node_attrs = {
                'label': node.label,
                'type': node.node_type.value,
            }
            
            # Add dynamic properties, filtering out None values
            for attr_name, attr_value in node.model_dump().items():
                if attr_value is not None and attr_name not in ['node_id', 'label', 'node_type']:
                    if not isinstance(attr_value, (str, int, float, bool)):
                        # Convert other types to string representation
                        node_attrs[attr_name] = str(attr_value)
                    else:
                        node_attrs[attr_name] = attr_value
            
            # Add metadata if present
            if node.metadata:
                metadata_dict = node.metadata.model_dump(exclude_unset=True) if hasattr(node.metadata, 'model_dump') else node.metadata
                for key, value in metadata_dict.items():
                    if value is not None:
                        if not isinstance(value, (str, int, float, bool)):
                            node_attrs[f'metadata_{key}'] = str(value)
                        else:
                            node_attrs[f'metadata_{key}'] = value
            
            G.add_node(node.node_id, **node_attrs)
        
        # Add edges
        for edge in self.edges:
            edge_attrs = {
                'relation': edge.relation_type,  # relation_type is already a string since RelationType is str, Enum
            }
            
            # Add edge attributes, filtering out None values
            for attr_name, attr_value in edge.attributes.items():
                if attr_value is not None:
                    if not isinstance(attr_value, (str, int, float, bool)):
                        edge_attrs[attr_name] = str(attr_value)
                    else:
                        edge_attrs[attr_name] = attr_value
            
            # Add edge metadata if present
            if edge.metadata:
                for key, value in edge.metadata.items():
                    if value is not None:
                        if not isinstance(value, (str, int, float, bool)):
                            edge_attrs[f'metadata_{key}'] = str(value)
                        else:
                            edge_attrs[f'metadata_{key}'] = value
            
            G.add_edge(edge.source, edge.target, **edge_attrs)
        
        return G


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def compute_file_hash(filepath: str) -> str:
    """Compute SHA-256 hash of a file for metadata tracking."""
    import hashlib
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()


def create_node_metadata(
    source_file: Optional[str] = None,
    file_hash: Optional[str] = None,
    extraction_date: Optional[datetime] = None,
    **kwargs: Any
) -> NodeMetadata:
    """Factory function for creating node metadata with defaults."""
    return NodeMetadata(
        source_file=source_file,
        file_hash=file_hash,
        extraction_date=extraction_date or datetime.now(),
        **kwargs
    )