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
    Determines if a PDF contains scanned images rather than native text.
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        True if the PDF appears to be scanned, False otherwise
    """
    try:
        # Import locally to avoid circular import
        from .text_extractor import extract_text_pdf
        
        # Extract a small amount of text to check if the PDF has native text
        text_sample = extract_text_pdf(pdf_path, max_pages=2)
        
        doc = fitz.open(str(pdf_path))
        total_pages = len(doc)
        
        # Check if the pages contain more images than text
        image_count = 0
        page_count = min(total_pages, 3)  # Check first 3 pages
        
        for page_num in range(page_count):
            page = doc[page_num]
            # Count images on the page
            img_list = page.get_images()
            if len(img_list) > 0:
                image_count += len(img_list)
        
        doc.close()
        
        # If we have images but little text, it's likely a scanned PDF
        text_length = len(text_sample.strip()) if text_sample else 0
        
        # Heuristic: if there are images and little text, consider it scanned
        return image_count > 0 and text_length < 100
    except Exception as e:
        logger.warning(f"Could not determine if PDF is scanned: {e}")
        return True  # Default to assuming it's scanned if we can't determine


def preprocess_image_for_ocr(image: Image.Image) -> Image.Image:
    """
    Preprocess an image to improve OCR accuracy.
    
    Args:
        image: Input PIL Image
        
    Returns:
        Preprocessed PIL Image
    """
    try:
        # Convert PIL image to OpenCV format
        opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # Convert to grayscale
        gray = cv2.cvtColor(opencv_image, cv2.COLOR_BGR2GRAY)
        
        # Apply threshold to get image with only black and white
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Denoise
        denoised = cv2.medianBlur(thresh, 3)
        
        # Convert back to PIL format
        processed_image = Image.fromarray(denoised)
        
        return processed_image
    except Exception as e:
        logger.error(f"Error preprocessing image for OCR: {e}")
        return image  # Return original image if preprocessing fails


def extract_text_from_scanned_pdf(pdf_path: Union[str, Path], dpi: int = 300) -> str:
    """
    Extracts text from a scanned PDF using OCR.
    
    Args:
        pdf_path: Path to the scanned PDF file
        dpi: DPI for image conversion (higher = better quality but slower)
        
    Returns:
        Extracted text from the PDF
    """
    try:
        doc = fitz.open(str(pdf_path))
        extracted_text = ""
        
        for page_num in range(len(doc)):
            # Get the page
            page = doc.load_page(page_num)
            
            # Convert to image (pixmap)
            mat = fitz.Matrix(dpi / 72, dpi / 72)  # 72 is default DPI
            pix = page.get_pixmap(matrix=mat)
            
            # Convert pixmap to bytes and then to PIL Image
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            
            # Perform OCR
            text = pytesseract.image_to_string(img)
            extracted_text += text + "\n"
        
        doc.close()
        return extracted_text
    except Exception as e:
        logger.error(f"Error extracting text from scanned PDF: {e}")
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