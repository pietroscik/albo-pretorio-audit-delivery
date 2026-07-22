"""
OCR processing module with parallel processing optimization.
This module extends the original ocr_processor.py with:
- Parallel processing using ThreadPoolExecutor
- Batch processing with configurable workers
- Progress tracking with tqdm
- Memory-efficient processing
"""

import io
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import partial
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import cv2
import fitz  # PyMuPDF
import numpy as np
import pytesseract
from PIL import Image

from ..utils.config import get_config
from ..utils.metrics_collector import get_metrics_collector
from ..utils.optional_deps import import_optional_dependency

# Setup logger
logger = logging.getLogger(__name__)

# Try to import OCR-related optional dependencies
cv2_available = import_optional_dependency("cv2")
pytesseract_available = import_optional_dependency("pytesseract")
fitz_available = import_optional_dependency("fitz")  # PyMuPDF


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
    Optimized version with parallel processing option.

    Args:
        pdf_path: Path to the PDF file
        use_parallel: Whether to use parallel processing for OCR
        max_workers: Maximum number of parallel workers

    Returns:
        Extracted text from the PDF
    """
    # First, check if the PDF is scanned
    if is_pdf_scanned(pdf_path):
        logger.info(f"PDF appears to be scanned, using OCR: {pdf_path}")
        if use_parallel:
            return extract_text_from_scanned_pdf_parallel(
                pdf_path, max_workers=max_workers
            )
        else:
            return extract_text_from_scanned_pdf(pdf_path)
    else:
        logger.info(f"PDF contains native text, using direct extraction: {pdf_path}")
        # Fall back to the standard text extraction
        from .text_extractor import extract_text_pdf

        return extract_text_pdf(pdf_path)


def process_single_pdf_ocr(
    pdf_file: Path,
    output_dir: Path = None,
    use_parallel: bool = True,
    max_workers: int = 4,
) -> Tuple[str, str]:
    """
    Process a single PDF file with OCR if needed.
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
        text = extract_text_with_fallback_optimized(pdf_file, use_parallel, max_workers)
        processing_time = time.time() - start_time

        # Record metrics
        ente = pdf_file.parent.parent.name  # Extract ente from grandparent directory
        is_scanned = is_pdf_scanned(pdf_file)
        processing_method = (
            "ocr_parallel"
            if is_scanned and use_parallel
            else ("ocr_sequential" if is_scanned else "standard")
        )
        document_type = "scanned_pdf" if is_scanned else "native_pdf"

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
    Batch extract text from PDFs in a directory, using OCR when necessary.
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

    return cv2_available and pytesseract_available and fitz_available
