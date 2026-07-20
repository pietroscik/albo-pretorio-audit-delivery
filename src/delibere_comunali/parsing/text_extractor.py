import os
import re
import tempfile
from pathlib import Path
from typing import Tuple, Optional
import pypdfium2 as pdfium
from ..utils.logger import get_logger
import time

try:
    import pytesseract
    from PIL import Image
except ImportError:
    pytesseract = None

from ..utils.metrics_collector import get_metrics_collector

logger = get_logger("text_extractor")

logger = get_logger("text_extractor")

class TextExtractor:
    """
    Estrae testo da diversi formati di file (PDF, HTML, P7M).
    Gestisce sia PDF testuali che immagini richiedenti OCR.
    """
    
    def __init__(self, config=None):
        self.config = config or {}
        
        # Configurazione OCR
        if pytesseract:
            tesseract_cmd = getattr(self.config, 'tesseract_cmd', None) if self.config else None
            if tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
                logger.info(f"Tesseract configurato: {tesseract_cmd}")

    def extract(self, file_path: Path, content_bytes: Optional[bytes] = None) -> Tuple[str, str]:
        """
        Estrae testo da un file e ritorna (testo, sorgente).
        Sorgente può essere 'text', 'ocr', 'html', 'p7m_extraction_failed'.
        """
        start_time = time.time()
        
        file_ext = file_path.suffix.lower()
        
        if file_ext in ['.p7m']:
            # Già gestito esternamente in analyze_albo.py
            return "", "p7m_extraction_failed"
        
        if file_ext in ['.html', '.htm']:
            result = self._extract_html(file_path), "html"
        elif file_ext in ['.pdf', '.PDF']:
            result = self._extract_pdf(file_path, content_bytes)
        else:
            # Per altri formati
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    result = f.read(), "text"
            except Exception:
                result = "", "extraction_failed"
        
        # Record metrics
        processing_time = time.time() - start_time
        ente = file_path.parent.parent.name  # Extract ente from parent directory
        document_type = 'pdf' if file_ext in ['.pdf', '.PDF'] else 'html' if file_ext in ['.html', '.htm'] else 'other'
        processing_method = result[1]  # Use source as processing method
        
        metrics_collector = get_metrics_collector()
        metrics_collector.record_document_processed(
            document_type=document_type,
            processing_method=processing_method,
            ente=ente,
            processing_time_sec=processing_time
        )
        
        return result

    def _extract_html(self, file_path: Path) -> Tuple[str, str]:
        """Estrae testo da file HTML."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Rimuovi i tag HTML mantenendo solo il testo
            from html import unescape
            import re
            
            # Rimuove i tag HTML
            clean_text = re.sub(r'<[^>]+>', ' ', content)
            # Decodifica entità HTML
            clean_text = unescape(clean_text)
            # Rimuove spazi multipli
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
            
            return clean_text, "html"
        except Exception as e:
            logger.error(f"Errore nell'estrazione HTML da {file_path}: {e}")
            
            # Record error metrics
            ente = file_path.parent.parent.name
            metrics_collector = get_metrics_collector()
            metrics_collector.record_error(
                error_type='html_extraction_error',
                module='text_extractor',
                ente=ente,
                details=str(e)
            )
            
            return "", "html_extraction_failed"

    def _extract_pdf(self, file_path: Path, content_bytes: Optional[bytes] = None) -> Tuple[str, str]:
        """Estrae testo da file PDF usando varie strategie."""
        if content_bytes:
            # Usa i byte forniti invece del file originale
            temp_pdf_path = Path(tempfile.mktemp(suffix='.pdf'))
            try:
                temp_pdf_path.write_bytes(content_bytes)
                result = self._extract_pdf_from_path(temp_pdf_path, True)
            finally:
                if temp_pdf_path.exists():
                    temp_pdf_path.unlink()
        else:
            result = self._extract_pdf_from_path(file_path, False)
        
        return result

    def _extract_pdf_from_path(self, pdf_path: Path, is_temporary: bool) -> Tuple[str, str]:
        """Estrae testo da PDF usando PDFium2 e OCR fallback."""
        try:
            # Estrazione testo diretta con PDFium2
            pdf = pdfium.PdfDocument(str(pdf_path))
            text_parts = []
            for page_idx in range(len(pdf)):
                page = pdf[page_idx]
                textpage = page.get_textpage()
                text = textpage.get_text_bounded().strip()
                if text:
                    text_parts.append(text)
            full_text = "\n".join(text_parts)
            
            # Se abbiamo ottenuto testo significativo, va bene
            if len(full_text.strip()) > 50:  # soglia minima di testo
                return full_text, "text"
                
        except Exception as e:
            logger.debug(f"Estrazione testo diretta fallita per {pdf_path}: {e}")
        
        # Prima di provare OCR interno, controlliamo se il PDF è effettivamente scansionato
        # usando la funzione specializzata del nuovo modulo OCR
        try:
            # Import localmente per evitare import circolare
            from .ocr_processor import is_pdf_scanned
            if is_pdf_scanned(pdf_path):
                logger.info(f"PDF identificato come scansionato, utilizzo OCR specializzato per {pdf_path}")
                # Usa il nuovo OCR processor per una gestione più sofisticata
                from .ocr_processor import extract_text_from_scanned_pdf
                ocr_text = extract_text_from_scanned_pdf(pdf_path)
                if ocr_text.strip():
                    return ocr_text, "ocr_specialized"
            else:
                logger.info(f"PDF contiene testo nativo ma non sufficiente, tentativo OCR di emergenza per {pdf_path}")
        except Exception as e:
            logger.warning(f"Controllo PDF scansionato fallito per {pdf_path}: {e}")
            # Procedi con OCR di emergenza come fallback
        
        # Se la lettura diretta fallisce o non trova testo sufficiente, prova OCR
        if pytesseract:
            try:
                logger.info(f"OCR richiesto per {pdf_path}")
                # Renderizza il PDF come immagini e applica OCR
                text_parts = []
                pdf = pdfium.PdfDocument(str(pdf_path))
                
                # Prova OCR sulle prime 3 pagine per efficienza
                for page_idx in range(min(3, len(pdf))):
                    page = pdf[page_idx]
                    bitmap = page.render(scale=2.0, rotation=0)  # 2.0 = ~144 DPI
                    pil_image = bitmap.to_pil()
                    
                    # Applica miglioramenti per OCR
                    processed_img = self._enhance_image_for_ocr(pil_image)
                    
                    # Estrai testo con OCR
                    try:
                        ocr_text = pytesseract.image_to_string(processed_img, lang="ita", config="--psm 6")
                    except:
                        # Fallback a lingua inglese se italiano non disponibile
                        ocr_text = pytesseract.image_to_string(processed_img, lang="eng", config="--psm 6")
                    
                    if ocr_text.strip():
                        text_parts.append(ocr_text)
                
                ocr_result = "\n".join(text_parts)
                if ocr_result.strip():
                    return ocr_result, "ocr"
                    
            except Exception as e:
                logger.warning(f"OCR fallito per {pdf_path}: {e}")
                
                # Record error metrics
                ente = pdf_path.parent.parent.name
                metrics_collector = get_metrics_collector()
                metrics_collector.record_error(
                    error_type='internal_ocr_error',
                    module='text_extractor',
                    ente=ente,
                    details=str(e)
                )
        
        # Se tutto fallisce
        return "", "extraction_failed"
    
    def _enhance_image_for_ocr(self, img: Image.Image) -> Image.Image:
        """Migliora l'immagine per migliorare risultati OCR."""
        try:
            import cv2
            import numpy as np
            
            # Converti PIL in OpenCV
            cv_img = np.array(img)
            if len(cv_img.shape) == 3:
                gray = cv2.cvtColor(cv_img, cv2.COLOR_RGB2GRAY)
            else:
                gray = cv_img
                
            # Applica threshold per migliorare contrasto
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Denoise
            denoised = cv2.fastNlMeansDenoising(thresh)
            
            # Converti nuovamente in PIL
            return Image.fromarray(denoised)
            
        except ImportError:
            # Fallback senza OpenCV
            from PIL import ImageEnhance, ImageOps
            img = ImageOps.grayscale(img)
            img = ImageEnhance.Contrast(img).enhance(2.0)
            return img