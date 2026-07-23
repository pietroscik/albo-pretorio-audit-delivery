"""
Module for extracting structured data tables, financial reports, and budget information from documents.
This module implements a layout-aware approach for detecting and parsing tables from both native PDFs
and scanned documents with OCR fallback.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
import pandas as pd
import numpy as np

# Optional imports for advanced table detection
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    import camelot
    CAMELOT_AVAILABLE = True
except ImportError:
    CAMELOT_AVAILABLE = False

try:
    import tabula
    TABULA_AVAILABLE = True
except ImportError:
    TABULA_AVAILABLE = False

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# Setup logger
logger = logging.getLogger(__name__)


@dataclass
class TableElement:
    """Represents a detected table element with position and content."""
    page_number: int
    bbox: tuple  # (x0, y0, x1, y1) coordinates
    headers: List[str]
    data: List[List[Any]]
    confidence: float  # Detection confidence score
    table_type: str  # 'financial', 'budget', 'schedule', 'general', etc.


@dataclass
class LayoutAwareResult:
    """Complete result of layout-aware document analysis."""
    text_elements: List[Dict[str, Any]]  # Regular text blocks
    table_elements: List[TableElement]  # Detected tables
    image_elements: List[Dict[str, Any]]  # Images with bounding boxes
    metadata: Dict[str, Any]  # Document metadata and processing info


class TabularExtractor:
    """
    Advanced tabular data extractor that implements layout-aware document analysis
    with document triage capabilities to optimize processing based on document type.
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.ocr_enabled = self.config.get('ocr_enabled', True)
        self.table_detection_enabled = self.config.get('table_detection_enabled', True)
        self.financial_table_keywords = self.config.get('financial_table_keywords', [
            'quadro economico', 'bilancio', 'rendiconto', 'conto', 'finanziario', 'economico',
            'importi', 'spese', 'entrate', 'costi', 'ricavi', 'investimenti', 'fondo',
            'previsioni', 'accertamenti', 'impegni', 'cassa', 'competenza', 'residui'
        ])

    def detect_document_layout_type(self, pdf_path: Union[str, Path]) -> str:
        """
        Detects the document layout type to route to the most appropriate processing engine.
        Returns 'native_text', 'scanned_image', 'mixed_content', 'table_heavy', or 'text_heavy'.
        """
        try:
            with pdfplumber.open(pdf_path) as pdf:
                first_page = pdf.pages[0] if pdf.pages else None
                
                if not first_page:
                    return 'scanned_image'  # Empty PDF, assume scanned
                
                # Check for text content ratio
                text_content = first_page.extract_text() or ""
                text_ratio = len(text_content) / max(len(first_page.chars), 1)
                
                # Check for table-like structures
                tables = first_page.find_tables()
                has_tables = len(tables) > 0
                
                # Analyze page layout
                chars_density = len(first_page.chars) / (first_page.width * first_page.height)
                
                if chars_density < 0.01:  # Very sparse character distribution
                    return 'scanned_image'
                elif has_tables and text_ratio > 0.3:
                    return 'table_heavy'
                elif text_ratio > 0.7:
                    return 'text_heavy'
                else:
                    return 'mixed_content'
                    
        except Exception as e:
            logger.warning(f"Could not detect document layout type, assuming scanned: {e}")
            return 'scanned_image'

    def extract_tables_native_pdf(self, pdf_path: Union[str, Path]) -> List[TableElement]:
        """
        Extracts tables from native PDFs using pdfplumber or camelot for high-accuracy extraction.
        """
        tables = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    # Find tables on the page
                    page_tables = page.find_tables()
                    
                    for table_idx, table_data in enumerate(page_tables):
                        # Convert table data to proper format
                        if table_data and len(table_data) > 0:
                            headers = table_data[0] if table_data else []
                            data_rows = table_data[1:] if len(table_data) > 1 else []
                            
                            # Determine table type based on content
                            table_type = self._classify_table_type(headers, data_rows)
                            
                            # Calculate bounding box (approximate)
                            bbox = self._calculate_table_bbox(table_data, page)
                            
                            table_element = TableElement(
                                page_number=page_num,
                                bbox=bbox,
                                headers=headers,
                                data=data_rows,
                                confidence=0.9,  # High confidence for native PDF extraction
                                table_type=table_type
                            )
                            tables.append(table_element)
                            
        except Exception as e:
            logger.error(f"Error extracting tables from native PDF: {e}")
            
        return tables

    def _classify_table_type(self, headers: List[str], data: List[List[Any]]) -> str:
        """Classifies table type based on headers and content keywords."""
        if not headers:
            return 'general'
            
        header_text = ' '.join(str(h) for h in headers if h).lower()
        content_text = ' '.join(str(cell) for row in data for cell in row if cell).lower()
        combined_text = header_text + ' ' + content_text
        
        # Check for financial indicators
        for keyword in self.financial_table_keywords:
            if keyword.lower() in combined_text:
                return 'financial'
                
        # Check for budget indicators
        budget_keywords = ['bilancio', 'budget', 'rendiconto', 'previsione', 'consuntivo', 'variazione']
        for keyword in budget_keywords:
            if keyword.lower() in combined_text:
                return 'budget'
                
        # Check for schedule indicators
        schedule_keywords = ['scheda', 'quadro', 'allegato', 'tabella', 'elenco']
        for keyword in schedule_keywords:
            if keyword.lower() in combined_text:
                return 'schedule'
                
        return 'general'

    def _calculate_table_bbox(self, table_data: List[List[Any]], page) -> tuple:
        """Calculates approximate bounding box for a table."""
        # This is a simplified calculation - in practice, you'd track actual coordinates
        return (50, 50, page.width - 50, page.height - 50)  # Default margins

    def extract_tables_ocr_based(self, pdf_path: Union[str, Path]) -> List[TableElement]:
        """
        Extracts tables from scanned PDFs using OCR-based approaches and layout detection.
        This is a simplified implementation - in production, would use unstructured.io or similar.
        """
        tables = []
        try:
            # For now, we'll simulate the OCR-based table extraction
            # In a real implementation, this would use computer vision and OCR to detect
            # table structures in scanned documents
            logger.info(f"Performing OCR-based table extraction for: {pdf_path}")
            
            # This is where we would integrate with unstructured.io or similar
            # For now, return empty list as placeholder
            pass
            
        except Exception as e:
            logger.error(f"Error in OCR-based table extraction: {e}")
            
        return tables

    def extract_structured_data(self, pdf_path: Union[str, Path]) -> LayoutAwareResult:
        """
        Main entry point for layout-aware document analysis that implements document triage.
        """
        pdf_path = Path(pdf_path)
        layout_type = self.detect_document_layout_type(pdf_path)
        logger.info(f"Document layout type detected as: {layout_type} for {pdf_path.name}")
        
        text_elements = []
        table_elements = []
        image_elements = []
        
        if layout_type in ['native_text', 'text_heavy', 'table_heavy', 'mixed_content']:
            # Process as native PDF with potential for structured data extraction
            if self.table_detection_enabled and layout_type in ['table_heavy', 'mixed_content']:
                table_elements = self.extract_tables_native_pdf(pdf_path)
                logger.info(f"Extracted {len(table_elements)} tables from native PDF")
            
            # Extract regular text content
            try:
                with pdfplumber.open(pdf_path) as pdf:
                    for page_num, page in enumerate(pdf.pages, 1):
                        text = page.extract_text() or ""
                        if text.strip():  # Only add non-empty text elements
                            text_elements.append({
                                'page_number': page_num,
                                'bbox': (0, 0, page.width, page.height),  # Full page
                                'text': text,
                                'element_type': 'paragraph'
                            })
            except Exception as e:
                logger.error(f"Error extracting text from PDF: {e}")
                
        elif layout_type == 'scanned_image' and self.ocr_enabled:
            # Process as scanned document with OCR
            logger.info(f"Processing scanned document with OCR: {pdf_path.name}")
            # In a full implementation, this would use OCR-based table detection
            table_elements = self.extract_tables_ocr_based(pdf_path)
            
        else:
            logger.warning(f"Unsupported layout type or OCR disabled: {layout_type}")
            
        return LayoutAwareResult(
            text_elements=text_elements,
            table_elements=table_elements,
            image_elements=image_elements,
            metadata={
                'source_file': str(pdf_path),
                'layout_type': layout_type,
                'tables_found': len(table_elements),
                'text_elements_found': len(text_elements),
                'processing_timestamp': pd.Timestamp.now()
            }
        )

    def convert_tables_to_dataframe(self, table_elements: List[TableElement]) -> List[pd.DataFrame]:
        """
        Converts extracted table elements to pandas DataFrames for further processing.
        """
        dataframes = []
        for table_elem in table_elements:
            try:
                # Create DataFrame from headers and data
                df = pd.DataFrame(table_elem.data, columns=table_elem.headers if table_elem.headers else [f"Col_{i}" for i in range(len(table_elem.data[0]) if table_elem.data else [])])
                dataframes.append(df)
            except Exception as e:
                logger.error(f"Error converting table element to DataFrame: {e}")
                continue
                
        return dataframes

    def normalize_financial_tables(self, dataframes: List[pd.DataFrame]) -> List[pd.DataFrame]:
        """
        Applies normalization rules specifically for financial and budget tables.
        """
        normalized_dfs = []
        for df in dataframes:
            try:
                # Clean and normalize the dataframe
                normalized_df = self._normalize_financial_dataframe(df.copy())
                if not normalized_df.empty:
                    normalized_dfs.append(normalized_df)
            except Exception as e:
                logger.error(f"Error normalizing financial DataFrame: {e}")
                continue
                
        return normalized_dfs

    def _normalize_financial_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Applies normalization rules to financial dataframes."""
        if df.empty:
            return df
            
        # Clean column names
        df.columns = [str(col).strip().lower().replace(' ', '_').replace('-', '_') for col in df.columns]
        
        # Look for common financial indicators in column names and normalize
        financial_indicators = ['importo', 'amount', 'totale', 'tot', 'somma', 'euro', '€', 'spesa', 'entrata', 'costo', 'ricavo']
        for col in df.columns:
            # Try to identify and standardize numeric columns
            if any(indicator in col.lower() for indicator in financial_indicators):
                # Attempt to convert to numeric, handling various formats
                df[col] = pd.to_numeric(df[col].astype(str).str.replace('€', '').str.replace(',', '').str.replace('.', ''), errors='coerce')
                
        return df