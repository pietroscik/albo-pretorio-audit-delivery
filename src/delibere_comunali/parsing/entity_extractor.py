import re
import time
import json
from typing import Optional, Dict, Any, List

from ..patterns.albo_patterns import (
    RX_CIG, RX_CUP, RX_OGGETTO, RX_NUM_ATTO, RX_REG_GEN, RX_BENEF,
    RX_IMPEGNO, RX_ACCERT, RX_CAPITOLO, RX_PEG, RX_IBAN, RX_IMPORTO_LIQUIDATO,
    IMPORTI_REGEX
)
from ..rag.llm_factory import get_llm_client
from ..utils.logger import get_logger
from ..utils.config import get_config

logger = get_logger(__name__)

try:
    from word2number import w2n
except ImportError:
    logger.warning("word2number library not available - amounts in letters will not be processed")
    w2n = None

def normalizza_rup(testo_rup: str) -> str:
    """Normalizza il nome del responsabile unico del procedimento."""
    if not testo_rup:
        return ""
    
    # Rimuovi eventuali titoli e abbreviazioni
    testo = str(testo_rup).strip().lower()
    
    # Rimuovi titoli professionali
    testo = re.sub(r'\b(sig|sig.ra|dott|dott.ssa|avv|geom|arch)\.?\s*', '', testo)
    
    # Rimuovi parole comuni non rilevanti
    testo = re.sub(r'\b(responsabile|del|dell|della|ufficio|settore|area|tecnico|amministrativo)\b', '', testo)
    
    # Normalizza gli spazi
    testo = re.sub(r'\s+', ' ', testo).strip()
    
    # Capitalize ogni parola
    testo = ' '.join(word.capitalize() for word in testo.split())
    
    return testo

def lettere_to_numero(testo: str) -> Optional[float]:
    """Converte testo in lettere in numero usando word2number."""
    if w2n is None or not testo:
        return None
        
    testo = testo.strip().lower()
    # Handle cases like "euro quarantadue 32/100" -> "quarantadue 32/100"
    if testo.startswith("euro"):
        testo = testo[4:].strip()
        
    # Check if it contains fractional part (like "/100")
    frazione_match = re.search(r'(\d+)/(\d+)', testo)
    if frazione_match:
        parte_lettere = re.sub(r'\s*\d+/\d+', '', testo).strip()
        parte_decimali = frazione_match.group(1)
        try:
            numero = w2n.word_to_num(parte_lettere)
            decimali = float(parte_decimali) / 100
            return float(numero + decimali)
        except:
            pass
    try:
        return float(w2n.word_to_num(testo))
    except:
        # Last resort: look for number words and convert them
        words = testo.split()
        numbers = []
        for word in words:
            try:
                num = w2n.word_to_num(word)
                numbers.append(num)
            except:
                continue
        if numbers:
            return float(sum(numbers))
    return None

def normalize_amount(amount_str: str) -> Optional[float]:
    """Normalizes an amount string to a float value."""
    if not amount_str:
        return None
    
    # Clean the string
    cleaned = str(amount_str).strip().lower()
    if not cleaned:
        return None
        
    # Handle currency symbols and special characters
    cleaned = cleaned.replace('€', '').replace('$', '').replace('£', '').strip()
    
    # Check if it's already a number-like string
    try:
        # Handle different number formats
        if ',' in cleaned and '.' in cleaned:
            # Format like "1.234,56" (European)
            if cleaned.rindex(',') > cleaned.rindex('.'):
                # Replace dots with nothing and comma with dot
                cleaned = cleaned.replace('.', '').replace(',', '.')
            else:
                # Format like "1,234.56" (US)
                cleaned = cleaned.replace(',', '')
        elif ',' in cleaned:
            # Could be either "1234,56" or "1,234" - assume European format for amounts
            if len(cleaned.split(',')[-1]) == 2:  # Two digits after comma
                cleaned = cleaned.replace(',', '.')
            else:  # More likely a separator: "1,234"
                cleaned = cleaned.replace(',', '')
                
        return float(cleaned)
    except ValueError:
        # If it contains letters, try to convert from words
        return lettere_to_numero(cleaned)

class EntityExtractor:
    """
    Advanced entity extractor that combines multiple extraction techniques:
    1. LLM-based extraction for complex patterns
    2. Advanced extractor (custom logic) for specific entities
    3. Regex-based extraction for standard patterns
    """
    
    def __init__(self, config=None, advanced_extractor=None):
        self.config = config or get_config()  # Use get_config() as fallback
        
        # Check if config has llm attribute, otherwise create a default
        if not hasattr(self.config, 'llm'):
            # Create a simple object with default values
            class DefaultLlmConfig:
                model_priority = ["gemini-1.5-flash"]
                api_key = None
                mistral_api_key = None
            self.config.llm = DefaultLlmConfig()
        
        # Import llm client function but don't call it yet - we'll use it when needed
        try:
            from ..rag.llm_factory import get_llm_client
            self.get_llm_client_func = get_llm_client
        except ImportError:
            logger.warning("LLM factory not available")
            self.get_llm_client_func = None
        self.llm_client = None  # We'll initialize this when actually needed
        
        # Use provided advanced extractor or create a new one
        if advanced_extractor is not None:
            self.advanced_extractor = advanced_extractor
        else:
            # Import advanced extractor if available
            try:
                from .advanced_entity_extractor import AdvancedEntityExtractor
                self.advanced_extractor = AdvancedEntityExtractor(config)
            except ImportError:
                logger.warning("Advanced entity extractor not available")
                self.advanced_extractor = None

    def extract_entities(self, text: str, doc_type: str = None, **kwargs) -> Dict[str, Any]:
        """
        Extract entities using multiple approaches and merge results.
        Priority: LLM > Advanced Extractor > Regex
        """
        # 1. LLM-based extraction
        llm_results = self._extract_with_llm(text, doc_type)
        
        # 2. Advanced extractor (custom logic)
        adv_results = self._extract_with_advanced(text, doc_type)
        
        # 3. Regex-based extraction
        regex_results = self._extract_with_regex(text)
        
        # 4. Amount extraction
        amounts = self._extract_amounts(text, kwargs.get('subcategory'), kwargs.get('llm_amounts'))
        
        # 5. Merge all results with priority
        final_results = self._merge_results(llm_results, adv_results, regex_results)
        final_results.update(amounts)
        
        # 6. Post-processing and validation
        final_results = self._post_process(final_results, text)
        
        return final_results

    def _extract_with_llm(self, text: str, doc_type: str = None) -> Dict[str, Any]:
        """Extract entities using LLM."""
        if not self.get_llm_client_func or not self.config.llm.api_key:
            return {}
            
        try:
            # Define extraction schema based on document type
            schema = self._get_extraction_schema(doc_type)
            
            prompt = f"""
            Estrai le seguenti informazioni dal testo del documento:
            {schema}
            
            Testo del documento:
            {text[:4000]}  # Limit text length for LLM
            
            Rispondi in formato JSON con le sole informazioni richieste.
            """
            
            # Call the LLM client with the prompt
            response = self.get_llm_client_func(prompt)
            
            # Parse and validate response
            if isinstance(response, str):
                try:
                    data = json.loads(response)
                    return {k: v for k, v in data.items() if v is not None}
                except json.JSONDecodeError:
                    logger.warning("LLM response is not valid JSON")
                    return {}
            elif isinstance(response, dict):
                return {k: v for k, v in response.items() if v is not None}
            else:
                return {}
                
        except Exception as e:
            logger.error(f"Error in LLM entity extraction: {e}")
            return {}

    def _get_extraction_schema(self, doc_type: str = None) -> str:
        """Define extraction schema based on document type."""
        base_schema = """
        {
            "oggetto": "oggetto del documento",
            "cig": "codice CIG se presente",
            "cup": "codice CUP se presente", 
            "beneficiario": "nome del beneficiario",
            "responsabile": "nome del responsabile del procedimento",
            "importo": "importo espresso nel documento",
            "numero_atto": "numero dell'atto",
            "data_atto": "data dell'atto in formato YYYY-MM-DD"
        }
        """
        
        return base_schema

    def _extract_with_advanced(self, text: str, doc_type: str = None) -> Dict[str, Any]:
        """Extract entities using advanced custom logic."""
        if not self.advanced_extractor:
            return {}
        
        ocr_confidence = 0.85 if "ocr" in text[:10].lower() else 1.0 # Heuristic
        if hasattr(self.advanced_extractor, 'extract_entities_full'):
            return self.advanced_extractor.extract_entities_full(text, doc_type=doc_type, ocr_conf=ocr_confidence)
        return self.advanced_extractor.extract_entities(text, doc_type=doc_type)

    def _extract_with_regex(self, text: str) -> Dict[str, Any]:
        """Estrae entità usando espressioni regolari."""
        data = {}

        # Oggetto
        m_oggetto = RX_OGGETTO.search(text)
        if m_oggetto:
            data['oggetto'] = m_oggetto.group(1).strip()[:1500]

        # Numero e data atto
        m_num_atto = RX_NUM_ATTO.search(text)
        if m_num_atto:
            data['numero_atto'] = m_num_atto.group(1)
            data['data_atto'] = m_num_atto.group(2)

        # Registro Generale
        m_reg_gen = RX_REG_GEN.search(text)
        if m_reg_gen:
            data['numero_registro'] = m_reg_gen.group(1)
            data['data_registro'] = m_reg_gen.group(2)

        # CIG e CUP
        m_cig = RX_CIG.search(text)
        if m_cig: data['cig'] = m_cig.group(1).upper()
        m_cup = RX_CUP.search(text)
        if m_cup: data['cup'] = m_cup.group(1).upper()

        # Beneficiario
        for rx in RX_BENEF:
            m_benef = rx.search(text)
            if m_benef:
                benef_text = m_benef.group(1).strip(" :;-|")
                benef_text = re.sub(r'\s*-\s*Progressivo Fornitore.*', '', benef_text, flags=re.IGNORECASE)
                if len(benef_text) < 150:
                    data['beneficiario'] = benef_text.strip()
                    break
        
        # IBAN
        m_iban = RX_IBAN.search(text)
        if m_iban:
            data['iban'] = re.sub(r'\s+', '', m_iban.group(0)).upper()

        # Dati contabili
        m_impegno = RX_IMPEGNO.search(text)
        if m_impegno: data['impegno_num'] = m_impegno.group(1)
        m_accert = RX_ACCERT.search(text)
        if m_accert: data['accert_num'] = m_accert.group(1)
        m_capitolo = RX_CAPITOLO.search(text)
        if m_capitolo:
            cap_val = m_capitolo.group(1)
            if not (len(cap_val) == 5 and cap_val.isdigit()):
                data['capitolo'] = cap_val
        
        return data

    def _extract_amounts(self, text: str, subcategory: Optional[str] = None, llm_amounts: Optional[List[str]] = None) -> Dict[str, Any]:
        """Estrae e calcola gli importi da un testo."""
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
        is_liquidazione = subcategory == "Liquidazione" or "s.a.l." in text.lower() or "sal n." in text.lower()
        if is_liquidazione:
            m_liq = RX_IMPORTO_LIQUIDATO.search(text)
            if m_liq:
                importo_specifico_liquidazione = normalize_amount(m_liq.group(1))
                if importo_specifico_liquidazione and importo_specifico_liquidazione > 0:
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
        
        for pattern in IMPORTI_REGEX[:8]:
            # Le regex sono già compilate, quindi non passiamo flag aggiuntivi
            matches = re.findall(pattern, text)
            for match in matches:
                importo_clean = re.sub(r"[^\d,]", "", str(match))
                if importo_clean:
                    val = normalize_amount(importo_clean)
                    if val and 0 < val < 100_000_000:
                        importi.add(val)
                    
        for pattern in IMPORTI_REGEX[8:]:
            # Le regex sono già compilate, quindi non passiamo flag aggiuntivi
            matches = re.findall(pattern, text)
            for match in matches:
                numero = lettere_to_numero(match[0] if isinstance(match, tuple) else match)
                if numero: importi.add(numero)
                
        return sorted(importi, reverse=True)

    def _merge_results(self, llm: Dict, adv: Dict, regex: Dict) -> Dict[str, Any]:
        """
        Unisce i risultati delle estrazioni dando priorità a LLM, poi Advanced, poi Regex.
        """
        merged = regex.copy()

        # Priorità all'estrattore avanzato su regex
        merged['cig'] = adv.get('cig_estratto') or merged.get('cig')
        merged['cup'] = adv.get('cup_estratto') or merged.get('cup')
        merged['beneficiario'] = adv.get('beneficiario') or merged.get('beneficiario')
        merged['responsabile'] = adv.get('responsabile') or merged.get('responsabile')
        merged['impegno_num'] = adv.get('impegno_num') or merged.get('impegno_num')
        merged['iban'] = adv.get('iban_estratto') or merged.get('iban')
        
        cap_adv = adv.get("capitolo")
        if cap_adv and not (len(str(cap_adv)) == 5 and str(cap_adv).isdigit()):
            merged['capitolo'] = cap_adv

        # Priorità a LLM su tutto
        merged['oggetto'] = llm.get('oggetto') or merged.get('oggetto')
        merged['cig'] = llm.get('cig') or merged.get('cig')
        merged['cup'] = llm.get('cup') or merged.get('cup')
        merged['beneficiario'] = llm.get('beneficiario') or merged.get('beneficiario')
        
        # Aggiunge dati solo presenti in adv (che non sono già stati gestiti con priorità)
        for key, value in adv.items():
            if key not in merged or merged[key] is None:
                merged[key] = value

        return merged

    def _post_process(self, results: Dict[str, Any], original_text: str) -> Dict[str, Any]:
        """Apply post-processing rules to extracted entities."""
        processed = results.copy()
        
        # Clean up text fields
        for key, value in processed.items():
            if isinstance(value, str):
                processed[key] = value.strip()
                
        # Validate dates
        for date_key in ['data_atto', 'data_registro']:
            if date_key in processed and processed[date_key]:
                date_val = str(processed[date_key])
                # Ensure date is in proper format
                if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_val):
                    # Try to convert various formats
                    import datetime
                    for fmt in ['%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y']:
                        try:
                            parsed_date = datetime.datetime.strptime(date_val, fmt)
                            processed[date_key] = parsed_date.strftime('%Y-%m-%d')
                            break
                        except ValueError:
                            continue
        
        return processed

    def extract_all(self, text: str, doc_type: str = None, subcategory: str = None, use_llm: bool = True, **kwargs):
        """
        Alias for extract_entities to maintain compatibility with existing code.
        """
        # Pass subcategory and use_llm as part of kwargs for the extraction process
        kwargs['subcategory'] = subcategory
        kwargs['use_llm'] = use_llm
        if 'pdf_path' in kwargs:
            # May need to handle pdf_path differently depending on implementation
            pass
        return self.extract_entities(text, doc_type=doc_type, **kwargs)