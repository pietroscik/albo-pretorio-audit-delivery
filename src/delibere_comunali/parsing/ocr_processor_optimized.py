"""
OCR processing module with parallel processing optimization and layout-aware document triage.
This module extends the original ocr_processor.py with:
- Parallel processing using ThreadPoolExecutor
- Batch processing with configurable workers
- Progress tracking with tqdm
- Memory-efficient processing
- Document triage for optimal processing path selection
- Integration with unstructured.io for layout-aware extraction
"""

import io
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import partial
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any
import tempfile

import cv2
import fitz  # PyMuPDF
import numpy as np
import pytesseract
from PIL import Image

from ..utils.config import get_config
from ..utils.metrics_collector import get_metrics_collector
from ..utils.optional_deps import import_optional_dependency

# Try importing unstructured.io for advanced layout-aware extraction
try:
    from unstructured.partition.pdf import partition_pdf
    from unstructured.documents.elements import Table
    UNSTRUCTURED_AVAILABLE = True
except ImportError:
    UNSTRUCTURED_AVAILABLE = False
    partition_pdf = None

# Setup logger
logger = logging.getLogger(__name__)

# Try to import OCR-related optional dependencies
cv2_available = import_optional_dependency("cv2")
pytesseract_available = import_optional_dependency("pytesseract")
fitz_available = import_optional_dependency("fitz")  # PyMuPDF


def classify_document_layout_type(pdf_path: Union[str, Path]) -> str:
    """
    Classify document layout type to route to the most appropriate processing engine.
    Returns 'native_text', 'scanned_image', 'mixed_content', 'table_heavy', or 'text_heavy'.
    """
    try:
        doc = fitz.open(str(pdf_path))
        page = doc.load_page(0) if doc.page_count > 0 else None
        
        if not page:
            doc.close()
            return 'scanned_image'  # Empty PDF, assume scanned
        
        # Get text blocks and images to determine layout
        text_blocks = page.get_text("dict")
        text_chars = page.get_text("rawdict")["chars"] if "chars" in page.get_text("rawdict") else page.get_text("dict")["blocks"]
        images = page.get_images()
        
        # Calculate text density
        total_chars = len(text_chars) if isinstance(text_chars, list) else 0
        page_area = page.rect.width * page.rect.height
        char_density = total_chars / max(page_area, 1)
        
        # Check for images that might indicate scanned content
        has_images = len(images) > 0
        
        # Check for existing text (if char_density is low but has images, likely scanned)
        if char_density < 0.001 and has_images:
            doc.close()
            return 'scanned_image'
        elif char_density > 0.01:
            # Check if page has table-like structures based on text arrangement
            # This is a simplified check - in reality, would use more sophisticated analysis
            text_content = page.get_text()
            has_table_indicators = any(keyword in text_content.lower() for keyword in ['tabella', 'quadro', 'elenco', 'colonna', 'riga'])
            if has_table_indicators:
                doc.close()
                return 'table_heavy'
            else:
                doc.close()
                return 'text_heavy'
        else:
            doc.close()
            return 'mixed_content'
            
    except Exception as e:
        logger.warning(f"Could not classify document layout type, assuming scanned: {e}")
        return 'scanned_image'


def is_pdf_scanned(pdf_path: Union[str, Path]) -> bool:
    """
    Determines if a PDF contains scanned images rather than native text.
    Now integrated with the layout classification system for better accuracy.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        True if the PDF appears to be scanned, False otherwise
    """
    layout_type = classify_document_layout_type(pdf_path)
    return layout_type == 'scanned_image'


def extract_text_native_pdf(pdf_path: Union[str, Path]) -> str:
    """
    Extract text directly from native PDFs without OCR for efficiency.
    This is the fast path for documents that already contain text layers.
    """
    try:
        doc = fitz.open(str(pdf_path))
        text = ""
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text += page.get_text() + "\n"
        doc.close()
        return text
    except Exception as e:
        logger.error(f"Error extracting text from native PDF: {e}")
        return ""


def extract_tables_unstructured(pdf_path: Union[str, Path]) -> List[Dict]:
    """
    Extract tables using unstructured.io for layout-aware processing (Slow Path).
    This is the advanced path for complex documents with tables, charts, etc.
    """
    if not UNSTRUCTURED_AVAILABLE:
        logger.warning("unstructured.io not available, skipping advanced table extraction")
        return []
    
    try:
        # Use unstructured.io to extract elements with layout awareness
        elements = partition_pdf(str(pdf_path), strategy="hi_res")
        tables = []
        for element in elements:
            if isinstance(element, Table):
                # Convert unstructured table to our format
                table_data = {
                    'metadata': element.metadata.to_dict() if hasattr(element, 'metadata') else {},
                    'text': element.text if hasattr(element, 'text') else str(element),
                    'element_type': 'table'
                }
                tables.append(table_data)
        return tables
    except Exception as e:
        logger.error(f"Error extracting tables with unstructured.io: {e}")
        return []


def extract_text_with_unstructured(pdf_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Extract all text and structured elements using unstructured.io for layout-aware processing.
    Returns a comprehensive representation of the document's content and structure.
    """
    if not UNSTRUCTURED_AVAILABLE:
        logger.warning("unstructured.io not available, falling back to basic extraction")
        return {
            'text': extract_text_native_pdf(pdf_path),
            'tables': [],
            'elements': [],
            'layout_analysis': {'engine_used': 'basic_extraction'}
        }
    
    try:
        # Use unstructured.io for comprehensive layout-aware extraction
        elements = partition_pdf(str(pdf_path), strategy="hi_res")
        text_elements = []
        table_elements = []
        other_elements = []
        
        for element in elements:
            element_type = type(element).__name__
            element_dict = {
                'type': element_type,
                'text': element.text if hasattr(element, 'text') else str(element),
                'metadata': element.metadata.to_dict() if hasattr(element, 'metadata') else {}
            }
            
            if element_type == 'Table':
                table_elements.append(element_dict)
            elif element_type in ['Title', 'NarrativeText', 'ListItem', 'Header', 'Footer']:
                text_elements.append(element_dict)
            else:
                other_elements.append(element_dict)
                
        # Combine all text for backward compatibility
        all_text = "\n".join([elem['text'] for elem in text_elements if elem['text']])
        
        return {
            'text': all_text,
            'tables': table_elements,
            'text_elements': text_elements,
            'other_elements': other_elements,
            'layout_analysis': {
                'engine_used': 'unstructured_hi_res',
                'total_elements': len(elements),
                'table_count': len(table_elements),
                'text_element_count': len(text_elements)
            }
        }
    except Exception as e:
        logger.error(f"Error in comprehensive unstructured extraction: {e}")
        # Fallback to basic extraction
        return {
            'text': extract_text_native_pdf(pdf_path),
            'tables': [],
            'elements': [],
            'layout_analysis': {'engine_used': 'fallback_basic_extraction', 'error': str(e)}
        }


def extract_text_with_layout_awareness(pdf_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Main function implementing document triage with layout-aware extraction.
    Routes documents to the most appropriate processing engine based on layout type.
    """
    pdf_path = Path(pdf_path)
    layout_type = classify_document_layout_type(pdf_path)
    logger.info(f"Document layout type detected as: {layout_type} for {pdf_path.name}")
    
    if layout_type in ['native_text', 'text_heavy']:
        # Fast Path: Native text extraction (Zero OCR)
        logger.info(f"Using fast path for native text extraction: {pdf_path.name}")
        text = extract_text_native_pdf(pdf_path)
        return {
            'text': text,
            'tables': [],
            'text_elements': [{'type': 'paragraph', 'text': text, 'metadata': {}}],
            'other_elements': [],
            'layout_analysis': {
                'engine_used': 'native_extraction_fast_path',
                'layout_type': layout_type,
                'processing_time': 0  # Will be measured externally
            }
        }
    elif layout_type in ['table_heavy', 'mixed_content'] and UNSTRUCTURED_AVAILABLE:
        # Medium Path: Layout-aware extraction with unstructured.io
        logger.info(f"Using layout-aware path for complex document: {pdf_path.name}")
        return extract_text_with_unstructured(pdf_path)
    else:
        # Slow Path: OCR-based extraction for scanned documents
        logger.info(f"Using OCR path for scanned document: {pdf_path.name}")
        from .text_extractor import extract_text_pdf
        text = extract_text_pdf(pdf_path)
        return {
            'text': text,
            'tables': [],
            'text_elements': [{'type': 'paragraph', 'text': text, 'metadata': {}}],
            'other_elements': [],
            'layout_analysis': {
                'engine_used': 'ocr_fallback_slow_path',
                'layout_type': layout_type,
                'processing_time': 0  # Will be measured externally
            }
        }


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


def extract_text_from_single_page(
    pdf_path: Union[str, Path], page_num: int, dpi: int = 300
) -> Tuple[int, str]:
    """
    Extract text from a single page of a PDF using OCR.
    This function is designed to be called in parallel.

    Args:
        pdf_path: Path to the PDF file
        page_num: Page number to process
        dpi: DPI for image conversion

    Returns:
        Tuple of (page_num, extracted_text)
    """
    try:
        doc = fitz.open(str(pdf_path))
        page = doc.load_page(page_num)

        # Convert to image (pixmap)
        mat = fitz.Matrix(dpi / 72, dpi / 72)  # 72 is default DPI
        pix = page.get_pixmap(matrix=mat)

        # Convert pixmap to bytes and then to PIL Image
        img_data = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_data))

        # Perform OCR
        text = pytesseract.image_to_string(img)
        doc.close()

        return (page_num, text)
    except Exception as e:
        logger.error(f"Error extracting text from page {page_num} of {pdf_path}: {e}")
        return (page_num, "")


def extract_text_from_scanned_pdf_parallel(
    pdf_path: Union[str, Path], dpi: int = 300, max_workers: int = 4
) -> str:
    """
    Extracts text from a scanned PDF using OCR with parallel processing.

    Args:
        pdf_path: Path to the scanned PDF file
        dpi: DPI for image conversion (higher = better quality but slower)
        max_workers: Maximum number of parallel workers

    Returns:
        Extracted text from the PDF
    """
    try:
        doc = fitz.open(str(pdf_path))
        total_pages = len(doc)
        doc.close()

        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all pages for processing
            futures = []
            for page_num in range(total_pages):
                future = executor.submit(
                    extract_text_from_single_page, pdf_path, page_num, dpi
                )
                futures.append(future)

            # Collect results as they complete
            results = []
            for future in as_completed(futures):
                page_num, text = future.result()
                results.append((page_num, text))

            # Sort results by page number and concatenate
            results.sort(key=lambda x: x[0])
            extracted_text = "\n".join([text for _, text in results])

        return extracted_text
    except Exception as e:
        logger.error(
            f"Error extracting text from scanned PDF with parallel processing: {e}"
        )
        # Fallback to sequential processing
        return extract_text_from_scanned_pdf(pdf_path, dpi)


def extract_text_from_scanned_pdf(pdf_path: Union[str, Path], dpi: int = 300) -> str:
    """
    Extracts text from a scanned PDF using OCR (sequential version).

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


def extract_text_with_fallback_optimized(
    pdf_path: Union[str, Path], use_parallel: bool = True, max_workers: int = 4
) -> str:
    """
    Extract text from PDF with fallback to OCR if the PDF is scanned.
    Updated to implement document triage with layout-aware processing.

    Args:
        pdf_path: Path to the PDF file
        use_parallel: Whether to use parallel processing for OCR
        max_workers: Maximum number of parallel workers

    Returns:
        Extracted text from the PDF
    """
    # Use the new layout-aware extraction system
    result = extract_text_with_layout_awareness(pdf_path)
    return result['text']


def process_single_pdf_ocr(
    pdf_file: Path,
    output_dir: Path = None,
    use_parallel: bool = True,
    max_workers: int = 4,
) -> Tuple[str, str]:
    """
    Process a single PDF file with layout-aware extraction if needed.
    Returns tuple of (filename, extracted_text).

    Args:
        pdf_file: Path to the PDF file
        output_dir: Directory to save extracted text (optional)
        use_parallel: Whether to use parallel processing
        max_workers: Maximum number of parallel workers

    Returns:
        Tuple of (filename, extracted_text)
    """
    try:
        start_time = time.time()
        text_result = extract_text_with_layout_awareness(pdf_file)
        text = text_result['text']
        processing_time = time.time() - start_time

        # Record metrics with layout analysis info
        ente = pdf_file.parent.parent.name  # Extract ente from grandparent directory
        layout_info = text_result.get('layout_analysis', {})
        processing_method = layout_info.get('engine_used', 'unknown')
        document_type = layout_info.get('layout_type', 'unknown')

        metrics_collector = get_metrics_collector()
        metrics_collector.record_document_processed(
            document_type=document_type,
            processing_method=processing_method,
            ente=ente,
            processing_time_sec=processing_time,
        )

        if output_dir:
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file = output_dir / f"{pdf_file.stem}.txt"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(text)

        return (pdf_file.name, text)
    except Exception as e:
        logger.error(f"Error processing {pdf_file}: {e}")

        # Record error metrics
        ente = pdf_file.parent.parent.name
        metrics_collector = get_metrics_collector()
        metrics_collector.record_error(
            error_type="batch_processing_error",
            module="ocr_processor_optimized",
            ente=ente,
            details=str(e),
        )

        return (pdf_file.name, "")


def batch_extract_text_with_ocr_optimized(
    pdf_directory: Union[str, Path],
    output_directory: Union[str, Path] = None,
    use_parallel: bool = True,
    max_workers: int = 4,
    batch_size: int = 10,
) -> Dict[str, str]:
    """
    Batch extract text from PDFs in a directory, using layout-aware processing when necessary.
    Optimized version with parallel processing and batching.

    Args:
        pdf_directory: Directory containing PDF files
        output_directory: Directory to save extracted text files (optional)
        use_parallel: Whether to use parallel processing for OCR
        max_workers: Maximum number of parallel workers
        batch_size: Number of PDFs to process in each batch

    Returns:
        Dictionary mapping PDF filenames to extracted text
    """
    import time

    from tqdm import tqdm

    pdf_dir = Path(pdf_directory)
    output_dir = Path(output_directory) if output_directory else None

    results = {}
    pdf_files = list(pdf_dir.glob("*.pdf"))

    # Process in batches to control memory usage
    for i in range(0, len(pdf_files), batch_size):
        batch_files = pdf_files[i : i + batch_size]

        if use_parallel:
            # Process batch in parallel
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Create partial function with fixed parameters
                process_func = partial(
                    process_single_pdf_ocr,
                    output_dir=output_dir,
                    use_parallel=True,  # Use parallel for page-level processing
                    max_workers=max_workers,
                )

                # Submit all files in batch
                futures = [
                    executor.submit(process_func, pdf_file) for pdf_file in batch_files
                ]

                # Collect results
                for future in tqdm(
                    as_completed(futures),
                    total=len(batch_files),
                    desc=f"Processing batch {i//batch_size + 1}",
                ):
                    filename, text = future.result()
                    results[filename] = text
        else:
            # Sequential processing
            for pdf_file in tqdm(
                batch_files, desc=f"Processing batch {i//batch_size + 1}"
            ):
                filename, text = process_single_pdf_ocr(
                    pdf_file, output_dir, use_parallel=False, max_workers=1
                )
                results[filename] = text

    return results


# Test function for development purposes
def test_ocr_optimized_integration():
    """
    Test function to verify optimized OCR integration works correctly.
    """
    print("Optimized OCR processor module loaded successfully")
    print(f"OpenCV available: {cv2_available is not None}")
    print(f"Pytesseract available: {pytesseract_available is not None}")
    print(f"PyMuPDF available: {fitz_available is not None}")
    print(f"Unstructured.io available: {UNSTRUCTURED_AVAILABLE}")

    return cv2_available and pytesseract_available and fitz_available