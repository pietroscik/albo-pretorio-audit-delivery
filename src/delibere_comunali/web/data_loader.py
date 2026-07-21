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
    # Convert DataFrame rows to ParsedDocument instances
    documents = []
    for _, row in df.iterrows():
        # Prepare data dictionary mapping CSV column names to ParsedDocument fields
        doc_data = {}
        for col in row.index:
            if pd.notna(row[col]):
                # Map common column names to ParsedDocument field names
                if col == 'id':
                    # Skip 'id' as it's not a field in ParsedDocument
                    continue
                elif col == 'filename':
                    doc_data['pdf_name'] = str(row[col])
                elif col == 'text':
                    doc_data['text_preview'] = str(row[col])
                elif col == 'text_complete':
                    doc_data['text_complete'] = str(row[col])
                elif col == 'importo_max':
                    try:
                        doc_data[col] = float(row[col]) if pd.notna(row[col]) else 0.0
                    except (ValueError, TypeError):
                        doc_data[col] = 0.0
                elif col in ['beneficiario', 'responsabile', 'oggetto', 'doc_type', 
                             'data_atto', 'cig', 'cup', 'iban', 'numero_atto']:
                    doc_data[col] = str(row[col]) if pd.notna(row[col]) else ''
                else:
                    # Direct mapping for fields that match ParsedDocument field names
                    doc_data[col] = row[col]
        
        # Create ParsedDocument instance using from_dict method
        doc = ParsedDocument.from_dict(doc_data)
        documents.append(doc)

    return documents


def load_parsed_documents(ente: str) -> List[ParsedDocument]:
    """
    Load parsed documents for a given entity.
    
    Args:
        ente: Name of the entity to load data for
        
    Returns:
        List of ParsedDocument objects
    """
    df = load_raw_data(ente)
    if df is None:
        return []
    
    return dataframe_to_parsed_documents(df)


def dataframe_to_administrative_events(df: pd.DataFrame) -> List[AdministrativeEvent]:
    """
    Transform a DataFrame into a list of AdministrativeEvent objects.
    
    Args:
        df: DataFrame containing parsed document data
        
    Returns:
        List of AdministrativeEvent objects
    """
    events = []
    for _, row in df.iterrows():
        # Use AdministrativeEvent.from_dict to create events from row data
        try:
            event = AdministrativeEvent.from_dict(row.to_dict())
            events.append(event)
        except Exception:
            # If direct creation fails, create a basic event using DigitalTwinEventFactory
            # First convert the row to a ParsedDocument, then create event from it
            doc_data = {}
            for col in row.index:
                if pd.notna(row[col]):
                    if col == 'id':
                        continue
                    elif col == 'filename':
                        doc_data['pdf_name'] = str(row[col])
                    elif col == 'text':
                        doc_data['text_preview'] = str(row[col])
                    elif col == 'text_complete':
                        doc_data['text_complete'] = str(row[col])
                    elif col == 'importo_max':
                        try:
                            doc_data[col] = float(row[col]) if pd.notna(row[col]) else 0.0
                        except (ValueError, TypeError):
                            doc_data[col] = 0.0
                    elif col in ['beneficiario', 'responsabile', 'oggetto', 'doc_type', 
                                 'data_atto', 'cig', 'cup', 'iban', 'numero_atto']:
                        doc_data[col] = str(row[col]) if pd.notna(row[col]) else ''
                    else:
                        doc_data[col] = row[col]
            
            doc = ParsedDocument.from_dict(doc_data)
            factory = DigitalTwinEventFactory()
            event = factory.create_event(doc)
            events.append(event)
    
    return events


def load_administrative_events(ente: str) -> List[AdministrativeEvent]:
    """
    Load administrative events for a given entity.
    
    Args:
        ente: Name of the entity to load data for
        
    Returns:
        List of AdministrativeEvent objects
    """
    df = load_raw_data(ente)
    if df is None:
        return []
    
    return dataframe_to_administrative_events(df)