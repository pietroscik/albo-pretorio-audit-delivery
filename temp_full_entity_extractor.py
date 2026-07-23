import json
import re
import time
from functools import lru_cache
from typing import Any, Dict, List, Optional

from ..patterns.albo_patterns import (
    IMPORTI_REGEX,
    RX_ACCERT,
    RX_BENEF,
    RX_CAPITOLO,
    RX_CIG,
    RX_CUP,
    RX_IBAN,
    RX_IMPEGNO,
    RX_IMPORTO_LIQUIDATO,
    RX_NUM_ATTO,
    RX_OGGETTO,
    RX_PEG,
    RX_REG_GEN,
)
from ..rag.llm_factory import get_llm_client
from ..utils.logger import get_logger

logger = get_logger("entity_extractor")

try:
    from word2number import w2n
except ImportError:
    w2n = None


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


@lru_cache(maxsize=1024)
def normalize_amount(txt: Optional[str]) -> Optional[float]:
    """Converte stringhe tipo '€ 1.234,56' o '12.345,67 euro' in float 12345.67.

    Gestisce formati:
    - € 1.234,56 (formato europeo con separatore migliaia)
    - 12.345,67 euro
    - importo di spesa: 500,00
    - 1.000 (migliaia con punto)
    - 500.00 (decimale con punto)
    """
    if not txt:
        return None

    # Convert to string and strip whitespace
    s = str(txt).strip()
    s = re.sub(r"[€\$£]", "", s)  # Rimuovi simboli monetari
    s = re.sub(r"[a-zA-Z]+", "", s)  # Rimuovi testo (euro, EUR, ecc.)
    s = re.sub(r"[:=]", "", s)  # Rimuovi separatori
    s = s.replace(" ", "")  # Rimuovi spazi

    if not s:
        return None

    # Gestione separatori - migliorata per distinguere tra separatore migliaia e decimale
    if "." in s and "," in s:
        # Formato europeo: 1.234,56 (punto = migliaia, virgola = decimale)
        # Formato americano: 1,234.56 (virgola = migliaia, punto = decimale)
        # Dobbiamo distinguere quale è quale
        # Se la parte dopo la virgola ha 2-3 cifre, probabilmente è il decimale
        parts = s.split(',')
        if len(parts) > 1 and len(parts[-1]) <= 3 and parts[-1].isdigit():
            # Probabilmente formato europeo
            s = s.replace(".", "").replace(",", ".")
        else:
            # Probabilmente formato americano
            s = s.replace(",", "")
    elif "," in s:
        # Formato con solo virgola: 1234,56 o 1.234,56 senza punto
        # Se la parte dopo la virgola ha 2-3 cifre, è il decimale
        parts = s.split(',')
        if len(parts) > 1 and len(parts[-1]) <= 3 and parts[-1].isdigit():
            s = s.replace(",", ".")
        else:
            # Altrimenti trattare come separatore di migliaia
            s = s.replace(",", "")
    elif "." in s:
        # Formato con solo punto: potrebbe essere 1234.56 (decimale) o 1.000 (migliaia)
        # Controlla se il punto è un separatore delle migliaia (es. 1.000.000 o 1.000)
        # Se ci sono più punti OPPURE il punto è seguito da esattamente 3 cifre e poi la fine
        point_parts = s.split(".")
        if len(point_parts) > 2:
            # Più punti -> separatore delle migliaia
            s = s.replace(".", "")
        elif len(point_parts) == 2 and len(point_parts[1]) <= 3 and point_parts[1].isdigit():
            # La parte dopo il punto ha 1-3 cifre, probabilmente è il decimale
            pass  # Lascia così, è già in formato corretto
        else:
            # Altrimenti trattare come separatore di migliaia
            s = s.replace(".", "")

    try:
        return float(s)
    except (ValueError, TypeError):
        # Tentativo alternativo: prova a cercare un valore numerico con due cifre decimali
        # all'interno della stringa originale
        numeric_match = re.search(r'(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2}))', str(txt))
        if numeric_match:
            numeric_str = numeric_match.group(1)
            # Converti in formato standard
            numeric_str = numeric_str.replace(".", "").replace(",", ".")
            try:
                return float(numeric_str)
            except (ValueError, TypeError):
                pass
        
        # Ultimo tentativo: cerca pattern specifici comuni in documenti amministrativi
        admin_patterns = [
            r"(?i)importo.*?di.*?(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2}))",
            r"(?i)per.*?un.*?importo.*?di.*?(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2}))",
            r"(?i)ammontare.*?a.*?(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2}))",
        ]
        for pattern in admin_patterns:
            match = re.search(pattern, str(txt))
            if match:
                numeric_str = match.group(1)
                numeric_str = numeric_str.replace(".", "").replace(",", ".")
                try:
                    return float(numeric_str)
                except (ValueError, TypeError):
                    continue
        return None