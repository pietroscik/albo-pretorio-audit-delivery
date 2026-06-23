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
from .enhanced_extractor import DelibereExtractor
from ..rag.llm_factory import get_llm_client
from ..patterns.albo_patterns import (
    get_extended_personnel_patterns,
    get_extended_accounting_patterns,
    get_category_specific_patterns,
    extract_cig_cup,
    extract_importi as extract_importi_extended,
    extract_date,
    extract_nomi_propri,
    match_patterns_in_text,
    get_patterns_by_category,
    ACCOUNTING_PATTERNS as EXTENDED_ACCOUNTING_PATTERNS,
    PERSONNEL_PATTERNS as EXTENDED_PERSONNEL_PATTERNS,
)

# --- Nuovi import per il Digital Twin ---
from ..models.administrative_event import AdministrativeEvent, EventType, DocumentType, Actor, ActorType
from ..models.procedure import Procedure
from ..processing.routers.event_router import route_document
from ..builders.procedure_builder import ProcedureBuilder

# Inizializza il builder globale
procedure_builder = ProcedureBuilder()

from ..utils.config import get_config
config = get_config()

try:
    import pytesseract
except ImportError:  # pragma: no cover - optional dependency
    pytesseract = None
logger = get_logger("analyze_albo")
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

def generate_legal_urn(doc_type, data_atto, numero_atto, ente_nome=None):
    """Genera un LegalURN secondo lo standard Normeinrete (NIR)."""
    if not data_atto or not numero_atto:
        return None
    
    if ente_nome is None:
        ente_nome = os.environ.get("ENTE_NOME", "comune.generic")

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

def normalizza_beneficiario(nome: str) -> str:
    if not isinstance(nome, str) or not nome.strip():
        return "NON IDENTIFICATO"
        
    nome = nome.upper().strip()
    
    # 1. Filtro falsi positivi burocratici aggiornato
    falsi_positivi = [
        "MAGGIORMENTE QUALIFICAT", "CHE HA PRESENTATO", "IN REGOLA", 
        "DIVERSI BENEFICIARI", "DIVERSE DITTE", "OPERATORE ECONOMICO",
        "APPALTATRICE", "AGGIUDICATARI", "DIVERSI"
    ]
    for fp in falsi_positivi:
        if fp in nome:
            return "DIVERSI/NON APPLICABILE"

    # 2. Rimozione di titoli e forme giuridiche per accorpare i nomi
    stopwords = [
        r'\bPROFESSIONISTA\b', r'\bDITTA\b', r'\bIMPRESA\b', r'\bSOCIET[AÀ]\b', 
        r'\bS\.?R\.?L\.?S?\b', r'\bS\.?P\.?A\.?\b', r'\bS\.?N\.?C\.?\b', r'\bS\.?A\.?S\.?\b',
        r'\bAVV\.?\b', r'\bING\.?\b', r'\bARCH\.?\b', r'\bDOTT\.?(SSA)?\b', r'\bGEOM\.?\b'
    ]
    for sw in stopwords:
        nome = re.sub(sw, '', nome, flags=re.IGNORECASE)
    
    # 3. Pulizia finale da spazi multipli e punteggiatura
    nome = re.sub(r'[^\w\s]', ' ', nome) # Rimuove punteggiatura
    nome = re.sub(r'\s+', ' ', nome).strip()
    
    # Correzione specifica per refusi OCR ricorrenti nei tuoi dati
    if "IORO EMANUELA" in nome or "IORIO EMANUELA" in nome:
        return "IORIO EMANUELA"
        
    return nome if nome else "NON IDENTIFICATO"

def normalizza_rup(testo_rup: str) -> str:
    """Normalizza il nome del Responsabile del Procedimento (RUP)."""
    if not isinstance(testo_rup, str) or not testo_rup.strip():
        return "NON IDENTIFICATO"
    
    testo_rup = testo_rup.upper().strip()

    # Filtro barriera per escludere frasi burocratiche comuni
    esclusioni = [
        "VISTO", "VISTA", "VISTI", "PREMESSO", "ACCERTATA", "SULLA BASE",
        "DECRETO", "FUNZIONI", "AI SENSI", "LA GIUNTA", "DI ADOTTARE", "IL CONSIGLIO",
        "HA ADOTTATO", "DELIBERAZIONE", "DETERMINAZIONE", "COMPETENZA", "MUNICIPIO",
        "URBANISTICO", "REGOLAMENTO", "PROMOZIONE", "FINANZIARIA", "NAZIONALE",
        "RIPRESA", "CENSIMENTO", "DIPENDENTE", "CONCESSO", "CHE CON", "PRO TEMPORE"
    ]
    if any(escl in testo_rup for escl in esclusioni):
        return "NON IDENTIFICATO"

    # Pulizia generica per nomi non mappati
    stopwords = [
        r'\bDOTT\.SSA\b', r'\bDOTT\.?\b', r'\bDR\.?\b', r'\bSSA\b', 
        r'\bIL RESPONSABILE\b', r'\bDEL SERVIZIO\b', r'\bF\.TO\b', 
        r'\bIL SEGRETARIO\b', r'\bIL SINDACO\b', r'\bGEOM\.?\b', 
        r'\bARCH\.?\b', r'\bING\.?\b', r'\bAVV\.?\b'
    ]
    for sw in stopwords:
        testo_rup = re.sub(sw, '', testo_rup, flags=re.IGNORECASE)
        
    testo_pulito = re.sub(r'[^\w\s]', ' ', testo_rup) # Rimuove punteggiatura
    testo_pulito = re.sub(r'\s+', ' ', testo_pulito).strip()

    return testo_pulito if testo_pulito else "NON IDENTIFICATO"

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

# --- Classification Rules ---
CATEGORY_RULES = {
    "Delibera di Giunta": ["deliberazione di giunta", "delibera di giunta", "verbale di deliberazione della giunta"],
    "Delibera di Consiglio": ["deliberazione del consiglio", "delibera di consiglio", "convocazione consiglio"],
    "Pubblicazione e Trasparenza": ["certificato di pubblicazione", "attestazione pubblicazione", "responsabile delle pubblicazioni", "albo pretorio"],
    "Lavori Pubblici": ["lavori pubblici", "progetto esecutivo", "completamento", "manutenzione straordinaria", "opera pubblica", "cantiere"],
    "Personale": ["personale", "assunzioni", "concorso", "selezione", "progressione verticale", "interpello", "trattenimento in servizio", "fabbisogno di personale", "dotazione organica"],
    "Contabilità": ["regolarità contabile", "visto contabile", "impegno di spesa", "liquidazione", "pagamento", "fattura", "capitolo", "accertamento", "residui", "salvaguardia equilibri", "fondo garanzia debiti commerciali", "pagoPA", "pos"],
    "Contenzioso": ["contenzioso", "incarico legale", "patrocinio", "corte di giustizia", "tribunale", "ricorso"],
    "Urbanistica": ["urbanistica", "piano di sviluppo", "recupero urbano", "permesso di costruire", "edilizia"],
    "Servizi Sociali": ["servizi sociali", "assistenza", "contributo economico", "indennità"],
    "Cultura, Turismo e Patrocini": ["cultura", "turismo", "manifestazione", "evento", "spettacolo", "patrocinio comunale", "concessione patrocinio"],
    "Ambiente": ["ambiente", "ecologia", "rifiuti", "inquinamento"],
    "Commercio": ["commercio", "suap", "attività produttive"],
    "Regolamenti": ["regolamento", "approvazione", "modifica"],
    "Affari Generali": ["affari generali", "protocollo", "archivio", "statuto"],
    "Servizi Demografici": ["servizi demografici", "anagrafe", "stato civile", "elettorale", "pubblicazione di matrimonio", "matrimonio", "cittadinanza"],
    "Pareri e Allegati": ["parere di regolarità tecnica", "parere tecnico", "parere contabile", "allegato tecnico", "certificato di pagamento"],
}

SUBCATEGORY_RULES = {
    "Approvazione Progetto": ["approvazione progetto"],
    "Liquidazione": ["liquidazione", "pagamento", "saldo"],
    "Affidamento Incarico": ["affidamento incarico", "conferimento incarico"],
    "Bando": ["bando", "avviso pubblico"],
    "Concorso": ["concorso", "selezione"],
    "Progressione Verticale": ["progressione verticale", "selezione interna"],
    "Riaccertamento Residui": ["riaccertamento residui"],
    "Variazione di Bilancio": ["variazione di bilancio"],
    "Nomina": ["nomina", "costituzione"],
}

def normalize_amount(txt):
    """Converte stringhe tipo '12.345,67' o '12 345,67' in float 12345.67"""
    if not txt: return None
    s = txt.strip().replace(" ", "").replace("'", "")
    # se ha sia . che ,: di solito . come separatore migliaia, , decimali
    if "." in s and "," in s:
        s = s.replace(".", "").replace(",", ".")
    else:
        # se solo virgola, usala come decimale
        if "," in s and "." not in s:
            s = s.replace(",", ".")
        # se solo punto: assumilo come decimale (ok)
    try:
        return float(s)
    except Exception:
        return None

def extract_importi(text: str) -> List[float]:
    """Estrae tutti gli importi (numerici e in lettere) da un testo"""
    importi = set()
    
    for pattern in IMPORTI_REGEX[:8]:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            importo_clean = re.sub(r"[^\d,]", "", str(match))
            if importo_clean:
                try:
                    importo_float = float(importo_clean.replace(",", "."))
                    if 0 < importo_float < 100_000_000:
                        importi.add(importo_float)
                except: pass
                
    for pattern in IMPORTI_REGEX[8:]:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            testo_importo = match[0] if isinstance(match, tuple) else match
            numero = lettere_to_numero(testo_importo)
            if numero: importi.add(numero)
            
    return sorted(importi, reverse=True)

def keyword_hits(haystack, keywords):
    hits = []
    if pd.isna(haystack):
        haystack = ""
    else:
        haystack = str(haystack)
    for keyword in keywords:
        if re.search(r'(?<!\w)' + re.escape(keyword) + r'(?!\w)', haystack, re.IGNORECASE):
            hits.append(keyword)
    return hits

from ..rag.llm_factory import get_llm_client

def extract_metadata_with_gemini(text: str, max_retries: int = 5) -> dict:
    """Usa l'LLM (Gemini o Mistral) con retry ed exponential backoff per l'estrazione metadati."""
    # Throttle automatico per rispettare i limiti del Free Tier di Google (Max 15 Richieste al Minuto)
    time.sleep(4.5)
    prompt = """
    Estrai i seguenti metadati dal testo dell'atto amministrativo fornito.
    Rispondi SOLO con un oggetto JSON valido con la seguente struttura:
    {
        "cig": "...", (oppure null se non presente)
        "cup": "...", (oppure null se non presente)
        "importi_raw": ["...", "..."], (lista di stringhe con gli importi in euro. ATTENZIONE: se l'atto è un S.A.L. o una liquidazione, metti per primo l'importo effettivamente pagato/liquidato e ignora il totale dell'appalto originale)
        "beneficiario": "...", (SOLO nome o denominazione della ditta/persona. NON inserire ASSOLUTAMENTE frasi o premesse giuridiche come "Visto...", "Accertata la competenza...", se non chiaro restituisci null)
        "responsabile": "...", (SOLO Nome e Cognome di persona fisica, NON inserire intere frasi o riferimenti normativi, altrimenti restituisci null)
        "oggetto": "..." (oggetto dell'atto, stringa pulita)
    }
    Testo:
    """ + text[:15000]
    
    result = get_llm_client(prompt)
    if not result:
        return {}

    # Sanitizzazione output (evita bug 'list object has no attribute upper')
    for key in ["cig", "cup", "beneficiario", "responsabile", "oggetto"]:
        if key in result and isinstance(result[key], list):
            result[key] = " ".join([str(x) for x in result[key] if x]) if result[key] else None
        if key in result and result[key] == "null":
            result[key] = None

    return result

def extract_quadro_economico_vision(pdf_path: Path, max_retries: int = 3) -> dict:
    """Usa Gemini Multimodal (Vision) con retry ed exponential backoff."""
    if not genai or not os.environ.get("GOOGLE_API_KEY"):
        return {}
        
    for attempt in range(max_retries):
        try:
            images = list(_render_pdfium_images(pdf_path, dpi=150, max_pages=4))
            if not images:
                return {}

            genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
            model_name = os.environ.get("GOOGLE_LLM_MODEL", "gemini-1.5-flash")
            model = genai.GenerativeModel(model_name, generation_config={"response_mime_type": "application/json"})
            
            prompt = """
            Analizza le immagini di questo atto amministrativo.
            Cerca una tabella relativa al "Quadro Economico", "Riepilogo Spese" o "Computo Metrico".
            Se la trovi, estrai i dati in formato JSON strutturato con un array di voci.
            Rispondi SOLO con un oggetto JSON valido con la seguente struttura:
            {
                "quadro_economico_trovato": true,
                "totale_complessivo": 12345.67,
                "voci": [
                    {"descrizione": "Lavori a base d'asta", "importo": 10000.00},
                    {"descrizione": "IVA 22%", "importo": 2200.00}
                ]
            }
            Se non trovi nessun quadro economico o tabella di riepilogo, rispondi {"quadro_economico_trovato": false}.
            """
            
            response = model.generate_content([prompt] + images)
            raw_text = response.text.strip()
            
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:-3].strip()
            elif raw_text.startswith("```"):
                raw_text = raw_text[3:-3].strip()
                
            # Throttling per visione
            time.sleep(5)
            
            return json.loads(raw_text)
        except Exception as e:
            msg = str(e).lower()
            if "429" in msg or "quota" in msg or "exhausted" in msg:
                wait_time = (attempt + 1) * 30
                logger.warning(f"[Vision Quota] Limite raggiunto (Tentativo {attempt+1}/{max_retries}). Pausa di {wait_time}s...")
                time.sleep(wait_time)
                continue
            logger.error(f"Fallita estrazione Quadro Economico (Tentativo {attempt+1}): {e}")
            if attempt == max_retries - 1:
                return {}
    return {}

def classify_document(oggetto, text, rf_model=None):
    """Classifica con punteggio, evitando che l'ordine delle categorie decida da solo."""
    oggetto_str = "" if pd.isna(oggetto) else str(oggetto)
    text_str = "" if pd.isna(text) else str(text)
    
    haystacks = [(oggetto_str, 4), (text_str[:3500], 1)]
    scores = {}
    for category, keywords in CATEGORY_RULES.items():
        score = 0
        matched = []
        for haystack, weight in haystacks:
            hits = keyword_hits(haystack, keywords)
            score += len(haystack) * weight
            matched.extend(hits)
        if score:
            scores[category] = (score, sorted(set(matched)))

    category = None
    confidence = None
    terms = []

    if scores:
        ranked = sorted(scores.items(), key=lambda item: (-item[1][0], item[0]))
        category = ranked[0][0]
        confidence = "high"
        terms = ranked[0][1][1]
        if len(ranked) > 1 and ranked[0][1][0] == ranked[1][1][0]:
            confidence = "ambiguous"

    # ML Fallback per documenti ambigui o non classificati
    if (category is None or confidence == "ambiguous") and rf_model is not None:
        text_preview = normalize_text_for_ml(text_str)[:1200]
        if len(text_preview) > 50:
            try:
                max_prob = np.max(rf_model.predict_proba([text_preview]))
                if max_prob >= 0.50:
                    category = rf_model.predict([text_preview])[0]
                    confidence = "ml_predicted"
                    terms = ["random_forest"]
            except Exception as e:
                logger.warning(f"Errore durante la predizione ML: {e}")

    subcategory = None
    for sub, sub_keywords in SUBCATEGORY_RULES.items():
        if keyword_hits(oggetto_str + " " + text_str, sub_keywords):
            subcategory = sub
            break
    return category, subcategory, confidence, ",".join(terms) if terms else None

def infer_doc_type(filename, text):
    name = filename.lower()
    head = (text or "")[:2500].lower()
    name_rules = [
        ("VistoContabile", ("vistocontabile", "visto_contabile")),
        ("AttestazionePubblicazione", ("attestazionepubblicazione", "certificatopubblicazione")),
        ("Elenco", ("elencoelettori", "elenco_", "_elenco")),
        ("Ordinanza", ("ordinanza", "ordinanzesindacali")),
        ("Decreto", ("decreto", "decretosindacale")),
        ("Determinazione", ("determina", "determinazione")),
        ("Delibera", ("delibera", "deliberazione")),
        ("Bando", ("bando",)),
        ("Avviso", ("avviso",)),
    ]
    for label, needles in name_rules:
        if any(n in name for n in needles):
            return label

    rules = [
        ("VistoContabile", ("visto di regolarità contabile", "visto di regolarita contabile")),
        ("AttestazionePubblicazione", ("certificato di pubblicazione", "attestazione di pubblicazione")),
        ("Elenco", ("elenco dei cittadini", "elenco elettori")),
        ("Ordinanza", ("ordinanza sindacale", "ordinanza n.")),
        ("Decreto", ("decreto sindacale", "decreto n.")),
        ("Determinazione", ("determina", "determinazione")),
        ("Delibera", ("delibera", "deliberazione")),
        ("Bando", ("bando",)),
        ("Avviso", ("avviso",)),
    ]
    for label, needles in rules:
        if any(n in head for n in needles):
            return label
    return "unknown"

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

def is_accounting_relevant_extended(text: str) -> bool:
    """Controlla rilevanza contabilità con pattern estesi."""
    for pattern in EXTENDED_ACCOUNTING_PATTERNS:
        if pattern.search(text):
            return True
    return False

def is_personnel_competence_relevant_extended(text: str) -> bool:
    """Controlla rilevanza competenze con pattern estesi."""
    for pattern in COMPILED_PATTERNS.values():
        if pattern.search(text):
            return True
    return False

def extract_all_metadata(pdf_path: str, filename: str = "") -> Dict:
    """Estrae TUTTI i metadati con pattern estesi."""
    if not filename:
        filename = os.path.basename(pdf_path)

    # Determina tipo documento
    doc_type = "altro"
    if any(t in filename for t in ["Determinazione", "Determina"]):
        doc_type = "determinazione"
    elif "Delibera" in filename:
        doc_type = "delibera"
    elif "Ordinanza" in filename:
        doc_type = "ordinanza"
    elif "Numeraria" in filename:
        doc_type = "numeraria"
    elif "Avviso" in filename:
        doc_type = "avviso"
    elif "Bando" in filename:
        doc_type = "bando"
    elif "Atto" in filename:
        doc_type = "atto"

    # Leggi testo
    text = ""
    try:
        with open(pdf_path, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read()
    except:
        pass

    # Estrai con pattern estesi
    metadata = {
        'filename': filename,
        'doc_type': doc_type,
        'is_accounting_relevant': is_accounting_relevant_extended(text),
        'is_personnel_competence_relevant': is_personnel_competence_relevant_extended(text),
    }

    # Estrai CIG e CUP
    cig_cup = extract_cig_cup(text)
    metadata.update(cig_cup)

    # Estrai importi
    importi = extract_importi_extended(text)
    if importi:
        metadata['importi'] = importi
        metadata['importo_totale'] = sum(importi)

    # Estrai date
    dates = extract_date(text)
    if dates:
        metadata['date'] = dates

    # Estrai nomi propri
    nomi = extract_nomi_propri(text)
    if nomi:
        metadata['nomi_propri'] = list(set(nomi))  # Rimuovi duplicati

    # Estrai competenze del personale
    competences = extract_personnel_competences(text)
    metadata['personnel_competences'] = [c.__dict__ for c in competences]

    # Estrai riferimenti a decreti
    metadata['decree_references'] = extract_decree_references(text)

    # Match pattern specifici per tipologia
    category_patterns = get_category_specific_patterns(doc_type)
    matched_patterns = match_patterns_in_text(text, category_patterns)
    if matched_patterns:
        metadata['matched_patterns'] = matched_patterns

    return metadata

def normalize_text_for_ml(text):
    """Normalizza solo spazi e caratteri di controllo, senza perdere contenuto utile."""
    if pd.isna(text):
        text = ""
    else:
        text = str(text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]+", " ", text)
    return " ".join(text.split())

def text_features(text):
    text = text or ""
    lower = text.lower()
    words = re.findall(r"\w+", lower, flags=re.UNICODE)
    years = sorted(set(re.findall(r"\b20\d{2}\b", text)))
    return {
        "text_chars": len(text),
        "text_words": len(words),
        "unique_words": len(set(words)),
        "euro_mentions": len(re.findall(r"€| euro\b", lower)),
        "cig_mentions": len(re.findall(r"\bcig\b", lower)),
        "cup_mentions": len(re.findall(r"\bcup\b", lower)),
        "date_mentions": len(re.findall(r"\b\d{1,2}/\d{1,2}/20\d{2}\b", text)),
        "years_mentioned": ",".join(years),
    }


def extract_from_pdf(path: Path, use_llm: bool = False, rf_model=None, text_dir: Path = None, ente_nome: str = "avella") -> dict:
    """Estrae testo e cattura campi principali da un PDF (testuale -> OCR fallback)."""
    
    # Gestione preliminare dei file .p7m
    is_p7m = path.name.lower().endswith(".p7m")
    pdf_content_bytes = None
    if is_p7m:
        pdf_content_bytes = extract_p7m_content(path)
        if not pdf_content_bytes:
            return {"pdf_name": path.name, "pdf_path": str(path), "source": "p7m_extraction_failed"}
        # Usiamo i byte estratti come se fossero il file originale
        path_for_parsing = pdf_content_bytes
    else:
        path_for_parsing = str(path)


    out = {
        "pdf_name": path.name,
        "pdf_path": str(path),
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
        "is_visto_contabile": ("VistoContabile" in path.name),
        "source": "text",   # 'text' o 'ocr'
        "accounting_relevant": False,
        "missing_amount_expected": False,
        "veridicità_score": 0,
        "solidità_globale": 0,
        "is_personnel_competence_relevant": False,
        "personnel_competences": "[]",
        "decree_references": "[]"
    }

    # 1) Verifica se esiste già un file di testo pre-generato (es. dal backend C#)
    text_file_path = text_dir / f"{path.stem}.txt" if text_dir else None
    if text_file_path and text_file_path.exists():
        text_one = text_file_path.read_text(encoding="utf-8", errors="ignore")
        text_one = " ".join(text_one.split())
        out["source"] = "csharp_extracted_text"
    else:
        # 2) Tentativo testuale nativo Python (Fallback)
        try:
            txt_raw = extract_text_pdf(path_for_parsing) or ""
        except Exception:
            txt_raw = ""

        text_one = " ".join((txt_raw or "").split())

        # Soglia: se testo è molto corto, prova OCR
        if len(text_one) < 500:
            probe_txt, good = ocr_pdf_probe(path_for_parsing, dpi=400, pages=(1,2))
            if good or len(probe_txt) > len(text_one):
                full_txt = ocr_pdf_full(path_for_parsing, dpi=400)
                if len(full_txt) > len(text_one):
                    text_one = full_txt
                    out["source"] = "ocr"
            else:
                # DOCUMENTI DIFFICILI: Fallback su Mistral OCR
                from llm_factory import mistral_ocr
                logger.info(f"Tesseract insufficiente per {path.name}, provo Mistral OCR (Documento Difficile)...")
                m_txt = mistral_ocr(str(path_for_parsing))
                if m_txt and "[MISTRAL_OCR_PENDING]" not in m_txt:
                    text_one = m_txt
                    out["source"] = "mistral_ocr"
                    logger.info("Recupero testo riuscito con Mistral OCR.")

    text_one = remove_boilerplate(text_one)
    text_one = normalize_text_for_ml(text_one)
    out["_text"] = text_one
    out["text_sha256"] = hashlib.sha256(text_one.encode("utf-8", errors="ignore")).hexdigest()
    out.update(text_features(text_one))

    # --- Competenze Personale ---
    out["is_personnel_competence_relevant"] = is_personnel_competence_relevant(text_one)
    out["personnel_competences"] = json.dumps([c.__dict__ for c in extract_personnel_competences(text_one)], ensure_ascii=False)
    out["decree_references"] = json.dumps(extract_decree_references(text_one), ensure_ascii=False)

    # Determiniamo in anticipo la natura giuridica del documento
    out["doc_type"] = infer_doc_type(path.name, text_one)

    # --- Estrazione Avanzata (Regex Potenziate) ---
    adv_data = {}
    if advanced_extractor:
        # Determina confidenza OCR di base
        ocr_confidence = 0.85 if out.get("source") == "ocr" else 1.0
        
        if hasattr(advanced_extractor, 'extract_entities_full'):
            adv_data = advanced_extractor.extract_entities_full(text_one, doc_type=out["doc_type"], ocr_conf=ocr_confidence)
        else:
            adv_data = advanced_extractor.extract_entities(text_one, doc_type=out["doc_type"])

    # Aggiorniamo out con i metadati forensi (confidence e metodi)
    if adv_data.get("confidence"):
        out["veridicità_score"] = int(adv_data.get("confidence", 0) * 100)
    
    out["anomalie"] = adv_data.get("forensic_flags")
    out["extraction_method"] = adv_data.get("extraction_method")
    out["trace_json"] = adv_data.get("trace_json")
    out["beneficiario_raw"] = adv_data.get("beneficiario_raw")
    out["layout_confidence"] = adv_data.get("layout_confidence")

    # --- Estrazione via LLM (Opzionale) ---
    llm_data = {}
    if use_llm:
        llm_data = extract_metadata_with_gemini(text_one)
        
        # Applichiamo la Vision API solo se il documento è di natura contabile o un Lavoro Pubblico
        if out.get("accounting_relevant") or out.get("category") == "Lavori Pubblici":
            vision_data = extract_quadro_economico_vision(path)
            if vision_data.get("quadro_economico_trovato"):
                out["quadro_economico"] = json.dumps(vision_data.get("voci", []), ensure_ascii=False)

    # --- Oggetto, Numero Atto, Registro Generale ---
    if llm_data.get("oggetto"):
        out["oggetto"] = llm_data["oggetto"]
    else:
        m = RX_OGGETTO.search(text_one)
        if m:
            oggetto_estratto = m.group(1).strip()
            # Tronca se troppo lungo
            if len(oggetto_estratto) > 1500:
                oggetto_estratto = oggetto_estratto[:1500] + "..."
            out["oggetto"] = oggetto_estratto

    # --- Classificazione ---
    category, subcategory, confidence, terms = classify_document(out["oggetto"], text_one, rf_model=rf_model)
    out["category"] = category
    out["subcategory"] = subcategory
    out["classification_confidence"] = confidence
    out["classification_terms"] = terms
    out["accounting_relevant"] = is_accounting_relevant(text_one, out["doc_type"], out["category"])

    # --- importi ---
    amts_norm = []
    if llm_data.get("importi_raw"):
        for amount_raw in llm_data["importi_raw"]:
            normalized = normalize_amount(amount_raw)
            if normalized is not None:
                amts_norm.append(normalized)
    else:
        amts_norm = extract_importi(text_one)
        
    out["importi_raw"] = [str(a) for a in amts_norm]
    
    # Gestione S.A.L. e Liquidazioni: Evitiamo la doppia imputazione (totale progetto vs importo liquidato)
    importo_specifico_liquidazione = None
    if out["subcategory"] == "Liquidazione" or "s.a.l." in text_one.lower() or "sal n." in text_one.lower():
        m_liq = RX_IMPORTO_LIQUIDATO.search(text_one)
        if m_liq:
            importo_specifico_liquidazione = normalize_amount(m_liq.group(1))
            
    if importo_specifico_liquidazione and importo_specifico_liquidazione > 0:
        out["importo_max"] = importo_specifico_liquidazione
    else:
        out["importo_max"] = adv_data.get("importo_max_estratto") or (max(amts_norm) if amts_norm else None)
        
    out["importo_sum"] = sum(amts_norm) if amts_norm else None
    out["importi_count"] = len(amts_norm)
    out["missing_amount_expected"] = bool(out["accounting_relevant"] and out["doc_type"] != "VistoContabile" and not amts_norm)

    m = RX_NUM_ATTO.search(text_one)
    if m:
        out["numero_atto"] = m.group(1)
        out["data_atto"] = m.group(2)

    m = RX_REG_GEN.search(text_one)
    if m:
        out["numero_registro"] = m.group(1)
        out["data_registro"] = m.group(2)

    # --- CIG / CUP ---
    try:
        if llm_data.get("cig"): out["cig"] = llm_data["cig"].upper()
        elif adv_data.get("cig_estratto"): out["cig"] = adv_data["cig_estratto"].upper()
        else:
            m = RX_CIG.search(text_one)
            if m: out["cig"] = m.group(1).upper()
            
        if llm_data.get("cup"): out["cup"] = llm_data["cup"].upper()
        elif adv_data.get("cup_estratto"): out["cup"] = adv_data["cup_estratto"].upper()
        else:
            m = RX_CUP.search(text_one)
            if m: out["cup"] = m.group(1).upper()
    except Exception as e:
        logger.warning(f"Errore durante l'estrazione di CIG/CUP per {path.name}: {e}")

    # --- LegalURN (NIR Standard) ---
    out["legal_urn"] = generate_legal_urn(out.get("doc_type"), out.get("data_atto"), out.get("numero_atto"), ente_nome=ente_nome)

    # --- Compliance (Firme e Accessibilità) ---
    compliance = check_normative_compliance(path)
    out.update(compliance)

    # --- beneficiario/fornitore/aggiudicatario ---
    if llm_data.get("beneficiario"):
        out["beneficiario"] = llm_data["beneficiario"].strip()
    else:
        for rx_pattern in RX_BENEF:
            m = rx_pattern.search(text_one)
            if m:
                beneficiario_text = m.group(1).strip(" :;-|")
                beneficiario_text = re.sub(r'\s*-\s*Progressivo Fornitore.*', '', beneficiario_text, flags=re.IGNORECASE)
                if len(beneficiario_text) < 150:
                    out["beneficiario"] = beneficiario_text.strip()
                    break
    
    out["piva_beneficiario"] = adv_data.get("piva_beneficiario")

    iban_estratto = adv_data.get("iban_estratto")
    if not iban_estratto:
        m_iban = RX_IBAN.search(text_one)
        if m_iban:
            iban_estratto = re.sub(r'\s+', '', m_iban.group(0)).upper()
    out["iban"] = iban_estratto

    out["codice_appalti"] = adv_data.get("codice_appalti")
    out["tipo_procedura"] = adv_data.get("tipo_procedura")
    out["importo_lettere"] = adv_data.get("importo_lettere")
    
    anomalia_corrente = out.get("anomalie", "")
    anomalia_nuova = adv_data.get("anomalie_rilevate")
    if anomalia_nuova:
        out["anomalie"] = f"{anomalia_corrente} | {anomalia_nuova}" if anomalia_corrente else anomalia_nuova

    cap_adv = adv_data.get("capitolo")
    # Filtro antifrode: evitiamo di scambiare il CAP postale (es. 83022) per un Capitolo di spesa
    if cap_adv and not (len(str(cap_adv)) == 5 and str(cap_adv).isdigit()):
        out["capitolo"] = cap_adv

    if adv_data.get("beneficiario"):
        out["beneficiario"] = adv_data.get("beneficiario")
        
    if adv_data.get("beneficiario_raw"):
        out["beneficiario_raw"] = adv_data.get("beneficiario_raw")

    if adv_data.get("responsabile"):
        out["responsabile"] = adv_data.get("responsabile")

    if adv_data.get("impegno_num"):
        out["impegno_num"] = adv_data.get("impegno_num")
    # --- Responsabile, Area e Ruolo (Rule-Based NER) ---
    if llm_data.get("responsabile"):
        out["rup_nome"] = str(llm_data["responsabile"]).strip().upper()
    else:
        attori = estrai_attori_procedimento(text_one)
        out["rup_nome"] = attori["nome"]
        out["rup_area"] = attori["area"]
        out["rup_ruolo"] = attori["ruolo"]

    # Mantieni retrocompatibilità per 'responsabile'
    out["responsabile"] = normalizza_rup(out.get("rup_nome") or out.get("responsabile"))

    # --- Override Categoria se LLM ha alta confidenza ---
    conf_attuale = out.get("classification_confidence")
    is_low_conf = conf_attuale in ("ambiguous", None) or (isinstance(conf_attuale, (int, float)) and conf_attuale < 0.70)
    if llm_data.get("category") and is_low_conf:
        out["category"] = llm_data["category"]
        out["classification_confidence"] = 0.88 # Badge confidenza LLM
        out["extraction_method"] = (out.get("extraction_method") or "") + "+LLM_CAT"


    # --- impegno/accertamento ---
    m = RX_IMPEGNO.search(text_one)
    if m:
        out["impegno_num"]  = m.group(1)
        if len(m.groups()) > 1 and m.group(2):
            out["impegno_anno"] = m.group(2)
            
    m = RX_ACCERT.search(text_one)
    if m:
        out["accert_num"]  = m.group(1)
        if len(m.groups()) > 1 and m.group(2):
            out["accert_anno"] = m.group(2)
        

    # --- capitolo & PEG ---
    m = RX_CAPITOLO.search(text_one)
    if m:
        cap_val = m.group(1)
        if not out.get("capitolo") and not (len(cap_val) == 5 and cap_val.isdigit()):
            out["capitolo"] = cap_val
    m = RX_PEG.search(text_one)
    if m:
        out["peg_riga"] = m.group(0)

    # --- Digital Twin Event Creation ---
    doc_type_enum, event_type_enum = route_document(text_one)

    actors = []
    if out.get("rup_nome") and out["rup_nome"] != "NON IDENTIFICATO":
        actors.append(Actor(
            name=out["rup_nome"],
            actor_type=ActorType.RUP,
            role=out.get("rup_ruolo"),
            area=out.get("rup_area")
        ))
    if out.get("beneficiario") and out["beneficiario"] not in ["NON IDENTIFICATO", "DIVERSI/NON APPLICABILE"]:
         actors.append(Actor(
            name=out["beneficiario"],
            actor_type=ActorType.BENEFICIARIO
        ))

    event = AdministrativeEvent(
        event_type=event_type_enum,
        document_type=doc_type_enum,
        document_id=path.stem,
        document_number=out.get("numero_atto"),
        document_date=out.get("data_atto"),
        title=out.get("oggetto"),
        economic_value=out.get("importo_max"),
        cig=out.get("cig"),
        cup=out.get("cup"),
        actors=actors,
        confidence=0.8, # Placeholder confidence
        raw_text=text_one,
        metadata={
            "urn": out.get("legal_urn"),
            "source_file": path.name
        }
    )
    procedure_builder.add_event(event)
    return out


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
    except Exception:
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

def extract_full_metadata(pdf_path: Path, filename: str = "") -> dict:
    """Estrae tutti i metadati da un singolo PDF inclusa la chiave accounting_relevant."""
    return extract_from_pdf(pdf_path, use_llm=False)

def process_directory_to_csv(pdf_dir: Path, output_csv: Path, max_files: int = None) -> pd.DataFrame:
    """Elabora tutti i PDF in una directory e salva i risultati in un file CSV."""
    results = []
    for i, pdf_file in enumerate(pdf_dir.glob("*.pdf")):
        if max_files and i >= max_files:
            break
        results.append(extract_full_metadata(pdf_file, pdf_file.name))
    df = pd.DataFrame(results)
    df.to_csv(output_csv, index=False, encoding="utf-8")
    return df

def main():
    args = build_parser().parse_args()
    if pytesseract is None:
        logger.warning("pytesseract non installato: OCR disattivato, continuo con testo PDF estraibile.")

    if args.base:
        base = Path(args.base)
    else:
        base = Path(f"data/{args.ente}/albo_download")
        
    csv_path = Path(args.csv) if args.csv else base / "albo_metadati.csv"
    pdf_dir = Path(args.pdf_dir) if args.pdf_dir else base / "pdf"
    out_xlsx = base / "albo_analisi.xlsx"
    out_csv_allegati = base / "allegati_parsed.csv"
    out_csv_atti = base / "atti_parsed.csv"
    out_csv_features = base / "documenti_features.csv"
    text_dir = base / "texts" # Definizione di text_dir
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
    else:
        # ---------------------------------------------------------
        # INTEGRAZIONE MODELLO SAAS GLOBALE (Federated Learning)
        # ---------------------------------------------------------
        global_model_path = Path("assets/models/global_rf_model.joblib")
        if joblib is None:
            logger.warning("joblib non installato: salto il caricamento del modello globale.")
        elif global_model_path.exists():
            logger.info(f"Caricamento Modello ML Globale SaaS da: {global_model_path}")
            try:
                rf_model = joblib.load(global_model_path)
                logger.info("Cervello Globale attivato con successo. L'Ente beneficia dell'addestramento centralizzato.")
            except Exception as e:
                logger.error(f"Errore nel caricamento del modello globale: {e}")
        else:
            logger.warning(f"Modello Globale non trovato in {global_model_path}. Assicurati di aver eseguito il primo addestramento.")

    # Assicura che la directory per i file di testo esista
    text_dir.mkdir(parents=True, exist_ok=True)

    # 1) Metadati
    if not csv_path.exists():
        logger.error(f"Nessun dato trovato in {csv_path}. Devi prima eseguire lo scraper (new_albo_scraper.py) per scaricare i dati dell'ente.")
        sys.exit(1)
        
    df = pd.read_csv(csv_path, encoding="utf-8", sep=",")
    # normalizza colonne attese dallo scraper
    expected = ["page_url","titolo","numero","data_pubblicazione","tipologia","ufficio","oggetto","dettaglio_url","allegati"]
    for c in expected:
        if c not in df.columns: df[c] = None

    # date pulite
    def to_date(x):
        if pd.isna(x) or not str(x).strip():
            return pd.NaT
        try:
            return dateparser.parse(str(x), dayfirst=True)
        except Exception:
            return pd.NaT
    df["data_dt"] = df["data_pubblicazione"].apply(to_date)

    # 2) Esplodi allegati
    df["allegati_list"] = df["allegati"].apply(safe_literal_list)
    rows = []
    for idx, r in df.iterrows():
        for url in r["allegati_list"]:
            rows.append({
                "titolo": r["titolo"],
                "numero": r["numero"],
                "data_pubblicazione": r["data_pubblicazione"],
                "data_dt": r["data_dt"],
                "tipologia": r["tipologia"],
                "ufficio": r["ufficio"],
                "oggetto": r["oggetto"],
                "dettaglio_url": r["dettaglio_url"],
                "allegato_url": url
            })
    dfa = pd.DataFrame(rows)

    # 3) Processa tutti i PDF locali indipendentemente dai metadati
    logger.info("Processando PDF locali...")
    files = list(pdf_dir.glob("*.pdf")) + list(pdf_dir.glob("*.php")) + list(pdf_dir.glob("*.p7m"))
    logger.info(f"Trovati {len(files)} file PDF/PHP")
    
    # Caricamento cache dei PDF già elaborati per evitare chiamate inutili all'API
    processed_cache = {}
    if out_csv_allegati.exists() and not args.force:
        try:
            df_cache = pd.read_csv(out_csv_allegati, encoding="utf-8")
            # Carichiamo i vecchi record in un dizionario con chiave il nome del pdf
            processed_cache = df_cache.set_index('pdf_name').to_dict('index')
            logger.info(f"Trovati {len(processed_cache)} PDF già elaborati nel CSV. Verranno saltati per risparmiare tempo e API.")
        except Exception as e:
            logger.warning(f"Impossibile caricare la cache dei PDF esistenti: {e}")
    elif args.force:
        logger.info("Flag --force attivo: la cache esistente verrà ignorata.")

    # 4) Parsing PDF
    parsed_pdfs = []
    corpus_rows = []
    
    with metrics.start_operation("analisi_pdf") as op:
        seen_hashes = set()
        
        for idx, pdf_file in enumerate(files):
            logger.info(f"Processando {idx + 1}/{len(files)}: {pdf_file.name}")
                
            if pdf_file.name in processed_cache:
                info = processed_cache[pdf_file.name]
                
                # Se abbiamo il modello ML, rivalutiamo al volo i documenti incerti presenti in cache
                if rf_model is not None and info.get("classification_confidence") in (None, "ambiguous", "unknown"):
                    cat, sub, conf, terms = classify_document(info.get("oggetto"), info.get("text_preview"), rf_model=rf_model)
                    info["category"] = cat
                    info["subcategory"] = sub
                    info["classification_confidence"] = conf
                    info["classification_terms"] = terms
                    
                # Deduplicazione documenti in cache
                text_hash = info.get("text_sha256")
                if text_hash and text_hash in seen_hashes:
                    continue
                seen_hashes.add(text_hash)

                info["pdf_name"] = pdf_file.name # Ripristiniamo la chiave
                info["pdf_path"] = str(pdf_file) # Aggiorniamo il path del PDF al sistema corrente
                
                text_path = text_dir / (pdf_file.stem + ".txt")
                info["text_path"] = str(text_path) # Forziamo il path del txt al sistema corrente
                parsed_pdfs.append(info)
                
                # Ricostruiamo la riga per il corpus testuale (RAG) leggendo il .txt se la cache l'ha saltato
                if not args.no_corpus:
                    text_full = text_path.read_text(encoding="utf-8", errors="ignore") if text_path.exists() else ""
                    corpus_rows.append({
                        **info,
                        "text": text_full,
                    })
                continue
                
            info = extract_from_pdf(pdf_file, use_llm=args.use_llm, rf_model=rf_model, ente_nome=args.ente)
            
            # Deduplicazione documenti appena estratti
            text_hash = info.get("text_sha256")
            if text_hash and text_hash in seen_hashes:
                continue
            seen_hashes.add(text_hash)

            text_full = info.pop("_text", "")
            text_name = pdf_file.stem + ".txt"
            text_path = text_dir / text_name
            info["text_path"] = str(text_path)
            info["text_preview"] = text_full[:1200]
            corpus_rows.append({
                **info,
                "text": text_full,
            })
            parsed_pdfs.append(info)
        
        op.set_items_processed(len(files))
    
    dfp = pd.DataFrame(parsed_pdfs)
    
    # --- Digital Twin Procedure Analysis ---
    logger.info("Costruzione e analisi dei procedimenti (Digital Twin)...")
    all_procedures = procedure_builder.get_all_procedures()
    
    # Salva i procedimenti e le anomalie
    procedures_path = base / "procedures.json"
    anomalies_path = base / "anomalies.json"

    with open(procedures_path, 'w', encoding='utf-8') as f:
        json.dump([p.to_dict() for p in all_procedures], f, indent=2, ensure_ascii=False)
    logger.info(f"Salvati {len(all_procedures)} procedimenti in {procedures_path}")

    anomalies = procedure_builder.detect_anomalies()
    with open(anomalies_path, 'w', encoding='utf-8') as f:
        json.dump(anomalies, f, indent=2, ensure_ascii=False)
    logger.info(f"Rilevate e salvate {len(anomalies)} anomalie in {anomalies_path}")

    # --- INTEGRAZIONE CERVELLO NORMATIVO: Merge Metadati Originali ---
    if csv_path.exists():
        logger.info(f"Merging con metadati originali da {csv_path.name} per precisione oggetti...")
        df_meta = pd.read_csv(csv_path)
        # Assumiamo che 'allegati' nel CSV contenga il nome del file o URL che punta al PDF
        # Dobbiamo estrarre il filename pulito per il match
        df_meta['filename_meta'] = df_meta['allegati'].apply(lambda x: Path(str(x)).name if pd.notna(x) else None)
        
        # Elimina colonne aggiunte in esecuzioni precedenti per evitare duplicati
        cols_to_drop = ['filename_meta', 'oggetto_orig', 'tipologia', 'doc_type_meta']
        dfp = dfp.drop(columns=[c for c in cols_to_drop if c in dfp.columns])

        dfp = pd.merge(dfp, df_meta[['filename_meta', 'oggetto', 'tipologia']], 
                       left_on='pdf_name', right_on='filename_meta', how='left', suffixes=('', '_orig'))
        
        # Sovrascrivi l'oggetto estratto dal PDF (spesso troncato) con quello perfetto del portale
        if 'oggetto_orig' in dfp.columns:
            # Assicuriamoci che dfp['oggetto_orig'] sia una Series
            if isinstance(dfp['oggetto_orig'], pd.DataFrame):
                dfp['oggetto_orig'] = dfp['oggetto_orig'].iloc[:, 0]
            dfp['oggetto'] = dfp['oggetto_orig'].fillna(dfp['oggetto'])
        if 'tipologia' in dfp.columns:
            dfp['doc_type_meta'] = dfp['tipologia'].fillna(dfp['doc_type'])

    # --- Normalizzazione Beneficiari e RUP ---
    if 'beneficiario' in dfp.columns:
        dfp['beneficiario'] = dfp['beneficiario'].apply(normalizza_beneficiario)
    if 'responsabile' in dfp.columns:
        dfp['responsabile'] = dfp['responsabile'].apply(normalizza_rup)

    logger.info(f"PDF processati: {len(dfp)}")
    logger.info(f"PDF con OCR: {(dfp['source']=='ocr').sum()}")
    logger.info(f"PDF con testo: {(dfp['source']=='text').sum()}")

    # Statistiche sul tipo di documento
    logger.info(f"Statistiche tipo documento:\n{dfp['doc_type'].value_counts().to_string()}")
    
    # 6) Costruisci tabella per atto (collapse allegati)
    def get_atto_group(filename):
        stem = Path(filename).stem
        return re.sub(r'_\d+$', '', stem)

    dfp["atto_group"] = dfp["pdf_name"].apply(get_atto_group)

    # Funzioni di aggregazione avanzata con priorità semantica
    def priority_doc_type(x):
        vals = x.dropna().tolist()
        if "Determinazione" in vals: return "Determinazione"
        if "Delibera" in vals: return "Delibera"
        if "Ordinanza" in vals: return "Ordinanza"
        if "Decreto" in vals: return "Decreto"
        return next(iter([i for i in vals if i != "unknown"]), "unknown")

    def priority_visto(group_df, col_name, fallback_agg):
        # Se c'è un Visto Contabile e ha il dato, usa quello
        visto_rows = group_df[group_df["doc_type"] == "VistoContabile"]
        if not visto_rows.empty:
            visto_val = visto_rows[col_name].dropna()
            if not visto_val.empty:
                if fallback_agg == "max": return visto_val.max()
                elif fallback_agg == "first": return visto_val.iloc[0]
                else: return " | ".join(visto_val.unique())

        # Altrimenti usa il fallback su tutto il gruppo
        all_val = group_df[col_name].dropna()
        if all_val.empty: return None
        if fallback_agg == "max": return all_val.max()
        elif fallback_agg == "first": return all_val.iloc[0]
        else: return " | ".join(all_val.astype(str).unique())

    # Raggruppiamo applicando le regole custom
    atti_records = []
    for nome_gruppo, group_df in dfp.groupby("atto_group", dropna=False):
        has_visto = "VistoContabile" in group_df["doc_type"].values
        record = {
            "atto_group": nome_gruppo,
            "doc_type": priority_doc_type(group_df["doc_type"]),
            "category": next(iter(group_df["category"].dropna()), None),
            "oggetto": next(iter(group_df["oggetto"].dropna()), None),
            "numero_atto": next(iter(group_df["numero_atto"].dropna()), None),
            "data_atto": next(iter(group_df["data_atto"].dropna()), None),
            "importo_max": priority_visto(group_df, "importo_max", "max"),
            "capitolo": priority_visto(group_df, "capitolo", "first"),
            "impegno_num": priority_visto(group_df, "impegno_num", "first"),
            "impegno_anno": priority_visto(group_df, "impegno_anno", "first"),
            "cig": ",".join(group_df["cig"].dropna().unique()),
            "cup": ",".join(group_df["cup"].dropna().unique()),
            "beneficiario": " | ".join(group_df["beneficiario"].dropna().unique()),
            "codice_appalti": next(iter(group_df["codice_appalti"].dropna()), None),
            "tipo_procedura": next(iter(group_df["tipo_procedura"].dropna()), None),
            "responsabile": next(iter(group_df["responsabile"].dropna()), None),
            "legal_urn": next(iter(group_df["legal_urn"].dropna()), None),
            "is_signed": group_df["is_signed"].any(),
            "is_accessible": group_df["is_accessible"].any(),
            "compliance_score": group_df["compliance_score"].mean(),
            "accounting_relevant": group_df["accounting_relevant"].any(),
            "has_visto_contabile": has_visto,
            "veridicità_score": group_df["veridicità_score"].max() + (20 if has_visto else 0),
            "anomalie": " | ".join(group_df["anomalie"].dropna().unique())
        }
        atti_records.append(record)

    df_atti = pd.DataFrame(atti_records)

    # Rimuoviamo le stringhe vuote spurie
    for col in ["cig", "cup", "beneficiario", "anomalie"]:
        df_atti[col] = df_atti[col].replace("", None)

    out_csv_failed = base / "failed_extractions.csv"
    failed_df = dfp[dfp["source"].isin(["p7m_extraction_failed", "error", "unknown"]) | (dfp["text_chars"].fillna(0) < 50)]

    # Top fornitori per somma importo_max
    fornitori = (dfp.dropna(subset=["beneficiario"])
                    .groupby("beneficiario", dropna=False)["importo_max"]
                    .sum().sort_values(ascending=False).reset_index()
                    .rename(columns={"importo_max":"importo_totale"}))

    # Statistiche base
    kpi_source = dfp.groupby("source", dropna=False)["importo_max"].agg(["count","sum"]).reset_index()
    kpi_visto  = dfp.groupby("is_visto_contabile", dropna=False)["importo_max"].agg(["count","sum"]).reset_index()
    kpi_doctype = dfp.groupby("doc_type", dropna=False)["importo_max"].agg(["count", "sum"]).reset_index()
    feature_cols = [
        "pdf_name", "doc_type", "category", "subcategory", "classification_confidence",
        "source", "text_sha256", "text_chars", "text_words", "unique_words",
        "euro_mentions", "cig", "cup", "cig_mentions", "cup_mentions", "date_mentions",
        "years_mentioned", "importo_max", "importo_sum", "importi_count",
        "accounting_relevant", "missing_amount_expected", "importo_lettere", "piva_beneficiario",
        "iban", "codice_appalti", "tipo_procedura", "quadro_economico", "anomalie",
        "extraction_method", "trace_json", "beneficiario_raw", "layout_confidence",
        "legal_urn", "is_signed", "is_accessible", "pdf_version", "compliance_score",
        "veridicità_score", "solidità_globale",
        "is_personnel_competence_relevant", "personnel_competences", "decree_references"
    ]
    dff = dfp[[c for c in feature_cols if c in dfp.columns]].copy()

    # 7) Salva CSV/Excel
    logger.info("Salvataggio CSV...")
    dfp.to_csv(out_csv_allegati, index=False, encoding="utf-8")
    dff.to_csv(out_csv_features, index=False, encoding="utf-8")
    if not args.no_corpus:
        text_dir.mkdir(parents=True, exist_ok=True)
        with open(out_corpus_jsonl, "w", encoding="utf-8") as f:
            for row in corpus_rows:
                text_path = Path(row["text_path"])
                text_path.write_text(row["text"], encoding="utf-8", errors="ignore")
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
    
    df_atti.to_csv(out_csv_atti, index=False, encoding="utf-8")
    if not failed_df.empty:
        failed_df.to_csv(out_csv_failed, index=False, encoding="utf-8")
    
    logger.info("CSV salvati con successo!")
    logger.info("Salvataggio Excel con motore 'xlsxwriter'...")
    
    # --- RECUPERO FEEDBACK UMANO PRIMA DI SOVRASCRIVERE L'EXCEL ---
    vecchie_correzioni = {}
    vecchie_anomalie = {}
    if out_xlsx.exists():
        try:
            xl_old = pd.ExcelFile(out_xlsx)
            if 'revisione_ml' in xl_old.sheet_names:
                vecchio_df = pd.read_excel(xl_old, sheet_name="revisione_ml")
                if 'categoria_corretta' in vecchio_df.columns:
                    val_corrette = vecchio_df.dropna(subset=['categoria_corretta'])
                    vecchie_correzioni = dict(zip(val_corrette['pdf_name'], val_corrette['categoria_corretta']))
            if 'anomalie_da_addestrare' in xl_old.sheet_names:
                vecchio_df_an = pd.read_excel(xl_old, sheet_name="anomalie_da_addestrare")
                if 'conferma_anomalia' in vecchio_df_an.columns:
                    val_anomalie = vecchio_df_an.dropna(subset=['conferma_anomalia'])
                    vecchie_anomalie = dict(zip(val_anomalie['pdf_name'], val_anomalie['conferma_anomalia']))
        except Exception as e:
            logger.warning(f"Impossibile leggere il vecchio Excel per il feedback: {e}")
    
    try:
        with pd.ExcelWriter(out_xlsx, engine="xlsxwriter") as xl:
            dfp.to_excel(xl, index=False, sheet_name="pdf_analisi")
            kpi_source.to_excel(xl, index=False, sheet_name="kpi_source")
            kpi_visto.to_excel(xl, index=False, sheet_name="kpi_visto_contabile")
            kpi_doctype.to_excel(xl, index=False, sheet_name="kpi_doctype")
            dff.to_excel(xl, index=False, sheet_name="features_ml")
            fornitori.head(50).to_excel(xl, index=False, sheet_name="fornitori_top50")
            # Aggiungiamo i due fogli mancanti e corretti
            df_atti.to_excel(xl, index=False, sheet_name="atti_estratti")
            df.to_excel(xl, index=False, sheet_name="metadati") # Usa df (non esploso) invece di dfa
            
            # Crea un foglio dedicato per revisionare comodamente le predizioni del modello ML
            ml_preds = dfp[dfp['classification_confidence'] == 'ml_predicted']
            if not ml_preds.empty:
                cols_review = [c for c in ["pdf_name", "doc_type", "category", "oggetto", "text_preview"] if c in dfp.columns]
                df_review = ml_preds[cols_review].copy()
                df_review.insert(3, 'categoria_corretta', df_review['pdf_name'].map(vecchie_correzioni)) # Ripristina il feedback umano
                df_review.to_excel(xl, index=False, sheet_name="revisione_ml")
                
            # Salva gli atti con anomalie per il feedback loop (Active Learning)
            anomalies_df = dfp[dfp['anomalie'].notna()]
            if not anomalies_df.empty:
                df_anomalies_review = anomalies_df[['pdf_name', 'importo_max', 'importo_lettere', 'piva_beneficiario', 'iban', 'anomalie', 'text_preview']].copy()
                df_anomalies_review.insert(6, 'conferma_anomalia', df_anomalies_review['pdf_name'].map(vecchie_anomalie)) # Ripristina il feedback
                df_anomalies_review.to_excel(xl, index=False, sheet_name="anomalie_da_addestrare")
        
        logger.info("Excel salvato con successo!")
    except Exception as e:
        logger.warning(f"Errore salvataggio Excel con xlsxwriter: {e}")
        logger.info("I dati CSV sono comunque disponibili!")

    logger.info(f"Salvati:\n- {out_csv_allegati}\n- {out_csv_atti}\n- {out_csv_features}\n- {out_corpus_jsonl if not args.no_corpus else '(corpus disattivato)'}\n- {out_xlsx} (se riuscito)")
    
    metrics.export_to_file(str((base / "metrics_analyze_albo.json").resolve()))

if __name__ == "__main__":
    main()
