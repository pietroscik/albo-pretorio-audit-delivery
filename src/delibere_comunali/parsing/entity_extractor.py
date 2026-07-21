import json
import re
import time
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

    # Rimuovi simboli monetari e spazi
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


def normalizza_beneficiario(nome: str) -> str:
    if not isinstance(nome, str) or not nome.strip():
        return "NON IDENTIFICATO"

    nome = nome.upper().strip()

    # 1. Filtro falsi positivi burocratici aggiornato
    falsi_positivi = [
        "MAGGIORMENTE QUALIFICAT",
        "CHE HA PRESENTATO",
        "IN REGOLA",
        "DIVERSI BENEFICIARI",
        "DIVERSE DITTE",
        "OPERATORE ECONOMICO",
        "APPALTATRICE",
        "AGGIUDICATARI",
        "DIVERSI",
    ]
    for fp in falsi_positivi:
        if fp in nome:
            return "DIVERSI/NON APPLICABILE"

    # 2. Rimozione di titoli e forme giuridiche per accorpare i nomi
    stopwords = [
        r"\bPROFESSIONISTA\b",
        r"\bDITTA\b",
        r"\bIMPRESA\b",
        r"\bSOCIET[AÀ]\b",
        r"\bS\.?R\.?L\.?S?\b",
        r"\bS\.?P\.?A\.?\b",
        r"\bS\.?N\.?C\.?\b",
        r"\bS\.?A\.?S\.?\b",
        r"\bAVV\.?\b",
        r"\bING\.?\b",
        r"\bARCH\.?\b",
        r"\bDOTT\.?(SSA)?\b",
        r"\bGEOM\.?\b",
    ]
    for sw in stopwords:
        nome = re.sub(sw, "", nome, flags=re.IGNORECASE)

    # 3. Pulizia finale da spazi multipli e punteggiatura
    nome = re.sub(r"[^\w\s]", " ", nome)  # Rimuove punteggiatura
    nome = re.sub(r"\s+", " ", nome).strip()

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
        "VISTO",
        "VISTA",
        "VISTI",
        "PREMESSO",
        "ACCERTATA",
        "SULLA BASE",
        "DECRETO",
        "FUNZIONI",
        "AI SENSI",
        "LA GIUNTA",
        "DI ADOTTARE",
        "IL CONSIGLIO",
        "HA ADOTTATO",
        "DELIBERAZIONE",
        "DETERMINAZIONE",
        "COMPETENZA",
        "MUNICIPIO",
        "URBANISTICO",
        "REGOLAMENTO",
        "PROMOZIONE",
        "FINANZIARIA",
        "NAZIONALE",
        "RIPRESA",
        "CENSIMENTO",
        "DIPENDENTE",
        "CONCESSO",
        "CHE CON",
        "PRO TEMPORE",
    ]
    if any(escl in testo_rup for escl in esclusioni):
        return "NON IDENTIFICATO"

    # Pulizia generica per nomi non mappati
    stopwords = [
        r"\bDOTT\.SSA\b",
        r"\bDOTT\.?\b",
        r"\bDR\.?\b",
        r"\bSSA\b",
        r"\bIL RESPONSABILE\b",
        r"\bDEL SERVIZIO\b",
        r"\bF\.TO\b",
        r"\bIL SEGRETARIO\b",
        r"\bIL SINDACO\b",
        r"\bGEOM\.?\b",
        r"\bARCH\.?\b",
        r"\bING\.?\b",
        r"\bAVV\.?\b",
    ]
    for sw in stopwords:
        testo_rup = re.sub(sw, "", testo_rup, flags=re.IGNORECASE)

    testo_pulito = re.sub(r"[^\w\s]", " ", testo_rup)  # Rimuove punteggiatura
    testo_pulito = re.sub(r"\s+", " ", testo_pulito).strip()

    return testo_pulito if testo_pulito else "NON IDENTIFICATO"


class EntityExtractor:
    """
    Classe responsabile dell'estrazione di entità strutturate dal testo di un documento.
    Orchestra l'estrazione da Regex, modelli LLM e altri estrattori avanzati.
    """

    def __init__(self, advanced_extractor: Optional[Any] = None):
        self.advanced_extractor = advanced_extractor

    def extract_all(
        self,
        text: str,
        doc_type: str,
        subcategory: Optional[str] = None,
        use_llm: bool = False,
    ) -> Dict[str, Any]:
        """
        Estrae tutte le entità da un testo, orchestrando diverse fonti.
        """
        # 1. Estrazione con LLM (se abilitata)
        llm_data = self._extract_with_llm(text) if use_llm else {}

        # 2. Estrazione con Regex (come fallback o per arricchimento)
        regex_data = self._extract_with_regex(text)

        # 3. Estrazione con Advanced Extractor (se presente)
        adv_data = self._extract_with_advanced(text, doc_type)

        # 4. Estrazione importi
        amount_data = self._extract_amounts(
            text, doc_type, subcategory, llm_data.get("importi_raw")
        )

        # 5. Unione e prioritizzazione dei risultati
        merged = self._merge_results(llm_data, adv_data, regex_data)
        merged.update(amount_data)

        # Logica di override per importo_max
        if adv_data.get("importo_max_estratto"):
            # L'estrattore avanzato ha priorità, a meno che non sia una liquidazione
            # dove l'importo specifico ha la precedenza assoluta.
            is_liquidazione = (
                subcategory == "Liquidazione"
                or "s.a.l." in text.lower()
                or "sal n." in text.lower()
            )
            if not is_liquidazione or not merged.get("importo_max"):
                merged["importo_max"] = adv_data["importo_max_estratto"]

        # Normalizzazione finale
        if "beneficiario" in merged and merged["beneficiario"]:
            merged["beneficiario"] = normalizza_beneficiario(merged["beneficiario"])
        if "responsabile" in merged and merged["responsabile"]:
            merged["responsabile"] = normalizza_rup(merged["responsabile"])

        return merged

    def _extract_with_llm(self, text: str) -> Dict[str, Any]:
        """Usa l'LLM (Gemini o Mistral) per l'estrazione dei metadati."""
        time.sleep(4.5)  # Throttle per rispettare i limiti API
        prompt = (
            """
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
        """
            + text[:15000]
        )

        result = get_llm_client(prompt)
        if not result:
            return {}

        # Sanitizzazione output
        for key in ["cig", "cup", "beneficiario", "responsabile", "oggetto"]:
            if key in result and isinstance(result[key], list):
                result[key] = (
                    " ".join([str(x) for x in result[key] if x])
                    if result[key]
                    else None
                )
            if key in result and result[key] == "null":
                result[key] = None

        return result

    def _extract_with_advanced(self, text: str, doc_type: str) -> Dict[str, Any]:
        if not self.advanced_extractor:
            return {}

        ocr_confidence = 0.85 if "ocr" in text[:10].lower() else 1.0  # Heuristic
        if hasattr(self.advanced_extractor, "extract_entities_full"):
            return self.advanced_extractor.extract_entities_full(
                text, doc_type=doc_type, ocr_conf=ocr_confidence
            )
        return self.advanced_extractor.extract_entities(text, doc_type=doc_type)

    def _extract_with_regex(self, text: str) -> Dict[str, Any]:
        """Estrae entità usando espressioni regolari."""
        data = {}

        # Oggetto
        m_oggetto = RX_OGGETTO.search(text)
        if m_oggetto:
            data["oggetto"] = m_oggetto.group(1).strip()[:1500]
        else:
            # Fallback per OGGETTO se il pattern principale non matcha
            m_oggetto_fallback = re.compile(
                r"OGGETTO:\s*(.+?\.)", re.IGNORECASE
            ).search(text)
            if m_oggetto_fallback:
                data["oggetto"] = m_oggetto_fallback.group(1).strip()[:1500]

        # Numero e data atto
        m_num_atto = RX_NUM_ATTO.search(text)
        if m_num_atto:
            data["numero_atto"] = m_num_atto.group(1)
            data["data_atto"] = m_num_atto.group(2)

        # Registro Generale
        m_reg_gen = RX_REG_GEN.search(text)
        if m_reg_gen:
            data["numero_registro"] = m_reg_gen.group(1)
            data["data_registro"] = m_reg_gen.group(2)

        # CIG e CUP
        m_cig = RX_CIG.search(text)
        if m_cig:
            data["cig"] = m_cig.group(1).upper()
        m_cup = RX_CUP.search(text)
        if m_cup:
            data["cup"] = m_cup.group(1).upper()

        # Beneficiario
        for rx in RX_BENEF:
            m_benef = rx.search(text)
            if m_benef:
                benef_text = m_benef.group(1).strip(" :;-|")
                benef_text = re.sub(
                    r"\s*-\s*Progressivo Fornitore.*",
                    "",
                    benef_text,
                    flags=re.IGNORECASE,
                )
                if len(benef_text) < 150:
                    data["beneficiario"] = benef_text.strip()
                    break

        # IBAN
        m_iban = RX_IBAN.search(text)
        if m_iban:
            data["iban"] = re.sub(r"\s+", "", m_iban.group(0)).upper()

        # Dati contabili
        m_impegno = RX_IMPEGNO.search(text)
        if m_impegno:
            data["impegno_num"] = m_impegno.group(1)
        m_accert = RX_ACCERT.search(text)
        if m_accert:
            data["accert_num"] = m_accert.group(1)
        m_capitolo = RX_CAPITOLO.search(text)
        if m_capitolo:
            cap_val = m_capitolo.group(1)
            if not (len(cap_val) == 5 and cap_val.isdigit()):
                data["capitolo"] = cap_val

        return data

    def _extract_amounts(
        self,
        text: str,
        doc_type: str,
        subcategory: Optional[str] = None,
        llm_amounts: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Estrae e calcola gli importi da un testo."""
        
        # Determina se il documento dovrebbe avere importi
        should_extract = should_extract_amounts(text, doc_type, subcategory)
        
        if not should_extract:
            # Se il documento non dovrebbe avere importi, ritorna valori nulli
            return {
                "importi_raw": [],
                "importo_max": None,
                "importo_sum": None,
                "importi_count": 0,
            }
        
        amts_norm = []
        if llm_amounts:
            for amount_raw in llm_amounts:
                normalized = normalize_amount(amount_raw)
                if normalized is not None:
                    amts_norm.append(normalized)
        else:
            amts_norm = self._extract_importi_raw(text)

        importo_max = None

        # Gestione S.A.L. e Liquidazioni: l'importo specifico ha la priorità
        is_liquidazione = (
            subcategory == "Liquidazione"
            or "s.a.l." in text.lower()
            or "sal n." in text.lower()
        )
        if is_liquidazione:
            m_liq = RX_IMPORTO_LIQUIDATO.search(text)
            if m_liq:
                importo_specifico_liquidazione = normalize_amount(m_liq.group(1))
                if (
                    importo_specifico_liquidazione
                    and importo_specifico_liquidazione > 0
                ):
                    importo_max = importo_specifico_liquidazione

        if importo_max is None:
            importo_max = max(amts_norm) if amts_norm else None

        return {
            "importi_raw": [str(a) for a in amts_norm],
            "importo_max": importo_max,
            "importo_sum": sum(amts_norm) if amts_norm else None,
            "importi_count": len(amts_norm),
        }

    def _extract_importi_raw(self, text: str) -> List[float]:
        """Estrae tutti gli importi (numerici e in lettere) da un testo."""
        importi = set()
        
        # Usare i pattern definiti in albo_patterns
        from ..patterns.albo_patterns import IMPORTI_REGEX
        
        # Applica i primi 9 pattern (più specifici) a tutti i documenti
        for pattern in IMPORTI_REGEX[:9]:  # Pattern per importi numerici specifici
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Estrarre solo il valore numerico dal match
                importo_clean = re.sub(r"[^\d,.\-\s]", "", str(match)).strip()
                if importo_clean:
                    val = normalize_amount(importo_clean)
                    if val and 0 < val < 100_000_000:  # Filtro per valori ragionevoli
                        # Filtro aggiuntivo: verificare che non sia un codice CIG/CUP
                        # Un codice CIG ha 10 caratteri alfanumerici, un CUP ne ha 15
                        # Se il valore è un numero intero di 10 o 15 cifre, probabilmente non è un importo
                        str_val = str(int(val)) if val.is_integer() else str(val)
                        clean_digits = str_val.replace('.', '').replace(',', '')
                        if not (len(clean_digits) == 10 or len(clean_digits) == 15):
                            # Ulteriore controllo contestuale: verificare che non sia vicino a parole chiave CIG/CUP
                            match_str = str(match)
                            text_lower = text.lower()
                            
                            # Trova la posizione del match nel testo
                            pos = text_lower.find(match_str.lower())
                            if pos != -1:
                                # Controlla un contesto di circa 50 caratteri prima e dopo il match
                                start = max(0, pos - 50)
                                end = min(len(text), pos + len(match_str) + 50)
                                context = text[start:end].lower()
                                
                                # Se il contesto contiene CIG o CUP, è probabile che non sia un importo
                                if 'cig' not in context and 'cup' not in context:
                                    importi.add(val)
                        
        for pattern in IMPORTI_REGEX[9:]:  # Pattern per importi in lettere
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                testo_importo = match[0] if isinstance(match, tuple) else match
                numero = lettere_to_numero(testo_importo)
                if numero and 0 < numero < 100_000_000: 
                    # Controllo simile per importi in lettere
                    str_numero = str(int(numero)) if numero.is_integer() else str(numero)
                    clean_digits = str_numero.replace('.', '').replace(',', '')
                    if not (len(clean_digits) == 10 or len(clean_digits) == 15):
                        importi.add(numero)
                    
        return sorted(list(importi), reverse=True)

    def _merge_results(self, llm: Dict, adv: Dict, regex: Dict) -> Dict[str, Any]:
        """
        Unisce i risultati delle estrazioni dando priorità a LLM, poi Advanced, poi Regex.
        """
        merged = regex.copy()

        # Priorità all'estrattore avanzato su regex
        merged["cig"] = adv.get("cig_estratto") or merged.get("cig")
        merged["cup"] = adv.get("cup_estratto") or merged.get("cup")
        merged["beneficiario"] = adv.get("beneficiario") or merged.get("beneficiario")
        merged["responsabile"] = adv.get("responsabile") or merged.get("responsabile")
        merged["impegno_num"] = adv.get("impegno_num") or merged.get("impegno_num")
        merged["iban"] = adv.get("iban_estratto") or merged.get("iban")

        cap_adv = adv.get("capitolo")
        if cap_adv and not (len(str(cap_adv)) == 5 and str(cap_adv).isdigit()):
            merged["capitolo"] = cap_adv

        # Priorità a LLM su tutto
        merged["oggetto"] = llm.get("oggetto") or merged.get("oggetto")
        merged["cig"] = llm.get("cig") or merged.get("cig")
        merged["cup"] = llm.get("cup") or merged.get("cup")
        merged["beneficiario"] = llm.get("beneficiario") or merged.get("beneficiario")

        # Aggiunge dati solo presenti in adv (che non sono già stati gestiti con priorità)
        for key, value in adv.items():
            if key not in merged or merged[key] is None:
                merged[key] = value

        return merged


def is_financial_document(text: str, doc_type: str, subcategory: str = None) -> bool:
    """
    Determines if a document is likely to contain financial amounts based on its type and content.
    """
    # Check document type
    financial_types = ['determinazione', 'delibera', 'atto', 'vistocontabile', 'impegno', 'liquidazione']
    if doc_type.lower() in financial_types:
        return True
    
    if subcategory and subcategory.lower() in ['contabilità', 'finanziario', 'impegno', 'liquidazione']:
        return True
    
    # Check content for financial keywords
    text_lower = text.lower()
    financial_keywords = [
        'importo', 'spesa', 'impegno', 'liquidazione', 'conto', 'bilancio', 'euro', '€',
        'costo', 'ricavo', 'provento', 'onorario', 'compens', 'tariff', 'canon', 'IVA',
        'oneri', 'accertamento', 'competenza', 'previsione', 'preventivo', 'consuntivo'
    ]
    
    financial_indicators = sum(1 for keyword in financial_keywords if keyword in text_lower)
    
    # If we have at least 2 financial indicators, it's likely a financial document
    return financial_indicators >= 2


def should_extract_amounts(text: str, doc_type: str, subcategory: str = None) -> bool:
    """
    Determines if amounts should be extracted from a document based on type and content.
    """
    # Check if document type suggests it should have amounts
    has_financial_type = is_financial_document(text, doc_type, subcategory)
    
    # Check for explicit non-financial document types
    non_financial_types = ['pubblicazione', 'avviso', 'notifica', 'atto_non_finanziario']
    if doc_type.lower() in non_financial_types:
        return False
    
    # Check for publication documents that typically don't have amounts
    text_lower = text.lower()
    if 'pubblicazione' in text_lower or 'rende noto' in text_lower or 'notifica' in text_lower:
        return False
    
    # If it's a financial document type or has financial content, extract amounts
    return has_financial_type
