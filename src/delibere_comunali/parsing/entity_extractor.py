import re
from functools import lru_cache
from typing import Any, Dict, Optional

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
            except Exception:
                pass
    try:
        return float(w2n.word_to_num(testo))
    except Exception:
        pass
    return None


@lru_cache(maxsize=1024)
def normalize_amount(txt: Optional[str]) -> Optional[float]:
    """Converte stringhe tipo '\u20ac 1.234,56' o '12.345,67 euro' in float 12345.67.

    Gestisce formati:
    - \u20ac 1.234,56 (formato europeo con separatore migliaia)
    - 12.345,67 euro
    - importo di spesa: 500,00
    - 1.000 (migliaia con punto)
    - 500.00 (decimale con punto)
    """
    if not txt:
        return None

    # Convert to string and strip whitespace
    s = str(txt).strip()
    s = re.sub(r"[\u20ac\$\u00a3]", "", s)  # Rimuovi simboli monetari
    s = re.sub(r"[a-zA-Z]+\s*", "", s)  # Rimuovi testo (euro, EUR, ecc.)
    s = re.sub(r"[:=]", "", s)  # Rimuovi separatori
    s = s.replace(" ", "")  # Rimuovi spazi

    if not s:
        return None

    # Gestione separatori - migliorata per distinguere tra separatore migliaia e decimale
    if "." in s and "," in s:
        # Formato europeo: 1.234,56 (punto = migliaia, virgola = decimale)
        # Formato americano: 1,234.56 (virgola = migliaia, punto = decimale)
        # Dobbiamo distinguere quale \u00e8 quale
        # Se la parte dopo la virgola ha 2-3 cifre, probabilmente \u00e8 il decimale
        parts = s.split(",")
        if len(parts) > 1 and len(parts[-1]) <= 3 and parts[-1].isdigit():
            # Probabilmente formato europeo
            s = s.replace(".", "").replace(",", ".")
        else:
            # Probabilmente formato americano
            s = s.replace(",", "")
    elif "," in s:
        # Formato con solo virgola: 1234,56 o 1.234,56 senza punto
        # Se la parte dopo la virgola ha 2-3 cifre, \u00e8 il decimale
        parts = s.split(",")
        if len(parts) > 1 and len(parts[-1]) <= 3 and parts[-1].isdigit():
            s = s.replace(",", ".")
        else:
            # Altrimenti trattare come separatore di migliaia
            s = s.replace(",", "")
    elif "." in s:
        # Formato con solo punto: potrebbe essere 1234.56 (decimale) o 1.000 (migliaia)
        # Controlla se il punto \u00e8 un separatore delle migliaia (es. 1.000.000 o 1.000)
        # Se ci sono pi\u00f9 punti OPPURE il punto \u00e8 seguito da esattamente 3 cifre e poi la fine
        point_parts = s.split(".")
        if len(point_parts) > 2:
            # Pi\u00f9 punti -> separatore delle migliaia
            s = s.replace(".", "")
        elif len(point_parts) == 2:
            # Controlla se \u00e8 un separatore di migliaia (es. 1.000)
            # Se la parte dopo il punto ha esattamente 3 cifre e quella prima \u00e8 un numero valido
            if (
                len(point_parts[1]) == 3
                and point_parts[1].isdigit()
                and point_parts[0].isdigit()
            ):
                # Probabilmente \u00e8 un separatore di migliaia (es. 1.000)
                s = s.replace(".", "")
            # altrimenti \u00e8 gi\u00e0 un decimale
        else:
            # Altrimenti trattare come separatore di migliaia
            s = s.replace(".", "")

    try:
        return float(s)
    except (ValueError, TypeError):
        # Tentativo alternativo: prova a cercare un valore numerico con due cifre decimali
        # all'interno della stringa originale
        numeric_match = re.search(r"(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2}))", str(txt))
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


def normalizza_beneficiario(beneficiario: str) -> str:
    """Normalizza il nome del beneficiario rimuovendo caratteri speciali e spazi multipli."""
    if not beneficiario:
        return ""
    # Rimuovi caratteri speciali tranne lettere, numeri, spazi, punti, virgole, e apici
    beneficiario = re.sub(r"[^\w\s\.\,\-\'\"&/]", "", beneficiario)
    # Sostituisci spazi multipli con uno solo
    beneficiario = re.sub(r"\s+", " ", beneficiario).strip()
    return beneficiario


class EntityExtractor:
    """Classe per l'estrazione di entit\u00e0 da documenti dell'Albo Pretorio.

    Utilizza espressioni regolari per identificare e estrarre:
    - Oggetto
    - Numero atto e data
    - CIG e CUP
    - Beneficiario
    - IBAN
    - Impegno, Capitolo, Accertamento
    - Importi
    """

    def __init__(self):
        """Inizializza l'estrattore con i pattern precompilati."""
        self.patterns = {
            "cig": RX_CIG,
            "cup": RX_CUP,
            "iban": RX_IBAN,
            "impegno": RX_IMPEGNO,
            "accertamento": RX_ACCERT,
            "capitolo": RX_CAPITOLO,
            "peg": RX_PEG,
            "numero_atto": RX_NUM_ATTO,
            "registro_generale": RX_REG_GEN,
            "beneficiario": RX_BENEF,
            "importo_liquidato": RX_IMPORTO_LIQUIDATO,
        }
        self.llm_client = None

    def _extract_with_regex(self, text: str) -> Dict[str, Any]:
        """Estrae entit\u00e0 dal testo usando espressioni regolari.

        Args:
            text: Testo da analizzare

        Returns:
            Dizionario con le entit\u00e0 estratte
        """
        entities = {}

        # Estrai oggetto - pattern personalizzato per gestire multiline
        # Cerca "OGGETTO:" e cattura tutto fino a "Numero Atto" o fine riga
        oggetto_pattern = re.compile(
            r"OGGETTO:\s*(.+?)(?=\s*(?:Numero\s+Atto|N\.\s*\d|$))",
            re.IGNORECASE | re.DOTALL,
        )
        oggetto_match = oggetto_pattern.search(text)
        if oggetto_match:
            entities["oggetto"] = oggetto_match.group(1).strip()

        # Estrai numero atto e data
        num_atto_match = self.patterns["numero_atto"].search(text)
        if num_atto_match:
            entities["numero_atto"] = num_atto_match.group(1).strip()
            entities["data_atto"] = num_atto_match.group(2).strip()

        # Estrai CIG
        cig_match = self.patterns["cig"].search(text)
        if cig_match:
            entities["cig"] = cig_match.group(1).strip()

        # Estrai CUP
        cup_match = self.patterns["cup"].search(text)
        if cup_match:
            entities["cup"] = cup_match.group(1).strip()

        # Estrai IBAN
        iban_match = self.patterns["iban"].search(text)
        if iban_match:
            entities["iban"] = iban_match.group(0).strip().replace(" ", "")

        # Estrai impegno
        impegno_match = self.patterns["impegno"].search(text)
        if impegno_match:
            entities["impegno_num"] = impegno_match.group(1).strip()

        # Estrai capitolo
        capitolo_match = self.patterns["capitolo"].search(text)
        if capitolo_match:
            entities["capitolo"] = capitolo_match.group(1).strip()

        # Estrai beneficiario (usa il primo pattern che matcha)
        for pattern in self.patterns["beneficiario"]:
            benef_match = pattern.search(text)
            if benef_match:
                entities["beneficiario"] = benef_match.group(1).strip()
                break

        # Estrai registro generale
        reg_gen_match = self.patterns["registro_generale"].search(text)
        if reg_gen_match:
            entities["registro_generale_num"] = reg_gen_match.group(1).strip()
            entities["registro_generale_data"] = reg_gen_match.group(2).strip()

        return entities

    def extract_all(self, text: str) -> Dict[str, Any]:
        """Estrae tutte le entit\u00e0 dal testo e normalizza i valori.

        Args:
            text: Testo da analizzare

        Returns:
            Dizionario con tutte le entit\u00e0 estratte e normalizzate
        """
        entities = self._extract_with_regex(text)

        # Normalizza beneficiario
        if "beneficiario" in entities:
            entities["beneficiario"] = normalizza_beneficiario(entities["beneficiario"])

        # Estrai e normalizza importi
        importi = []
        for pattern in IMPORTI_REGEX:
            matches = pattern.finditer(text)
            for match in matches:
                importo_str = match.group(0)
                # Estrai solo la parte numerica
                numeric_match = re.search(r"[\d.,]+", importo_str)
                if numeric_match:
                    importo_normalizzato = normalize_amount(numeric_match.group(0))
                    if importo_normalizzato:
                        importi.append(importo_normalizzato)

        if importi:
            entities["importi"] = importi
            entities["importo_totale"] = sum(importi)

        return entities

    def extract_with_llm(
        self, text: str, prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Estrae entit\u00e0 usando LLM (opzionale, richiede configurazione API).

        Args:
            text: Testo da analizzare
            prompt: Prompt personalizzato per l'estrazione

        Returns:
            Dizionario con le entit\u00e0 estratte dall'LLM
        """
        if self.llm_client is None:
            self.llm_client = get_llm_client()

        if self.llm_client is None:
            logger.warning(
                "Nessun client LLM configurato. Usa solo l'estrazione con regex."
            )
            return self.extract_all(text)

        # TODO: Implementare estrazione con LLM
        return self.extract_all(text)
