import re
from typing import Dict, Optional, List
from src.models.administrative_event import EventType, DocumentType

# Pattern per la classificazione del documento (Livello 1)
DOCUMENT_PATTERNS: Dict[DocumentType, List[str]] = {
    DocumentType.DETERMINA: [
        r"determin(azione|a)\s*(n\.\s*\d+|del\s*\d{1,2}/\d{2,4})",
        r"determin(azione|a)\s+di\s+(dirigente|responsabile|settore)",
        r"deter\.?\s+n\.\s*\d+",
        r"il\s+(dirigente|responsabile|rup)\s+.*\s+determina",
    ],
    DocumentType.DELIBERA: [
        r"deliber(azione|a)\s*(n\.\s*\d+|del\s*\d{1,2}/\d{2,4})",
        r"deliberazione\s+di\s+giunta",
        r"deliberazione\s+di\s+consiglio",
        r"delib\.?\s+n\.\s*\d+",
        r"la\s+giunta\s+.*\s+delibera",
        r"il\s+consiglio\s+.*\s+delibera",
    ],
    DocumentType.BANDO: [
        r"bando\s+(di\s+gara|per\s+l’?affidamento|n\.\s*\d+)",
        r"avviso\s+pubblico",
        r"procedura\s+(aperta|ristretta|negoziata)",
    ],
    DocumentType.AVVISO: [
        r"avviso\s+(pubblico|di\s+selezione|n\.\s*\d+)",
        r"manifestazione\s+d’?interesse",
    ],
    DocumentType.ORDINANZA: [
        r"ordinanza\s+(n\.\s*\d+|del\s+sindaco|sindacale)",
        r"il\s+sindaco\s+.*\s+ordina",
    ],
    DocumentType.ATTO: [
        r"atto\s+(amministrativo|dirigenziale|n\.\s*\d+)",
    ],
    DocumentType.NUMERARIA: [
        r"impegno\s+(di\s+spesa|n\.\s*\d+)",
        r"liquidazione\s+(n\.\s*\d+|della\s+spesa)",
        r"mandato\s+(di\s+pagamento|n\.\s*\d+)",
    ],
    DocumentType.ESITO: [
        r"esito\s+(di\s+gara|aggiudicazione|n\.\s*\d+)",
        r"verbale\s+(di\s+gara|aggiudicazione)",
        r"aggiudicat(ario|o)\s+(a\s+|:)",
    ],
}

# Pattern per la classificazione dell'evento (Livello 2)
EVENT_PATTERNS: Dict[DocumentType, Dict[str, EventType]] = {
    DocumentType.DETERMINA: {
        r"(?:si\s+)?(liquidare|liquida|liquidazione)\s+(la\s+)?(somma\s+)?(di\s+)?€?\s*\d{1,3}(?:[\.,]\d{3})*(?:[\.,]\d{2})?": EventType.LIQUIDAZIONE,
        r"(?:si\s+)?(impegnare|impegna|impegno)\s+(la\s+)?(somma\s+)?(di\s+)?€?\s*\d{1,3}(?:[\.,]\d{3})*(?:[\.,]\d{2})?": EventType.IMPEGNO,
        r"(?:si\s+)?(pagare|paga|pagamento)\s+(la\s+)?(somma\s+)?(di\s+)?€?\s*\d{1,3}(?:[\.,]\d{3})*(?:[\.,]\d{2})?": EventType.PAGAMENTO,
        r"(?:si\s+)?(affidare|affida|affidamento)\s+(il\s+)?(servizio|lotto|lavori|fornitura)": EventType.AFFIDAMENTO,
    },
    DocumentType.DELIBERA: {
        r"(nomina|nomina\s+del)\s+(del\s+)?(rup|responsabile\s+del\s+procedimento)": EventType.NOMINA,
        r"(selezione|selezione\s+pubblica)\s+(pubblica|per\s+titoli)?": EventType.SELEZIONE,
    },
}

def classify_document(text: str) -> DocumentType:
    if not text: return DocumentType.ALTRO
    text_lower = text.lower()
    for doc_type, patterns in DOCUMENT_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text_lower, re.IGNORECASE): return doc_type
    return DocumentType.ALTRO

def classify_event(text: str, doc_type: DocumentType) -> EventType:
    if doc_type not in EVENT_PATTERNS: return EventType.ALTRO
    text_lower = text.lower()
    for pattern, event_type in EVENT_PATTERNS[doc_type].items():
        if re.search(pattern, text_lower, re.IGNORECASE): return event_type
    return EventType.ALTRO

def route_document(text: str) -> tuple[DocumentType, EventType]:
    doc_type = classify_document(text)
    event_type = classify_event(text, doc_type)
    return doc_type, event_type
