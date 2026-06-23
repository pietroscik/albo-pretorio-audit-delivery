import re
import json
import logging
import pandas as pd
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

logger = logging.getLogger("RegTechExtractor")

@dataclass
class LayoutDetectionResult:
    layout: str
    confidence: float
    evidence: List[str] = field(default_factory=list)

@dataclass
class ExtractionTrace:
    layout_detector: str = "unknown"
    layout_evidence: List[str] = field(default_factory=list)
    sentence_scores: List[int] = field(default_factory=list)
    selected_sentences: List[int] = field(default_factory=list)
    ocr_confidence: float = 1.0
    regex_used: str = ""
    importo_match: Optional[str] = None
    action: Optional[str] = None

@dataclass
class ExtractedData:
    layout: str
    beneficiario_raw: Optional[str] = None
    beneficiario_clean: Optional[str] = None
    importo: Optional[float] = None
    financial_extract_enabled: bool = False
    confidence: float = 0.0
    trace: ExtractionTrace = field(default_factory=ExtractionTrace)
    forensic_flags: List[str] = field(default_factory=list)


class BaseParser:
    def __init__(self):
        self.entity_stopwords = [
            r'\bS\.?R\.?L\.?S?\b', r'\bS\.?P\.?A\.?\b', r'\bS\.?N\.?C\.?\b', r'\bS\.?A\.?S\.?\b',
            r'\bS\.?C\.?A\.?R\.?L\.?\b', r'\bS\.?S\.?D\.?\b', r'\bO\.?N\.?L\.?U\.?S\b',
            r'\bSOCIET[AÀ]\b', r'\bDITTA\b', r'\bIMPRESA\b', r'\bCOOPERATIVA\b', r'\bCONSORTILE\b',
            r'\bSOCIALE\b', r'\bAZIENDA\b', r'\bGRUPPO\b',
            r'\bAVV\.?\b', r'\bING\.?\b', r'\bARCH\.?\b', r'\bDOTT\.?(SSA)?\b', r'\bGEOM\.?\b',
            r'\bRAG\.?\b', r'\bPROF\.?\b', r'\bDR\.?\b'
        ]

    def parse(self, text: str, layout: LayoutDetectionResult, ocr_conf: float) -> ExtractedData:
        raise NotImplementedError

    def _clean_importo(self, val: str, flags: List[str]) -> Optional[float]:
        try:
            cleaned = val.replace('.', '').replace(',', '.')
            parsed_val = float(cleaned)
            # Hard limit forense: blocca valori impossibili
            if parsed_val <= 0 or parsed_val >= 1_000_000_000:
                flags.append("IMPORTO_INVALIDO")
                return None
            # Soft limit (segnalazione anomalia per audit)
            if parsed_val > 5_000_000:
                flags.append("HIGH_IMPORTO")
            return parsed_val
        except ValueError:
            return None

    def _clean_entita(self, val: str) -> Optional[str]:
        if not val or pd.isna(val): return None
        # Rimuove dati fiscali se in coda
        pulito = re.split(r'\b(?:P\.?\s*IVA|C\.?F\.?|CON\s+SEDE)\b', val, flags=re.IGNORECASE)[0].strip()
        # Rimuove qualifiche aziendali per normalizzazione
        for sw in self.entity_stopwords:
            pulito = re.sub(sw, '', pulito, flags=re.IGNORECASE)
        # Pulizia caratteri speciali
        pulito = re.sub(r'[^\w\s]', ' ', pulito)
        pulito = re.sub(r'\s+', ' ', pulito).strip()
        return pulito.upper() if pulito else None


class VistoParser(BaseParser):
    def parse(self, text: str, layout: LayoutDetectionResult, ocr_conf: float) -> ExtractedData:
        flags = []
        match_cred = re.search(r'Creditore Denominazione:\s*(.+?)(?=\s*-)', text, re.IGNORECASE)
        match_importo = re.search(r'(?:€|EURO)?\s*([\d]{1,3}(?:\.[\d]{3})*,\d{2})', text, re.IGNORECASE)
        
        beneficiario_raw = match_cred.group(1).strip() if match_cred else None
        beneficiario_clean = self._clean_entita(beneficiario_raw)
        
        if not beneficiario_raw:
            flags.append("BENEFICIARIO_ASSENTE")
            
        importo = self._clean_importo(match_importo.group(1), flags) if match_importo else None

        ext_score = 0.95 if importo else 0.50
        if ocr_conf < 0.60:
            flags.append("LOW_OCR")
            
        # Confidence Composita
        overall_conf = layout.confidence * ext_score * ocr_conf
        
        trace = ExtractionTrace(
            layout_detector="keyword_v1",
            layout_evidence=layout.evidence,
            regex_used="visto_strutturata",
            ocr_confidence=ocr_conf,
            importo_match=match_importo.group(1) if match_importo else None
        )
        
        return ExtractedData(
            layout="VISTO_CONTABILE",
            beneficiario_raw=beneficiario_raw,
            beneficiario_clean=beneficiario_clean,
            importo=importo,
            financial_extract_enabled=True,
            confidence=overall_conf,
            trace=trace,
            forensic_flags=flags
        )


class DeterminaParser(BaseParser):
    def __init__(self):
        super().__init__()
        self.scoring_rules = {
            "liquidare": 5, "liquidazione": 5, "pagare": 5,
            "affidare": 4, "affidamento": 4, "impegnare": 4,
            "a favore di": 3, "all'operatore economico": 3,
            "all'impresa": 3, "alla ditta": 2, "aggiudicatar": 2
        }

    def _score_sentence(self, frase: str) -> int:
        score = 0
        lower_frase = frase.lower()
        for keyword, weight in self.scoring_rules.items():
            if keyword in lower_frase:
                score += weight
        return score

    def parse(self, text: str, layout: LayoutDetectionResult, ocr_conf: float) -> ExtractedData:
        flags = []
        # Ricerca del dispositivo
        parti = re.split(r'\bDETERMINA\b|\bORDINA\b|\bDECIDE\b', text, maxsplit=1, flags=re.IGNORECASE)
        if len(parti) <= 1:
            flags.append("NO_DISPOSITIVO")
            
        testo_dispositivo = parti[1] if len(parti) > 1 else text
        frasi = re.split(r'\.\s|;|\n', testo_dispositivo)
        
        # Top-K Sentence Scoring per identificare le frasi finanziarie salienti
        candidate_sentences = []
        for i, frase in enumerate(frasi):
            score = self._score_sentence(frase)
            if score >= 3:
                candidate_sentences.append((score, i, frase))
        
        candidate_sentences.sort(key=lambda x: x[0], reverse=True)
        top_k = candidate_sentences[:3] # Prende le 3 frasi più rilevanti
        
        # Costruisce la finestra di contesto
        context = " ".join([s[2] for s in sorted(top_k, key=lambda x: x[1])]) if top_k else testo_dispositivo[:1000]
        
        # Estrazione beneficiario dal contesto filtrato
        match_op = re.search(r'\b(?:liquidare a favore di|a favore di|all[’\']|alla ditta|all\'operatore economico|liquidare a(?:lla)?)\s+[“"«]?(.+?)(?=\s+la somma|\s+l\'importo|\s+per\b|\s+di\s*€|\s+di\s*euro|[,.;]|$)[”"»]?', context, re.IGNORECASE)
        beneficiario_raw = match_op.group(1).strip() if match_op else None
        beneficiario_clean = self._clean_entita(beneficiario_raw)

        if not beneficiario_raw:
            flags.append("BENEFICIARIO_ASSENTE")

        # Estrazione importo
        match_importo = re.search(r'(?:€|EURO)?\s*([\d]{1,3}(?:\.[\d]{3})*,\d{2})', context, re.IGNORECASE)
        importo = self._clean_importo(match_importo.group(1), flags) if match_importo else None

        # Calcolo extraction score
        ext_score = 0.90 if len(top_k) > 0 else 0.40
        if not importo: ext_score -= 0.30
        
        if ocr_conf < 0.60:
            flags.append("LOW_OCR")
            
        overall_conf = layout.confidence * ext_score * ocr_conf
        
        trace = ExtractionTrace(
            layout_detector="keyword_v1",
            layout_evidence=layout.evidence,
            sentence_scores=[s[0] for s in top_k],
            selected_sentences=[s[1] for s in top_k],
            ocr_confidence=ocr_conf,
            regex_used="determina_topk_context",
            importo_match=match_importo.group(1) if match_importo else None
        )

        return ExtractedData(
            layout="DETERMINAZIONE",
            beneficiario_raw=beneficiario_raw,
            beneficiario_clean=beneficiario_clean,
            importo=importo,
            financial_extract_enabled=True,
            confidence=overall_conf,
            trace=trace,
            forensic_flags=flags
        )


class EsitoGaraParser(BaseParser):
    def parse(self, text: str, layout: LayoutDetectionResult, ocr_conf: float) -> ExtractedData:
        flags = []
        match_op = re.search(r'(?:aggiudicatario|aggiudicazione all\'operatore|affidatario)\s+([^.,;]+)', text, re.IGNORECASE)
        beneficiario_raw = match_op.group(1).strip() if match_op else None
        beneficiario_clean = self._clean_entita(beneficiario_raw)
        
        if not beneficiario_raw:
            flags.append("BENEFICIARIO_ASSENTE")
            
        if ocr_conf < 0.60:
            flags.append("LOW_OCR")
            
        overall_conf = layout.confidence * 0.85 * ocr_conf
        
        trace = ExtractionTrace(
            layout_detector="keyword_v1",
            layout_evidence=layout.evidence,
            ocr_confidence=ocr_conf,
            regex_used="bando_aggiudicato_regex"
        )
        return ExtractedData(
            layout="ESITO_GARA",
            beneficiario_raw=beneficiario_raw,
            beneficiario_clean=beneficiario_clean,
            importo=None,
            financial_extract_enabled=True,
            confidence=overall_conf,
            trace=trace,
            forensic_flags=flags
        )


class DeliberaParser(BaseParser):
    def parse(self, text: str, layout: LayoutDetectionResult, ocr_conf: float) -> ExtractedData:
        flags = []
        if ocr_conf < 0.60:
            flags.append("LOW_OCR")
        
        trace = ExtractionTrace(
            layout_detector="keyword_v1",
            layout_evidence=layout.evidence,
            ocr_confidence=ocr_conf,
            action="financial_disabled"
        )
        return ExtractedData(
            layout="DELIBERAZIONE",
            financial_extract_enabled=False,
            confidence=layout.confidence * 0.95 * ocr_conf,
            trace=trace,
            forensic_flags=flags
        )


class BandoParser(BaseParser):
    def parse(self, text: str, layout: LayoutDetectionResult, ocr_conf: float) -> ExtractedData:
        flags = []
        if ocr_conf < 0.60:
            flags.append("LOW_OCR")
            
        trace = ExtractionTrace(
            layout_detector="keyword_v1",
            layout_evidence=layout.evidence,
            ocr_confidence=ocr_conf,
            action="financial_disabled"
        )
        return ExtractedData(
            layout="BANDO_PURO",
            financial_extract_enabled=False,
            confidence=layout.confidence * 0.95 * ocr_conf,
            trace=trace,
            forensic_flags=flags
        )


class FallbackParser(BaseParser):
    def parse(self, text: str, layout: LayoutDetectionResult, ocr_conf: float) -> ExtractedData:
        trace = ExtractionTrace(
            layout_detector="fallback",
            layout_evidence=layout.evidence,
            ocr_confidence=ocr_conf,
            action="fallback_no_extract"
        )
        return ExtractedData(
            layout="SCONOSCIUTO",
            financial_extract_enabled=False,
            confidence=layout.confidence * 0.40 * ocr_conf,
            trace=trace,
            forensic_flags=["FALLBACK_LAYOUT"]
        )


class DocumentProfileFactory:
    """Factory per l'istanziazione dinamica dei parser basata sul layout rilevato."""
    def __init__(self):
        self.parsers = {
            "VISTO_CONTABILE": VistoParser(),
            "DETERMINAZIONE": DeterminaParser(),
            "DELIBERAZIONE": DeliberaParser(),
            "ESITO_GARA": EsitoGaraParser(),
            "BANDO_PURO": BandoParser(),
            "SCONOSCIUTO": FallbackParser()
        }

    def get_parser(self, layout: str) -> BaseParser:
        return self.parsers.get(layout, self.parsers["SCONOSCIUTO"])


class DocumentExtractor:
    """
    Pipeline di Audit Forense con Factory Pattern, Top-K Sentence Scoring,
    Composite Confidence e ExtractionTrace per l'Explainable AI (XAI).
    """
    def __init__(self):
        self.factory = DocumentProfileFactory()

    def detect_layout(self, testo: str) -> LayoutDetectionResult:
        """Classificatore del layout basato su marcatori forti, con evidence e confidence."""
        testo_upper = testo.upper()
        
        if "VISTO DI REGOLARITÀ CONTABILE" in testo_upper or "IMPEGNO DEFINITIVO" in testo_upper:
            return LayoutDetectionResult("VISTO_CONTABILE", 0.98, ["VISTO DI REGOLARITÀ CONTABILE", "IMPEGNO DEFINITIVO"])
        elif "AGGIUDICAZIONE DEFINITIVA" in testo_upper or "PROPOSTA DI AGGIUDICAZIONE" in testo_upper or "ESITO PROCEDURA" in testo_upper:
            return LayoutDetectionResult("ESITO_GARA", 0.95, ["AGGIUDICAZIONE DEFINITIVA", "ESITO PROCEDURA"])
        elif "AVVISO PUBBLICO" in testo_upper or "BANDO DI GARA" in testo_upper or "MANIFESTAZIONE DI INTERESSE" in testo_upper:
            return LayoutDetectionResult("BANDO_PURO", 0.95, ["AVVISO PUBBLICO", "BANDO DI GARA"])
        elif "LA GIUNTA COMUNALE" in testo_upper or "IL CONSIGLIO COMUNALE" in testo_upper:
            return LayoutDetectionResult("DELIBERAZIONE", 0.95, ["LA GIUNTA COMUNALE", "IL CONSIGLIO COMUNALE"])
        elif "DETERMINA" in testo_upper or "DETERMINAZIONE" in testo_upper:
            return LayoutDetectionResult("DETERMINAZIONE", 0.96, ["DETERMINA", "DETERMINAZIONE"])
            
        return LayoutDetectionResult("SCONOSCIUTO", 0.40, [])

    def extract_entities_full(self, testo: str, doc_type: str = "", ocr_conf: float = 1.0) -> dict:
        """Metodo principale per l'estrazione di entità con Explainable AI (XAI)."""
        if not testo or not isinstance(testo, str):
            testo = ""
            
        testo_pulito = re.sub(r'\s+', ' ', testo)
        layout_res = self.detect_layout(testo_pulito)
        
        # Selezione del parser tramite Factory
        parser = self.factory.get_parser(layout_res.layout)
        extracted = parser.parse(testo_pulito, layout_res, ocr_conf)
        
        # --- Estrazione Campi Standard (CIG, CUP, Capitolo, RUP) ---
        cig_pattern = re.compile(r'\bC\.?I\.?G\.?[\s:;]*([A-Z0-9]{10})\b', re.IGNORECASE)
        cup_pattern = re.compile(r'\bC\.?U\.?P\.?[\s:;]*([A-Z0-9]{15})\b', re.IGNORECASE)
        capitolo_pattern = re.compile(r'\b(?:capitolo|cap\.|capitolo di spesa n\.)\s*(?:n\.?\s*)?(\d+(?:\.\d+)*)\b', re.IGNORECASE)
        
        cig_matches = cig_pattern.findall(testo)
        cig = cig_matches[0].upper() if cig_matches else None
        
        cup_matches = cup_pattern.findall(testo)
        cup = cup_matches[0].upper() if cup_matches else None
        
        cap_matches = capitolo_pattern.findall(testo)
        capitolo = cap_matches[0] if cap_matches else None

        # RUP (Sintattico istituzionale)
        pattern_istituzionale = re.compile(
            r"(?P<ruolo>RESPONSABILE|DIRIGENTE|FUNZIONARIO|IL R\.U\.P\.?|IL SEGRETARIO|IL SINDACO|IL COORDINATORE)\s+"
            r"(?:DEL|DELL['’]|DELLO|DELLA|DEGLI|GENERALE)?\s*"
            r"(?P<area>(?:SETTORE|AREA|SERVIZIO|UFFICIO|DIREZIONE|COMUNE|COMANDO)\s+[A-Z\sÀ-ú]{3,100}?)\s+"
            r"(?:(?P<titolo>DOTT\.?|DOTT\.SSA|DR\.?|ING\.?|ARCH\.?|GEOM\.?|AVV\.?|RAG\.?|PROF\.?|COL\.?|M\.LLO)\s+)?"
            r"(?P<nome>[A-Z][A-ZÀ-úa-z']+(?:\s+[A-Z][A-ZÀ-úa-z']+){1,3})\b",
            re.IGNORECASE
        )
        match_rup = pattern_istituzionale.search(testo)
        rup = match_rup.group("nome").upper().strip() if match_rup else None
        
        # Costruisce l'output finale armonizzato
        return {
            "layout_rilevato": extracted.layout,
            "layout_confidence": layout_res.confidence,
            "beneficiario": extracted.beneficiario_clean,
            "beneficiario_raw": extracted.beneficiario_raw,
            "importo_max_estratto": extracted.importo,
            "financial_extract_enabled": extracted.financial_extract_enabled,
            "confidence": extracted.confidence,
            "extraction_method": extracted.trace.regex_used if extracted.trace.regex_used else extracted.trace.action,
            "trace_json": json.dumps(asdict(extracted.trace), ensure_ascii=False),
            "forensic_flags": "|".join(extracted.forensic_flags) if extracted.forensic_flags else None,
            "cig_estratto": cig,
            "cup_estratto": cup,
            "capitolo": capitolo,
            "responsabile": rup
        }

# Alias per retrocompatibilità con analyze_albo.py
DelibereExtractor = DocumentExtractor
