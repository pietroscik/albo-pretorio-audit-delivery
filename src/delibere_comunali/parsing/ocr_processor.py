"""
OCR processing module for scanned PDF documents.
Integrates with the new modular framework to handle documents without native text.
"""

import cv2
import numpy as np
import pytesseract
from PIL import Image
import fitz  # PyMuPDF
from pathlib import Path
from typing import Optional, Union
import logging
import time

from ..utils.config import get_config
from .text_extractor import extract_text_pdf
from ..utils.optional_deps import import_optional_dependency
from ..utils.metrics_collector import get_metrics_collector

# Setup logger
logger = logging.getLogger(__name__)

# Try to import OCR-related optional dependencies
cv2_available = import_optional_dependency('cv2')
pytesseract_available = import_optional_dependency('pytesseract')
fitz_available = import_optional_dependency('fitz')  # PyMuPDF


def is_pdf_scanned(pdf_path: Union[str, Path]) -> bool:
    """
    Determine if a PDF is scanned (image-based) or contains native text.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        True if the PDF is scanned, False if it contains native text
    """
    if not cv2_available or not pytesseract_available or not fitz_available:
        logger.warning("OCR dependencies not available, assuming PDF contains native text")
        return False
    
    try:
        # Open PDF with PyMuPDF
        doc = fitz.open(str(pdf_path))
        
        # Check first few pages for text content
        for page_num in range(min(3, len(doc))):  # Check first 3 pages or all pages if less
            page = doc[page_num]
            text = page.get_text()
            
            # If we find substantial text content, it's likely not scanned
            if len(text.strip()) > 50:  # More than 50 characters of text
                doc.close()
                return False
        
        doc.close()
        return True
    except Exception as e:
        logger.error(f"Error checking if PDF is scanned: {e}")
        return False


def preprocess_image_for_ocr(image: np.ndarray) -> np.ndarray:
    """
    Preprocess image to improve OCR accuracy.
    
    Args:
        image: Input image array
        
    Returns:
        Preprocessed image array
    """
    if not cv2_available:
        logger.warning("OpenCV not available, skipping image preprocessing")
        return image
    
    # Convert to grayscale if needed
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    
    # Apply Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Threshold the image to get a binary image
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Apply morphological operations to enhance text
    kernel = np.ones((1, 1), np.uint8)
    processed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    
    return processed


def extract_text_from_scanned_pdf(pdf_path: Union[str, Path], page_numbers: Optional[list] = None) -> str:
    """
    Extract text from a scanned PDF using OCR.
    
    Args:
        pdf_path: Path to the scanned PDF file
        page_numbers: List of specific page numbers to process (0-indexed). If None, process all pages.
        
    Returns:
        Extracted text from the PDF
    """
    if not cv2_available or not pytesseract_available or not fitz_available:
        raise RuntimeError(
            "Required OCR dependencies (cv2, pytesseract, fitz) are not available. "
            "Please install opencv-python, pytesseract, and PyMuPDF."
        )
    
    try:
        # Start timing for metrics
        start_time = time.time()
        
        # Open PDF with PyMuPDF
        doc = fitz.open(str(pdf_path))
        
        # Determine which pages to process
        if page_numbers is None:
            page_range = range(len(doc))
        else:
            page_range = [pn for pn in page_numbers if 0 <= pn < len(doc)]
        
        extracted_text = []
        
        for page_num in page_range:
            page = doc[page_num]
            
            # Get the pixmap (image) of the page
            pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))  # Scale to 300 DPI
            
            # Convert to numpy array
            img_data = pix.tobytes("png")
            img_array = np.frombuffer(img_data, dtype=np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            
            if img is None:
                logger.warning(f"Could not decode page {page_num} as image")
                continue
            
            # Preprocess image for better OCR
            processed_img = preprocess_image_for_ocr(img)
            
            # Perform OCR
            text = pytesseract.image_to_string(processed_img, lang='ita')
            extracted_text.append(text)
        
        doc.close()
        
        # Record metrics
        processing_time = time.time() - start_time
        ente = Path(pdf_path).parent.parent.name  # Extract ente from path structure
        metrics_collector = get_metrics_collector()
        metrics_collector.record_document_processed(
            document_type='scanned_pdf',
            processing_method='ocr',
            ente=ente,
            processing_time_sec=processing_time
        )
        
        return "\n".join(extracted_text)
    
    except Exception as e:
        logger.error(f"Error extracting text from scanned PDF {pdf_path}: {e}")
        
        # Record error metrics
        ente = Path(pdf_path).parent.parent.name  # Extract ente from path structure
        metrics_collector = get_metrics_collector()
        metrics_collector.record_error(
            error_type='ocr_failure',
            module='ocr_processor',
            ente=ente,
            details=str(e)
        )
        
        return ""


def extract_text_with_fallback(pdf_path: Union[str, Path]) -> str:
    """
    Extract text from PDF with fallback to OCR if the PDF is scanned.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Extracted text from the PDF
    """
    # First, check if the PDF is scanned
    if is_pdf_scanned(pdf_path):
        logger.info(f"PDF appears to be scanned, using OCR: {pdf_path}")
        return extract_text_from_scanned_pdf(pdf_path)
    else:
        logger.info(f"PDF contains native text, using direct extraction: {pdf_path}")
        # Fall back to the standard text extraction
        return extract_text_pdf(pdf_path)


def batch_extract_text_with_ocr(pdf_directory: Union[str, Path], output_directory: Union[str, Path] = None) -> dict:
    """
    Batch extract text from PDFs in a directory, using OCR when necessary.
    
    Args:
        pdf_directory: Directory containing PDF files
        output_directory: Directory to save extracted text files (optional)
        
    Returns:
        Dictionary mapping PDF filenames to extracted text
    """
    import time
    pdf_dir = Path(pdf_directory)
    output_dir = Path(output_directory) if output_directory else None
    
    results = {}
    
    for pdf_file in pdf_dir.glob("*.pdf"):
        try:
            start_time = time.time()
            text = extract_text_with_fallback(pdf_file)
            processing_time = time.time() - start_time
            
            results[pdf_file.name] = text
            
            # Record metrics
            ente = pdf_dir.parent.name  # Extract ente from parent directory
            is_scanned = is_pdf_scanned(pdf_file)
            processing_method = 'ocr' if is_scanned else 'standard'
            document_type = 'scanned_pdf' if is_scanned else 'native_pdf'
            
            metrics_collector = get_metrics_collector()
            metrics_collector.record_document_processed(
                document_type=document_type,
                processing_method=processing_method,
                ente=ente,
                processing_time_sec=processing_time
            )
            
            if output_dir:
                output_dir.mkdir(parents=True, exist_ok=True)
                output_file = output_dir / f"{pdf_file.stem}.txt"
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(text)
        except Exception as e:
            logger.error(f"Error processing {pdf_file}: {e}")
            
            # Record error metrics
            ente = pdf_dir.parent.name
            metrics_collector = get_metrics_collector()
            metrics_collector.record_error(
                error_type='batch_processing_error',
                module='ocr_processor',
                ente=ente,
                details=str(e)
            )
            
            results[pdf_file.name] = ""
    
    return results


# Test function for development purposes
def test_ocr_integration():
    """
    Test function to verify OCR integration works correctly.
    """
    import tempfile
    
    # This is just a placeholder test - in real usage, you'd have actual PDFs to test
    print("OCR processor module loaded successfully")
    print(f"OpenCV available: {cv2_available is not None}")
    print(f"Pytesseract available: {pytesseract_available is not None}")
    print(f"PyMuPDF available: {fitz_available is not None}")
    
    return cv2_available and pytesseract_available and fitz_available