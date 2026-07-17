"""
Data loader module for the web dashboard.
Transforms raw CSV data into standardized ParsedDocument or AdministrativeEvent objects.
"""

import pandas as pd
from pathlib import Path
from typing import List, Optional
from ..models.parsed_document import ParsedDocument
from ..models.administrative_event import AdministrativeEvent
from ..processing.event_factory import DigitalTwinEventFactory
from ..utils.config import get_tenant_dir


def load_raw_data(ente: str) -> Optional[pd.DataFrame]:
    """
    Load raw data from CSV file for a given entity.
    
    Args:
        ente: Name of the entity to load data for
        
    Returns:
        DataFrame with raw data or None if file not found
    """
    tenant_dir = get_tenant_dir(ente)
    csv_path = tenant_dir / "allegati_parsed.csv"
    
    if not csv_path.exists():
        return None
    
    # Load with explicit dtype to handle mixed-type columns
    df = pd.read_csv(csv_path, low_memory=False)
    return df


def dataframe_to_parsed_documents(df: pd.DataFrame) -> List[ParsedDocument]:
    """
    Transform a DataFrame into a list of ParsedDocument objects.
    
    Args:
        df: DataFrame containing parsed document data
        
    Returns:
        List of ParsedDocument objects
    """
    documents = []
    
    for _, row in df.iterrows():
        doc = ParsedDocument()
        
        # Map common fields from the DataFrame
        doc.pdf_name = str(row.get('pdf_name', ''))
        doc.numero_atto = str(row.get('numero_atto', ''))
        doc.data_atto = str(row.get('data_atto', ''))
        doc.oggetto = str(row.get('oggetto', ''))
        doc.rup_nome = str(row.get('responsabile', '')) if pd.notna(row.get('responsabile')) else ''
        doc.beneficiario = str(row.get('beneficiario', '')) if pd.notna(row.get('beneficiario')) else ''
        
        # Handle numeric values safely
        try:
            doc.importo_max = float(row.get('importo_max', 0.0)) if pd.notna(row.get('importo_max')) else 0.0
        except (ValueError, TypeError):
            doc.importo_max = 0.0
            
        doc.cig = str(row.get('cig', '')) if pd.notna(row.get('cig')) else ''
        doc.cup = str(row.get('cup', '')) if pd.notna(row.get('cup')) else ''
        doc.legal_urn = str(row.get('legal_urn', ''))
        
        # Extract text content if available
        doc._text = str(row.get('text', '')) if pd.notna(row.get('text')) else str(row.get('_text', ''))
        
        # Additional fields that might be present
        if 'doc_type' in df.columns:
            doc.doc_type = str(row.get('doc_type', ''))
        if 'category' in df.columns:
            doc.category = str(row.get('category', ''))
        if 'veridicità_score' in df.columns:
            try:
                doc.veridicita_score = float(row.get('veridicità_score', 0.0)) if pd.notna(row.get('veridicità_score')) else 0.0
            except (ValueError, TypeError):
                doc.veridicita_score = 0.0
        if 'anomalie' in df.columns:
            doc.anomalie = str(row.get('anomalie', '')) if pd.notna(row.get('anomalie')) else ''
            
        documents.append(doc)
    
    return documents


def dataframe_to_administrative_events(df: pd.DataFrame) -> List[AdministrativeEvent]:
    """
    Transform a DataFrame into a list of AdministrativeEvent objects using DigitalTwinEventFactory.
    
    Args:
        df: DataFrame containing parsed document data
        
    Returns:
        List of AdministrativeEvent objects
    """
    factory = DigitalTwinEventFactory()
    events = []
    
    for _, row in df.iterrows():
        # Create a temporary ParsedDocument from the row
        doc = ParsedDocument()
        
        # Map common fields from the DataFrame
        doc.pdf_name = str(row.get('pdf_name', ''))
        doc.numero_atto = str(row.get('numero_atto', ''))
        doc.data_atto = str(row.get('data_atto', ''))
        doc.oggetto = str(row.get('oggetto', ''))
        doc.rup_nome = str(row.get('responsabile', '')) if pd.notna(row.get('responsabile')) else ''
        doc.beneficiario = str(row.get('beneficiario', '')) if pd.notna(row.get('beneficiario')) else ''
        
        # Handle numeric values safely
        try:
            doc.importo_max = float(row.get('importo_max', 0.0)) if pd.notna(row.get('importo_max')) else 0.0
        except (ValueError, TypeError):
            doc.importo_max = 0.0
            
        doc.cig = str(row.get('cig', '')) if pd.notna(row.get('cig')) else ''
        doc.cup = str(row.get('cup', '')) if pd.notna(row.get('cup')) else ''
        doc.legal_urn = str(row.get('legal_urn', ''))
        doc._text = str(row.get('text', '')) if pd.notna(row.get('text')) else str(row.get('_text', ''))
        
        # Additional fields that might be present
        if 'doc_type' in df.columns:
            doc.doc_type = str(row.get('doc_type', ''))
        if 'category' in df.columns:
            doc.category = str(row.get('category', ''))
        if 'veridicità_score' in df.columns:
            try:
                doc.veridicita_score = float(row.get('veridicità_score', 0.0)) if pd.notna(row.get('veridicità_score')) else 0.0
            except (ValueError, TypeError):
                doc.veridicita_score = 0.0
        if 'anomalie' in df.columns:
            doc.anomalie = str(row.get('anomalie', '')) if pd.notna(row.get('anomalie')) else ''
        
        # Create AdministrativeEvent using the factory
        try:
            event = factory.create_event(doc)
            events.append(event)
        except Exception:
            # If factory creation fails, create a basic event manually
            # This ensures we don't lose data even if factory has issues
            event = AdministrativeEvent(
                event_type=row.get('category', 'Generic'),
                document_type=row.get('doc_type', 'Generic'),
                document_id=Path(doc.pdf_name).stem,
                document_number=doc.numero_atto,
                document_date=doc.data_atto,
                title=doc.oggetto,
                economic_value=doc.importo_max,
                cig=doc.cig,
                cup=doc.cup,
                actors=[],
                confidence=0.5,  # Default confidence when factory fails
                raw_text=doc._text,
                metadata={"urn": doc.legal_urn, "source_file": doc.pdf_name},
            )
            events.append(event)
    
    return events


def load_parsed_documents(ente: str) -> List[ParsedDocument]:
    """
    Load data for an entity and convert to ParsedDocument objects.
    
    Args:
        ente: Name of the entity to load data for
        
    Returns:
        List of ParsedDocument objects
    """
    df = load_raw_data(ente)
    if df is None:
        return []
    
    return dataframe_to_parsed_documents(df)


def load_administrative_events(ente: str) -> List[AdministrativeEvent]:
    """
    Load data for an entity and convert to AdministrativeEvent objects.
    
    Args:
        ente: Name of the entity to load data for
        
    Returns:
        List of AdministrativeEvent objects
    """
    df = load_raw_data(ente)
    if df is None:
        return []
    
    return dataframe_to_administrative_events(df)