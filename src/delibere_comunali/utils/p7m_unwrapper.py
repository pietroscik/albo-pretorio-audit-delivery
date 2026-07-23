"""
Module for unwrapping P7M digital signature envelopes to extract the original PDF content.
This module handles the extraction of embedded PDF documents from PKCS#7 signature containers.
"""

import subprocess
import logging
import platform
from pathlib import Path
from typing import Optional
from .p7m import extract_embedded_content

logger = logging.getLogger(__name__)

def unwrap_p7m_file(p7m_path: Path, output_pdf_path: Optional[Path] = None) -> Optional[Path]:
    """
    Unwrap a P7M digital signature envelope to extract the original PDF content.
    
    Args:
        p7m_path: Path to the .p7m file containing the signed document
        output_pdf_path: Optional path for the extracted PDF. If None, uses same name without .p7m extension
    
    Returns:
        Path to the extracted PDF file, or None if extraction failed
    """
    try:
        # If no output path is specified, use the input path without the .p7m extension
        if output_pdf_path is None:
            output_pdf_path = p7m_path.with_suffix('')
        
        # Try using our existing p7m utility first (handles SignedData containers)
        try:
            extracted_path = extract_embedded_content(p7m_path, output_pdf_path)
            logger.info(f"Successfully extracted content from {p7m_path.name} using asn1crypto method")
            return extracted_path
        except Exception as e:
            logger.debug(f"asn1crypto method failed for {p7m_path.name}: {e}")
            # Fall back to openssl method
            pass
        
        # Fallback: Use OpenSSL command line tool
        # Detect platform to use appropriate command
        if platform.system() == "Windows":
            # On Windows, look for openssl.exe in common locations
            openssl_cmd = "openssl.exe"
        else:
            openssl_cmd = "openssl"
        
        # Check if openssl is available
        try:
            subprocess.run([openssl_cmd, "version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.warning(f"OpenSSL not found or not working, skipping extraction for {p7m_path.name}")
            return None
        
        cmd = [
            openssl_cmd, "smime", "-verify", "-noverify", 
            "-in", str(p7m_path), 
            "-inform", "DER", 
            "-out", str(output_pdf_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0 or output_pdf_path.exists():
            logger.info(f"Successfully extracted content from {p7m_path.name} using OpenSSL method")
            return output_pdf_path
        else:
            logger.warning(f"OpenSSL extraction failed for {p7m_path.name}: {result.stderr}")
            return None
            
    except Exception as e:
        logger.error(f"Failed to unwrap P7M file {p7m_path.name}: {e}")
        return None

def process_p7m_files_in_directory(directory: Path) -> None:
    """
    Process all P7M files in a directory, extracting their content and organizing files appropriately.
    
    Args:
        directory: Directory containing P7M files to process
    """
    p7m_files = list(directory.glob("*.p7m")) + list(directory.glob("*.P7M"))
    
    logger.info(f"Found {len(p7m_files)} P7M files to process in {directory}")
    
    for p7m_file in p7m_files:
        # Create path for extracted PDF (remove .p7m extension)
        extracted_pdf_path = p7m_file.with_suffix('')
        
        # Check if we already have an extracted version
        if extracted_pdf_path.exists():
            logger.debug(f"Extracted file already exists: {extracted_pdf_path.name}")
            continue
            
        # Try to unwrap the P7M file
        result_path = unwrap_p7m_file(p7m_path=p7m_file, output_pdf_path=extracted_pdf_path)
        
        if result_path and result_path.exists():
            logger.info(f"Successfully processed {p7m_file.name} -> {result_path.name}")
            
            # Optionally, move the original P7M to a separate directory for archival
            archive_dir = directory / "p7m_archives"
            archive_dir.mkdir(exist_ok=True)
            
            archived_p7m = archive_dir / p7m_file.name
            p7m_file.rename(archived_p7m)
            logger.info(f"Archived original P7M: {archived_p7m.name}")
        else:
            logger.warning(f"Failed to extract content from {p7m_file.name}")