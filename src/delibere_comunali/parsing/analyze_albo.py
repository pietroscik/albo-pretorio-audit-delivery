# -*- coding: utf-8 -*-
"""
Created on Wed Nov 12 15:29:14 2025

@author: 39329
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import hashlib
import json
import re
import os
import ast
import sys
import shutil
import time
import subprocess
from typing import Optional, List, Dict
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np
import pypdfium2 as pdfium
from dateutil import parser as dateparser
from dotenv import load_dotenv

try:
    import joblib
except ImportError:  # pragma: no cover - optional dependency
    joblib = None

from ..utils.logger import get_logger
from ..utils.metrics import get_metrics_collector
from ..utils.config import get_config
from ..models.parsed_document import ParsedDocument # noqa
from .text_extractor import TextExtractor
from .document_classifier import DocumentClassifier
from .entity_extractor import EntityExtractor, normalizza_rup
from .feature_extractor import TextFeatureExtractor
from .enhanced_extractor import DelibereExtractor
from ..rag.llm_factory import get_llm_client
from ..patterns.albo_patterns import (
    get_extended_personnel_patterns,
    get_extended_accounting_patterns,
    get_category_specific_patterns,
    extract_cig_cup,
    extract_date,
    extract_nomi_propri,
    match_patterns_in_text,
    get_patterns_by_category,
    ACCOUNTING_PATTERNS as EXTENDED_ACCOUNTING_PATTERNS,
    PERSONNEL_PATTERNS as EXTENDED_PERSONNEL_PATTERNS,
)

# --- Nuovi import per il Digital Twin ---
from ..models.procedure import Procedure
from ..utils.text_utils import normalize_text_for_ml
from ..processing.routers.event_router import route_document
from ..models.procedure_builder import ProcedureBuilder
from ..processing.event_factory import DigitalTwinEventFactory  # Added missing import

# Inizializza il builder globale
procedure_builder = ProcedureBuilder()

# --- CONFIGURAZIONE GLOBALE ---
from ..utils.config import get_config
config = get_config()

try:
    import pytesseract
except ImportError:  # pragma: no cover - optional dependency
    pytesseract = None
logger = get_logger("analyze_albo")
text_extractor = TextExtractor(config)
classifier: Optional[DocumentClassifier] = None
entity_extractor: Optional[EntityExtractor] = None
feature_extractor: Optional[TextFeatureExtractor] = None
event_factory: Optional[DigitalTwinEventFactory] = None
metrics = get_metrics_collector()

# Configurazione Tesseract dinamica tramite AppConfig
if pytesseract:
    if config.ocr.tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = config.ocr.tesseract_cmd
        logger.info(f"Tesseract configurato: {config.ocr.tesseract_cmd}")
    else:
        logger.warning("Tesseract non trovato o non configurato. L'OCR potrebbe non funzionare.")

# Imposta automaticamente TESSDATA_PREFIX se necessario
    if config.ocr.tesseract_cmd and os.path.exists(config.ocr.tesseract_cmd):
        tessdata_path = os.path.join(os.path.dirname(config.ocr.tesseract_cmd), "tessdata")
        if "TESSDATA_PREFIX" not in os.environ and os.path.exists(tessdata_path):
            os.environ["TESSDATA_PREFIX"] = tessdata_path

try:
    from delibere_comunali.parsing.enhanced_extractor import DelibereExtractor
except ImportError:
    DelibereExtractor = None

from ..processing.event_factory import DigitalTwinEventFactory # noqa
# Importiamo la funzione infer_doc_type da analyzer
try:
    def infer_doc_type(pdf_path, text_content): # Definizione di fallback
        pdf_name = os.path.basename(pdf_path) if isinstance(pdf_path, (str, os.PathLike)) else str(pdf_path)
        text_lower = text_content.lower() if text_content else ""
        name_lower = pdf_name.lower()
        
        # Controlla prima il nome del file
        if any(keyword in name_lower for keyword in ['determinazione', 'determina', 'determ']):
            return "Determinazione"
        if any(keyword in name_lower for keyword in ['delibera', 'delib']):
            return "Delibera"
        if any(keyword in name_lower for keyword in ['bando']):
            return "Bando"
        if any(keyword in name_lower for keyword in ['ordinanza', 'ord.']):
            return "Ordinanza"
        if any(keyword in name_lower for keyword in ['avviso']):
            return "Avviso"
        if any(keyword in name_lower for keyword in ['atto']):
            return "Atto"
        if any(keyword in name_lower for keyword in ['liquidazione', 'impegno', 'mandato', 'pagamento']):
            return "Numeraria"
        if any(keyword in name_lower for keyword in ['certificato']):
            return "Certificato"
        if any(keyword in name_lower for keyword in ['parere', 'visto']):
            if 'tecnico' in name_lower or 'contabile' in name_lower:
                return "ParereTecnico" if 'tecnico' in name_lower else "VistoContabile"
        
        # Controlla il contenuto del testo
        if any(keyword in text_lower for keyword in ['determina', 'determinazione']):
            return "Determinazione"
        if any(keyword in text_lower for keyword in ['delibera', 'deliberazione']):
            return "Delibera"
        if any(keyword in text_lower for keyword in ['ordina', 'ordinanza']):
            return "Ordinanza"
        if any(keyword in text_lower for keyword in ['esito', 'aggiudicazione', 'verbale']):
            return "Esito"
        if any(keyword in text_lower for keyword in ['contratto', 'convenzione']):
            return "Contratto"
        if any(keyword in text_lower for keyword in ['liquidazione', 'impegno', 'mandato', 'pagamento']):
            return "Numeraria"
        if any(keyword in text_lower for keyword in ['certificato di pubblicazione', 'pubblicazione']):
            return "AttestazionePubblicazione"
        if any(keyword in text_lower for keyword in ['parere di regolarit', 'visto contabile']):
            return "ParereTecnico" if 'regolarit' in text_lower else "VistoContabile"
        
        # Default
        return "unknown"
except ImportError:
    pass # Gestito dal fallback

# Inizializza l'estrattore avanzato globale
advanced_extractor = DelibereExtractor() if DelibereExtractor else None

try:
    import google.generativeai as genai
except ImportError:
    genai = None

try:
    from word2number import w2n
except ImportError:
    w2n = None

try:
    from pyhanko.pdf_utils.reader import PdfFileReader
    import pdfx
except ImportError:
    PdfFileReader = None
    pdfx = None

try:
    from System.Security.Cryptography.Pkcs import SignedCms, ContentInfo
except ImportError:
    SignedCms = None

def generate_legal_urn(doc_type, data_atto, numero_atto, ente_nome: str):
    """Genera un LegalURN secondo lo standard Normeinrete (NIR)."""
    if not all([data_atto, numero_atto, ente_nome]):
        return None
    
    # Pulizia nomi
    ente_slug = ente_nome.lower().replace(" ", ".").replace("comune.di.", "comune.")
    type_slug = str(doc_type).lower()
    
    # Formattazione data
    try:
        dt = dateparser.parse(str(data_atto), dayfirst=True)
        date_str = dt.strftime("%Y-%m-%d")
    except:
        return None
        
    organo = "giunta" if "giunta" in type_slug else "consiglio" if "consiglio" in type_slug else "dirigente"
    tipo = "delibera" if "delibera" in type_slug else "determinazione" if "determina" in type_slug else "ordinanza" if "ordinanza" in type_slug else "atto"
    
    return f"urn:nir:{ente_slug};{organo}:{tipo}:{date_str};{numero_atto}"

def estrai_attori_procedimento(testo_atto: str) -> dict:
    """
    Estrae Ruolo, Area e Nome del Dirigente in modo generalizzato
    basandosi sulla sintassi formale degli atti PA italiana.
    """
    if not isinstance(testo_atto, str) or not testo_atto.strip():
        return {"ruolo": "NON IDENTIFICATO", "area": "NON IDENTIFICATA", "nome": "NON IDENTIFICATO"}
    
    # Pulizia per facilitare la regex su righe multiple
    testo = " ".join(testo_atto.split())
    
    risultato = {
        "ruolo": "NON IDENTIFICATO", 
        "area": "NON IDENTIFICATA", 
        "nome": "NON IDENTIFICATO"
    }

    # LA NORMA: Regex che cattura la triade istituzionale [Ruolo] [Area] [Titolo] [Nome]
    pattern_istituzionale = re.compile(
        r"(?P<ruolo>RESPONSABILE|DIRIGENTE|FUNZIONARIO|IL R\.U\.P\.?|IL SEGRETARIO|IL SINDACO)\s+"
        r"(?:DEL|DELL['’]|DELLO|DELLA|DEGLI|GENERALE)?\s*"
        r"(?P<area>(?:SETTORE|AREA|SERVIZIO|UFFICIO|DIREZIONE|COMUNE)\s+[A-Z\sÀ-ú]+?)\s+"
        r"(?:(?P<titolo>DOTT\.?|DOTT\.SSA|DR\.?|ING\.?|ARCH\.?|GEOM\.?|AVV\.?|RAG\.?|PROF\.?)\s+)?"
        r"(?P<nome>[A-Z][a-zÀ-úA-Z']+(?:\s+[A-Z][a-zÀ-úA-Z']+){1,3})\b",
        re.IGNORECASE
    )

    match = pattern_istituzionale.search(testo)
    
    if match:
        risultato["ruolo"] = match.group("ruolo").upper()
        area_raw = match.group("area").upper()
        # Pulizia area da titoli residui
        area_clean = re.sub(r'\s+(DOTT|ING|ARCH|GEOM|AVV|RAG|PROF).*', '', area_raw).strip()
        risultato["area"] = area_clean
        
        nome_raw = match.group("nome").upper().strip()
        # Rimuoviamo eventuali formule burocratiche successive catturate dalla regex
        for stop_word in [" PREMESSO", " VISTO", " VISTA", " CONSIDERATO", " ACCERTATO", " DATO ATTO", " RITENUTO", " IL QUALE"]:
            if stop_word in nome_raw:
                nome_raw = nome_raw.split(stop_word)[0].strip()
        risultato["nome"] = nome_raw
    
    return risultato

def check_normative_compliance(pdf_path: Path):
    """Verifica la conformità normativa (firme e accessibilità)."""
    results = {
        "is_signed": False,
        "is_accessible": False,
        "pdf_version": None,
        "compliance_score": 0
    }
    
    if not pdf_path.exists(): return results

    # 1. Verifica Firme (Presenza campi firma PAdES)
    if PdfFileReader is not None:
        try:
            with open(pdf_path, 'rb') as f:
                reader = PdfFileReader(f)
                if reader.embedded_signatures:
                    results["is_signed"] = True
                    results["compliance_score"] += 50
        except Exception as e:
            logger.debug(f"Verifica firma fallita per {pdf_path.name}: {e}")

    # 2. Verifica Accessibilità (Testo vs Immagine)
    try:
        pdf = pdfium.PdfDocument(str(pdf_path))
        results["pdf_version"] = pdf.get_version() / 10.0
        
        has_text = False
        # Controlliamo le prime 3 pagine per efficienza
        for i in range(min(3, len(pdf))):
            text = pdf[i].get_textpage().get_text_bounded().strip()
            if len(text) > 100: # Almeno 100 caratteri di testo reale
                has_text = True
                break
        
        results["is_accessible"] = has_text
        if has_text:
            results["compliance_score"] += 50
    except Exception as e:
        logger.debug(f"Verifica accessibilità fallita per {pdf_path.name}: {e}")
        
    return results

def extract_p7m_content(p7m_path: Path) -> Optional[bytes]:
    """Estrae il contenuto da un file .p7m usando librerie .NET (Windows) o OpenSSL (Linux/Fallback)."""
    # 1. Tentativo con librerie .NET (se disponibili su Windows)
    if SignedCms is not None:
        try:
            p7m_bytes = p7m_path.read_bytes()
            signed_cms = SignedCms()
            signed_cms.Decode(p7m_bytes)
            return signed_cms.ContentInfo.Content
        except Exception as e:
            logger.debug(f"Estrazione .NET fallita, provo fallback: {e}")

    # 2. Fallback universale con OpenSSL (Obbligatorio su Linux/WSL)
    openssl_cmd = "openssl"
    if shutil.which(openssl_cmd):
        try:
            return subprocess.check_output(
                [openssl_cmd, "smime", "-decrypt", "-in", str(p7m_path), "-inform", "DER", "-noverify"],
                stderr=subprocess.DEVNULL
            )
        except Exception as e:
            logger.warning(f"Estrazione OpenSSL fallita per {p7m_path.name}: {e}")
    
    return None

# --- Extractor usando pypdfium2 ---
def extract_text_pdf(pdf_input) -> str:
    """Estrae testo da PDF usando pypdfium2"""
    try:
        pdf = pdfium.PdfDocument(pdf_input)
        text_parts = []
        for page in pdf:
            textpage = page.get_textpage()
            text = textpage.get_text_bounded()
            text_parts.append(text)
        return "\n".join(text_parts)
    except Exception as e:
        logger.error(f"Estrazione testo nativo fallita: {e}")
        return ""


def _render_pdfium_images(pdf_input, dpi=300, max_pages=None):
    try:
        pdf = pdfium.PdfDocument(pdf_input)
    except Exception as e:
        logger.error(f"Render PDF fallito: {e}")
        return
    n = len(pdf)
    last = n if max_pages is None else min(n, max_pages)
    scale = dpi / 72.0
    for i in range(last):
        page = pdf[i]
        bitmap = page.render(scale=scale, rotation=0)
        yield bitmap.to_pil()  # PIL Image

def _enhance_image_for_ocr(img):
    """Migliora il contrasto e converte in scala di grigi per aiutare Tesseract sui file sgranati."""
    try:
        import cv2
        import numpy as np
        from PIL import Image
        
        cv_img = np.array(img)
        if len(cv_img.shape) == 3:
            gray = cv2.cvtColor(cv_img, cv2.COLOR_RGB2GRAY)
        else:
            gray = cv_img
            
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        denoised = cv2.fastNlMeansDenoising(thresh, h=10)
        
        return Image.fromarray(denoised)
        
    except ImportError:
        # Fallback a PIL se OpenCV non è installato
        from PIL import ImageEnhance, ImageOps
        img = ImageOps.grayscale(img)
        img = ImageEnhance.Contrast(img).enhance(2.0)
        return img

def ocr_pdf_probe(pdf_input, dpi=300, pages=(1,2)):
    if pytesseract is None:
        return "", False
    txt = []
    try:
        pdf = pdfium.PdfDocument(pdf_input)
        scale = dpi / 72.0
        for i in range(min(len(pdf), pages[-1])):
            page = pdf[i]
            bitmap = page.render(scale=scale, rotation=0)
            img = _enhance_image_for_ocr(bitmap.to_pil())
            try:
                txt.append(pytesseract.image_to_string(img, lang="ita", config="--psm 4"))
            except pytesseract.TesseractError:
                # Fallback alla lingua inglese (di default sempre presente) se manca l'italiano
                txt.append(pytesseract.image_to_string(img, lang="eng", config="--psm 4"))
    except Exception as e:
        logger.error(f"Prova OCR fallita: {e}")
        return "", False
    text = " ".join(" ".join(txt).split())
    good = any(k in text.lower() for k in ["€","euro","cig","cup","impegno","liquidazione","corrispettivo","spesa"])
    return text, good

def ocr_pdf_full(pdf_input, dpi=300, max_pages=None):
    if pytesseract is None:
        return ""
    parts = []
    try:
        for img in _render_pdfium_images(pdf_input, dpi=dpi, max_pages=max_pages):
            img = _enhance_image_for_ocr(img)
            try:
                parts.append(pytesseract.image_to_string(img, lang="ita", config="--psm 4"))
            except pytesseract.TesseractError:
                parts.append(pytesseract.image_to_string(img, lang="eng", config="--psm 4"))
    except Exception as e:
        logger.error(f"OCR completo fallito: {e}")
        return ""
    return " ".join(" ".join(parts).split())

SCRIPT_DIR = Path(__file__).resolve().parent

# -------- Boilerplate --------
ente_nome_env = os.environ.get("ENTE_NOME", "Comune")
BOILERPLATE_PATTERNS = [
    re.compile(r"COPIA\s+Piazza Municipio.*?\n", re.IGNORECASE),
    re.compile(rf"{ente_nome_env}.*?\n", re.IGNORECASE),
    re.compile(r"Albo Pretorio Online.*?\n", re.IGNORECASE),
    re.compile(r"Pubblicato il \d{2}/\d{2}/\d{4}.*?\n", re.IGNORECASE),
    re.compile(r"IL RESPONSABILE DEL SERVIZIO.*?\n", re.IGNORECASE),
    re.compile(r"IL SINDACO.*?\n", re.IGNORECASE),
    re.compile(r"Firmato digitalmente.*?\n", re.IGNORECASE),
    re.compile(r"PARERE DI REGOLARITÀ TECNICA.*?\n", re.IGNORECASE),
    re.compile(r"ATTESTAZIONE DI PUBBLICAZIONE.*?\n", re.IGNORECASE),
    re.compile(r"---+\s*$", re.MULTILINE),
    re.compile(r"===\s*$", re.MULTILINE),
    re.compile(r"\*+\s*$", re.MULTILINE),
    re.compile(r"Pag\. \d+ di \d+", re.IGNORECASE),
]

def remove_boilerplate(text):
    """Rimuove il boilerplate dal testo."""
    if not text:
        return text
    for pattern in BOILERPLATE_PATTERNS:
        text = pattern.sub("", text)
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()

# -------- Regex utili --------
# Regex per documenti da saltare
RX_SKIP_PATTERNS = {
    'personnel': re.compile(r'\b(trattenimento in servizio|fabbisogno di personale|dotazione organica|assunzioni|concorso pubblico)\b', re.I),
    'regulation': re.compile(r'\b(approvazione.*regolamento|modifica.*regolamento)\b', re.I),
    'accounting_summary': re.compile(r'\b(riaccertamento.*residui|salvaguardia.*equilibri.*bilancio)\b', re.I),
    'commission': re.compile(r'\b(nomina.*commissione|costituzione.*commissione)\b', re.I),
}

def lettere_to_numero(testo: str) -> Optional[float]:
    """Converte testo in lettere in numero usando word2number."""
    if w2n is None or not testo:
        return None

    testo = testo.strip().lower()
    testo = re.sub(r"[^\w\s/]", "", testo)

    if "/" in testo:
        parti = testo.split("/")
        if len(parti) == 2:
            parte_lettere = parti[0].strip()
            parte_decimali = parti[1].strip()
            try:
                numero = w2n.word_to_num(parte_lettere)
                decimali = float(parte_decimali) / 100
                return float(numero + decimali)
            except:
                pass
    try:
        return float(w2n.word_to_num(testo))
    except:
        pass
    return None

# Pattern aggiornati per importi
IMPORTI_REGEX = [
    r"€\s*[\d.,]+",
    r"[\d.,]+\s*(euro|€|EUR)",
    r"importo\s*(totale|complessivo|di\s+spesa|a\s+base\s+d[’']asta)\s*[:=]?\s*[\d.,]+",
    r"(impegno|liquidazione|accredito|pagamento)\s+(n\.?\s*\d+\s*)?[\d.,]+",
    r"CIG\s+[A-Z0-9]+\s*[:\-]?\s*[\d.,]+",
    r"CUP\s+[A-Z0-9]+\s*[:\-]?\s*[\d.,]+",
    r"IVA\s+(inclusa|esclusa)\s*[\d.,]+",
    r"\b\d{1,3}/\d{2}\b",
    r"\b(uno|due|tre|quattro|cinque|sei|sette|otto|nove|dieci|undici|dodici|tredici|quattordici|quindici|sedici|diciassette|diciotto|diciannove|venti|trenta|quaranta|cinquanta|sessanta|settanta|ottanta|novanta|cento|mille|milione|miliardo)\s+(euro|€|EUR)\b",
    r"\b(uno|due|tre|quattro|cinque|sei|sette|otto|nove|dieci|undici|dodici|tredici|quattordici|quindici|sedici|diciassette|diciotto|diciannove|venti|trenta|quaranta|cinquanta|sessanta|settanta|ottanta|novanta|cento|mille|milione|miliardo)\s*/\d{2}\b",
]

# Regex per CIG e CUP (Migliorate per intercettare C.I.G., spaziature, ecc.)
RX_CIG = re.compile(r'\bC\.?I\.?G\.?(?:\s*(?:n\.|numero|codice)?\s*[:\-]?\s*)([A-Z0-9]{10})\b', re.IGNORECASE)
RX_CUP = re.compile(r'\bC\.?U\.?P\.?(?:\s*(?:n\.|numero|codice)?\s*[:\-]?\s*)([A-Z0-9]{15})\b', re.IGNORECASE)

# Regex per dati specifici dell'atto
RX_OGGETTO = re.compile(r'OGGETTO:\s*(.+?)(?=\s+(?:Registro\s+Generale\b|L[\'’\s]anno\b|CIG\s*[:\-]|CUP\s*[:\-]|Premess[oa]\b|Vist[oi]\s*(?::|il\b|la\b|i\b|le\b|che\b|l[\'’])|Considerat[oa]\b|Richiamat[oi]\b|Rilevat[oa]\b|Attes[oa]\b|Acquisit[oa]\b|Dato\s+atto\b|Preso\s+atto\b|DELIBERA\b|DETERMINA\b|ORDINA\b|IL\s+RESPONSABILE\b|IL\s+SINDACO\b|LA\s+GIUNTA\b|IL\s+CONSIGLIO\b|PARERE\b)|$)', re.IGNORECASE)
RX_NUM_ATTO = re.compile(r'N\.\s*(\d+)\s*DEL\s*(\d{2}/\d{2}/\d{4})', re.IGNORECASE)
RX_REG_GEN = re.compile(r'Registro Generale\s*N\.\s*(\d+)\s*DEL\s*(\d{2}/\d{2}/\d{4})', re.IGNORECASE)

RX_RESPONSABILE = re.compile(r'IL\s+RESPONSABILE\s+DEL\s+SERVIZIO\s*(?:\n)?\s*(?:Finanziario)?\s*(?:dott\.|dott\.ssa|Avv\.|Ing\.|Arch\.)?\s*([A-Z][a-zà-úA-Z\s\.\'’]+(?:\s[A-Z][a-zà-úA-Z\s\.\'’]+)*)', re.IGNORECASE)
RX_UFFICIO = re.compile(r'(?:Area|Settore|Servizio)\s+([A-Z][a-zà-úA-Z\s]+)', re.IGNORECASE)

# Regex per il beneficiario (più robusta)
RX_BENEF = [
    # Pattern più specifici e affidabili vengono provati prima
    re.compile(r'Denominazione:\s+([A-Z\s\.\'’\-]+)', re.IGNORECASE),
    re.compile(r'(?:aggiudicatari[oa]|affidatari[oa]|ditta|societ[aà]|impresa)\s+(?:all[a\'’]\s+|è\s+)?([A-Z0-9\s\.\&\-\'\"]+?)(?:\s+con\s+sede|\s+p\.iva|\s+c\.f\.|\s+per\s+l\'importo|,|\n)', re.IGNORECASE),
]


# Regex per dati contabili
RX_IMPEGNO = re.compile(r'(?:impegno|impegno\s+n\.|N\.\s+Impegno\s+Definitivo)\s*[:\s]*(\d+)', re.IGNORECASE)
RX_ACCERT = re.compile(r'(?:accertamento|accertamento\s+n\.|N\.\s+Accertamento)\s*[:\s]*(\d+)', re.IGNORECASE)
RX_CAPITOLO = re.compile(r'(?:capitolo|Capitolo\s+Quinti\s+Livello)\s*[:\s]*([\d\.]+)', re.IGNORECASE)
RX_PEG     = re.compile(r"\b(PEG|missione|programma)\b[^\n\r]*", re.I)
RX_IBAN    = re.compile(r'\bIT\s*\d{2}\s*[A-Z]\s*\d{5}\s*\d{5}\s*[0-9A-Z]{12}\b', re.IGNORECASE)

# Regex per catturare l'importo specifico di liquidazione/SAL evitando il totale dell'appalto
RX_IMPORTO_LIQUIDATO = re.compile(r'(?:liquidare|pagare|erogare|saldo del SAL|certificato di pagamento)[\s\w\n]{1,80}?(?:€|euro)\s*([\d.,]+)', re.IGNORECASE)


# -------- Competenze Personale (Pattern basati su documenti reali) --------

# Pattern per contabilita - AGGIORNATO
ACCOUNTING_PATTERNS = EXTENDED_ACCOUNTING_PATTERNS

# Pattern per competenze del personale - AGGIORNATO (50+)
PERSONNEL_PATTERNS = get_extended_personnel_patterns()

# Compila tutti i pattern
COMPILED_PATTERNS = {k: re.compile(v.pattern if hasattr(v, 'pattern') else v, re.IGNORECASE)
                     for k, v in PERSONNEL_PATTERNS.items()}

@dataclass
class PersonnelCompetence:
    competence_type: str
    description: str
    assigned_to: str
    source_decree: Optional[str] = None

def is_personnel_competence_relevant(text: str) -> bool:
    for pattern in COMPILED_PATTERNS.values():
        if pattern.search(text):
            return True
    return False

def extract_decree_references(text: str) -> List[Dict]:
    references = []
    for match in COMPILED_PATTERNS['decreto_sindacale'].finditer(text):
        references.append({'number': match.group(1), 'text': match.group(0)})
    return references

def extract_personnel_competences(text: str) -> List[PersonnelCompetence]:
    competences = []
    for ref in extract_decree_references(text):
        competences.append(PersonnelCompetence(
            competence_type="decreto_sindacale",
            description=f"Decreto Sindacale {ref['number']}",
            assigned_to="Sindaco",
            source_decree=ref['number']
        ))
    if COMPILED_PATTERNS.get('funzioni_dirigenziali') and COMPILED_PATTERNS['funzioni_dirigenziali'].search(text):
        competences.append(PersonnelCompetence(
            competence_type="funzioni_dirigenziali",
            description="Funzioni dirigenziali attribuite",
            assigned_to="Dirigente"
        ))
    for match in COMPILED_PATTERNS.get('ufficio', re.compile('')).finditer(text):
        office = match.group(0).strip()
        competences.append(PersonnelCompetence(
            competence_type="ufficio",
            description=f"Gestione {office}",
            assigned_to=office
        ))
    return competences

def is_accounting_relevant(text, doc_type, category):
    haystack = (text or "").lower()
    if doc_type in {"Ordinanza", "Decreto", "Elenco", "AttestazionePubblicazione", "Avviso"}:
        return False
    
    # Esclusioni esplicite per tipologie non contabili che possono contenere numeri
    if category in {"Servizi Demografici", "Pareri e Allegati"}:
        return False
    if "pubblicazione di matrimonio" in haystack or "concessione del patrocinio" in haystack:
        return False

    # Le delibere sono atti di indirizzo, non contabili di default, a meno di keyword specifiche
    if category in {"Delibera di Giunta", "Delibera di Consiglio", "Regolamenti", "Affari Generali", "Personale"}:
        strong_markers = ["impegno di spesa", "liquidazione", "variazione di bilancio", "riconoscimento debito", "debito fuori bilancio"]
        if not any(m in haystack for m in strong_markers):
            return False
            
    if doc_type == "VistoContabile":
        return True
        
    if any(p.search(haystack) for p in ACCOUNTING_PATTERNS):
        return True
    if category == "Contabilità" and doc_type == "Determinazione":
        return True
    if doc_type == "Determinazione" and any(m in haystack for m in ("servizio", "lavori", "fornitura")):
        return True
    return False

def extract_from_pdf(pdf_file: Path, use_llm=False, classifier: Optional[DocumentClassifier] = None, entity_extractor: Optional[EntityExtractor] = None, feature_extractor: Optional[TextFeatureExtractor] = None, ente_nome=None, text_dir=None) -> ParsedDocument:
    """Estrae testo e cattura campi principali da un PDF (testuale -> OCR fallback)."""
    
    # Gestione preliminare dei file .p7m
    is_p7m = pdf_file.name.lower().endswith(".p7m")
    pdf_content_bytes = None
    if is_p7m:
        pdf_content_bytes = extract_p7m_content(pdf_file)
        if not pdf_content_bytes:
            return ParsedDocument(pdf_name=pdf_file.name, pdf_path=str(pdf_file), source="p7m_extraction_failed")
        # Usiamo i byte estratti come se fossero il file originale
        path_for_parsing = pdf_content_bytes # Questo non è più usato direttamente qui
    else:
        path_for_parsing = str(pdf_file)


    out = {
        "pdf_name": pdf_file.name,
        "pdf_path": str(pdf_file),
        "doc_type": "unknown",
        "category": None,
        "subcategory": None,
        "classification_confidence": None,
        "classification_terms": None,
        "oggetto": None,
        "numero_atto": None,
        "data_atto": None,
        "numero_registro": None,
        "data_registro": None,
        "importi_raw": [],
        "importo_max": None,
        "importo_sum": None,
        "importi_count": 0,
        "cig": None,
        "cup": None,
        "beneficiario": None,
        "piva_beneficiario": None,
        "iban": None,
        "codice_appalti": None,
        "tipo_procedura": None,
        "importo_lettere": None,
        "anomalie": None,
        "responsabile": None,
        "ufficio": None,
        "impegno_num": None,
        "impegno_anno": None,
        "accert_num": None,
        "accert_anno": None,
        "quadro_economico": None,
        "capitolo": None,
        "peg_riga": None,
        "is_visto_contabile": ("VistoContabile" in pdf_file.name),
        "source": "text",   # 'text' o 'ocr'
        "accounting_relevant": False,
        "missing_amount_expected": False,
        "veridicità_score": 0,
        "solidità_globale": 0,
        "is_personnel_competence_relevant": False,
        "personnel_competences": "[]",
        "decree_references": "[]"
    }

    # 1. Estrazione unificata del testo (gestisce PDF, HTML, OCR)
    text_file_path = text_dir / f"{pdf_file.stem}.txt" if text_dir else None
    if text_file_path and text_file_path.exists():
        text_one = text_file_path.read_text(encoding="utf-8", errors="ignore")
        source = "pre_extracted_text"
    else:
        text_one, source = text_extractor.extract(pdf_file, content_bytes=pdf_content_bytes)
    
    out["source"] = source

    # 2. Normalizzazione e arricchimento del testo
    text_one = remove_boilerplate(text_one)
    text_one = normalize_text_for_ml(text_one)
    out["text_sha256"] = hashlib.sha256(text_one.encode("utf-8", errors="ignore")).hexdigest()

    if feature_extractor:
        out.update(feature_extractor.extract(text_one))

    # Popola i campi di testo nel dizionario di output
    text_name = pdf_file.stem + ".txt"
    if text_dir:
        out["text_path"] = str(text_dir / text_name)
    out["text_preview"] = text_one[:1200]

    # --- Competenze Personale ---
    out["is_personnel_competence_relevant"] = is_personnel_competence_relevant(text_one)
    out["personnel_competences"] = json.dumps([c.__dict__ for c in extract_personnel_competences(text_one)], ensure_ascii=False)
    out["decree_references"] = json.dumps(extract_decree_references(text_one), ensure_ascii=False)

    # Determiniamo in anticipo la natura giuridica del documento
    out["doc_type"] = infer_doc_type(pdf_file, text_one)

    # --- Classificazione ---
    if classifier:
        category, subcategory, confidence, terms = classifier.classify(out["oggetto"], text_one)
        out["category"] = category
        out["subcategory"] = subcategory
        out["classification_confidence"] = confidence
        out["classification_terms"] = terms

        # --- Estrazione Entità (Regex, LLM, Advanced) ---
        if entity_extractor:
            entities = entity_extractor.extract_all(text_one, out["doc_type"], subcategory, use_llm)
            out.update(entities)
    else:
        out["classification_confidence"] = "no_classifier"

    out["accounting_relevant"] = is_accounting_relevant(text_one, out["doc_type"], out["category"])
    out["missing_amount_expected"] = bool(out["accounting_relevant"] and out["doc_type"] != "VistoContabile" and not out.get("importi_raw"))

    # --- LegalURN (NIR Standard) ---
    out["legal_urn"] = generate_legal_urn(out.get("doc_type"), out.get("data_atto"), out.get("numero_atto"), ente_nome=ente_nome)

    # --- Compliance (Firme e Accessibilità) ---
    compliance = check_normative_compliance(pdf_file)
    out.update(compliance)

    # --- Responsabile, Area e Ruolo (Rule-Based NER) ---
    attori = estrai_attori_procedimento(text_one)
    out["rup_nome"] = attori["nome"]
    out["rup_area"] = attori["area"]
    out["rup_ruolo"] = attori["ruolo"]

    # Mantieni retrocompatibilità per 'responsabile'
    out["responsabile"] = normalizza_rup(out.get("rup_nome") or out.get("responsabile"))

    known_fields = set(ParsedDocument.__annotations__.keys())
    filtered_out = {k: v for k, v in out.items() if k in known_fields}
    return ParsedDocument(**filtered_out, _text=text_one)

def safe_literal_list(s):
    """Converte la stringa della colonna allegati (lista) in lista Python."""
    if pd.isna(s) or not str(s).strip():
        return []
    txt = str(s).strip()
    # tentativo con ast.literal_eval (se è una lista python)
    try:
        val = ast.literal_eval(txt)
        if isinstance(val, list):
            return [str(x) for x in val]
    except Exception as e:
        # Log the exception for debugging
        import logging
        logging.warning(f"Failed to evaluate literal from text '{txt}': {e}")
        pass
    # fallback: separatore ; o |
    if ";" in txt:
        return [t.strip() for t in txt.split(";") if t.strip()]
    if "|" in txt:
        return [t.strip() for t in txt.split("|") if t.strip()]
    # ultimo tentativo: singolo URL
    return [txt]

def build_parser():
    ap = argparse.ArgumentParser(description="Analizza gli allegati PDF scaricati dall'albo.")
    ap.add_argument("--ente", default="avella", help="Nome dell'ente per tracciamento dati (es. avella, tufino).")
    ap.add_argument("--base", default=None, help="Cartella output dello scraper (default: data/{ente}/albo_download).")
    ap.add_argument("--csv", default=None, help="CSV metadati. Default: <base>/albo_metadati.csv")
    ap.add_argument("--pdf-dir", default=None, help="Cartella PDF. Default: <base>/pdf")
    ap.add_argument("--no-corpus", action="store_true", help="Non esportare corpus JSONL e testi per ML/RAG.")
    ap.add_argument("--use-llm", action="store_true", help="Usa Gemini API per estrarre metadati complessi (richiede variabile d'ambiente GOOGLE_API_KEY).")
    ap.add_argument("--force", action="store_true", help="Ignora la cache e rianalizza tutti i PDF.")
    return ap

def main(args=None):
    if args is None:
        args = build_parser().parse_args()
    else:
        # If args is passed as an object, make sure it has the required attributes with defaults
        if not hasattr(args, 'ente'):
            args.ente = 'avella'  # default value
        if not hasattr(args, 'base'):
            from ..utils.config import get_tenant_dir
            args.base = str(get_tenant_dir(args.ente))
        if not hasattr(args, 'csv'):
            args.csv = None
        if not hasattr(args, 'pdf_dir'):
            args.pdf_dir = None
        if not hasattr(args, 'force'):
            args.force = False
        if not hasattr(args, 'use_llm'):
            args.use_llm = False
        if not hasattr(args, 'no_corpus'):
            args.no_corpus = False

    from ..utils.config import get_tenant_dir
    base = get_tenant_dir(args.ente)

    csv_path = Path(args.csv) if args.csv else base / "albo_metadati.csv"
    pdf_dir = Path(args.pdf_dir) if args.pdf_dir else base / "pdf"
    out_xlsx = base / "albo_analisi.xlsx"
    out_csv_allegati = base / "allegati_parsed.csv"
    out_csv_atti = base / "atti_parsed.csv"
    out_csv_features = base / "documenti_features.csv"
    text_dir = base / "texts"
    out_corpus_jsonl = base / "documenti_corpus.jsonl"

    # Caricamento del modello ML (Random Forest) se esiste
    model_path = base / "random_forest_model.joblib"
    rf_model = None
    if joblib is None:
        logger.warning("joblib non installato: salto il caricamento del modello ML.")
    elif model_path.exists():
        try:
            rf_model = joblib.load(model_path)
            logger.info(f"Modello Machine Learning caricato da {model_path}")
        except Exception as e:
            logger.warning(f"Impossibile caricare il modello ML: {e}")

    # Inizializzazione dei componenti
    global classifier, entity_extractor, feature_extractor, event_factory
    classifier = DocumentClassifier(rf_model=rf_model)
    entity_extractor = EntityExtractor(advanced_extractor=advanced_extractor)
    feature_extractor = TextFeatureExtractor()
    event_factory = DigitalTwinEventFactory()

    text_dir.mkdir(parents=True, exist_ok=True)

    if not csv_path.exists():
        logger.error(f"Nessun dato trovato in {csv_path}. Devi prima eseguire lo scraper.")
        sys.exit(1)

    df = pd.read_csv(csv_path, encoding="utf-8", sep=",")

    files = (list(pdf_dir.glob("*.pdf")) +
             list(pdf_dir.glob("*.PDF")) +
             list(pdf_dir.glob("*.php")) +
             list(pdf_dir.glob("*.PHP")) +
             list(pdf_dir.glob("*.p7m")) +
             list(pdf_dir.glob("*.P7M")) +
             list(pdf_dir.glob("*.html")) +
             list(pdf_dir.glob("*.HTML")))
    logger.info(f"Trovati {len(files)} file (PDF/PHP/P7M/HTML)")

    processed_cache = {}
    if out_csv_allegati.exists() and not args.force:
        try:
            df_cache = pd.read_csv(out_csv_allegati, encoding="utf-8")
            processed_cache = df_cache.set_index('pdf_name').to_dict('index')
            logger.info(f"Trovati {len(processed_cache)} PDF già elaborati nel CSV. Verranno saltati.")
        except Exception as e:
            logger.warning(f"Impossibile caricare la cache dei PDF esistenti: {e}")

    parsed_docs = []
    corpus_rows = []

    with metrics.start_operation("analisi_pdf") as op:
        seen_hashes = set()

        for idx, pdf_file in enumerate(files):
            logger.info(f"Processando {idx + 1}/{len(files)}: {pdf_file.name}")

            if pdf_file.name in processed_cache:
                info = processed_cache[pdf_file.name]
                parsed_docs.append(ParsedDocument.from_dict(info))
                continue

            doc = extract_from_pdf(
                pdf_file,
                use_llm=args.use_llm,
                classifier=classifier,
                entity_extractor=entity_extractor,
                feature_extractor=feature_extractor,
                ente_nome=args.ente,
                text_dir=text_dir
            )

            text_hash = doc.text_sha256
            if text_hash and text_hash in seen_hashes:
                continue
            seen_hashes.add(text_hash)

            parsed_docs.append(doc)

            if event_factory and doc._text:
                event = event_factory.create_event(doc)
                procedure_builder.add_event(event)

            if not args.no_corpus:
                corpus_row = doc.model_dump()
                corpus_row["text"] = doc._text
                corpus_rows.append(corpus_row)

        op.set_items_processed(len(files))

    dfp = pd.DataFrame([p.model_dump() for p in parsed_docs])

    # --- Digital Twin Procedure Analysis ---
    logger.info("Costruzione e analisi dei procedimenti (Digital Twin)...")
    all_procedures = procedure_builder.get_all_procedures()

    procedures_path = base / "procedures.json"
    anomalies_path = base / "anomalies.json"

    with open(procedures_path, 'w', encoding='utf-8') as f:
        json.dump([p.to_dict() for p in all_procedures], f, indent=2, ensure_ascii=False)
    logger.info(f"Salvati {len(all_procedures)} procedimenti in {procedures_path}")

    anomalies = procedure_builder.detect_anomalies()
    with open(anomalies_path, 'w', encoding='utf-8') as f:
        json.dump(anomalies, f, indent=2, ensure_ascii=False)
    logger.info(f"Rilevate e salvate {len(anomalies)} anomalie in {anomalies_path}")

    # --- Costruzione tabella per atto (collapse allegati) ---
    def get_atto_group(filename):
        stem = Path(filename).stem
        return re.sub(r'_\d+$', '', stem)

    if 'pdf_name' in dfp.columns:
        dfp["atto_group"] = dfp["pdf_name"].apply(get_atto_group)

        def priority_doc_type(x):
            vals = x.dropna().tolist()
            if "Determinazione" in vals: return "Determinazione"
            if "Delibera" in vals: return "Delibera"
            return next(iter([i for i in vals if i != "unknown"]), "unknown")

        atti_records = []
        for nome_gruppo, group_df in dfp.groupby("atto_group", dropna=False):
            record = {
                "atto_group": nome_gruppo,
                "doc_type": priority_doc_type(group_df["doc_type"]),
                "category": next(iter(group_df["category"].dropna()), None),
                "oggetto": next(iter(group_df["oggetto"].dropna()), None),
                "numero_atto": next(iter(group_df["numero_atto"].dropna()), None),
                "data_atto": next(iter(group_df["data_atto"].dropna()), None),
                "importo_max": group_df["importo_max"].max(),
                "cig": ",".join(group_df["cig"].dropna().unique()),
                "cup": ",".join(group_df["cup"].dropna().unique()),
                "beneficiario": " | ".join(group_df["beneficiario"].dropna().unique()),
                "responsabile": next(iter(group_df["responsabile"].dropna()), None),
                "anomalie": " | ".join(group_df["anomalie"].dropna().unique())
            }
            atti_records.append(record)

        df_atti = pd.DataFrame(atti_records)
        df_atti.to_csv(out_csv_atti, index=False, encoding="utf-8")

    # --- Salvataggio output ---
    logger.info("Salvataggio CSV...")
    dfp.to_csv(out_csv_allegati, index=False, encoding="utf-8")

    feature_cols = [c for c in ParsedDocument.model_fields.keys() if c != "_text"]
    dff = dfp[[c for c in feature_cols if c in dfp.columns]].copy()
    dff.to_csv(out_csv_features, index=False, encoding="utf-8")

    if not args.no_corpus:
        with open(out_corpus_jsonl, "w", encoding="utf-8") as f:
            for row in corpus_rows:
                text_path = Path(row["text_path"])
                text_path.write_text(row["text"], encoding="utf-8", errors="ignore")
                del row["text"]
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    logger.info("Salvataggio Excel...")
    try:
        with pd.ExcelWriter(out_xlsx, engine="xlsxwriter") as xl:
            dfp.to_excel(xl, index=False, sheet_name="pdf_analisi")
            if 'df_atti' in locals():
                df_atti.to_excel(xl, index=False, sheet_name="atti_estratti")
            dff.to_excel(xl, index=False, sheet_name="features_ml")
        logger.info("Excel salvato con successo!")
    except Exception as e:
        logger.warning(f"Errore salvataggio Excel con xlsxwriter: {e}")

    logger.info(f"Salvati:\n- {out_csv_allegati}\n- {out_csv_atti}\n- {out_csv_features}\n- {out_corpus_jsonl if not args.no_corpus else '(corpus disattivato)'}\n- {out_xlsx} (se riuscito)")

    metrics.export_to_file(str((base / "metrics_analyze_albo.json").resolve()))

if __name__ == "__main__":
    main()
