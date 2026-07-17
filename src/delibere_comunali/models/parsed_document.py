from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from pathlib import Path

@dataclass
class ParsedDocument:
    """
    Modello dati per rappresentare un documento analizzato dal sistema di parsing.
    Contiene tutti i metadati estratti da un documento PDF.
    """
    # Informazioni di base
    pdf_name: str = ""
    pdf_path: str = ""
    
    # Classificazione
    doc_type: str = "unknown"
    category: Optional[str] = None
    subcategory: Optional[str] = None
    classification_confidence: Optional[float] = None
    classification_terms: Optional[str] = None
    
    # Dati principali documento
    oggetto: Optional[str] = None
    numero_atto: Optional[str] = None
    data_atto: Optional[str] = None
    numero_registro: Optional[str] = None
    data_registro: Optional[str] = None
    
    # Dati finanziari
    importi_raw: List[str] = field(default_factory=list)
    importo_max: Optional[float] = None
    importo_sum: Optional[float] = None
    importi_count: int = 0
    importo_lettere: Optional[float] = None
    
    # Codici identificativi
    cig: Optional[str] = None
    cup: Optional[str] = None
    codice_appalti: Optional[str] = None
    tipo_procedura: Optional[str] = None
    
    # Parti coinvolte
    beneficiario: Optional[str] = None
    piva_beneficiario: Optional[str] = None
    responsabile: Optional[str] = None
    ufficio: Optional[str] = None
    
    # Dati contabili
    iban: Optional[str] = None
    impegno_num: Optional[str] = None
    impegno_anno: Optional[str] = None
    accert_num: Optional[str] = None
    accert_anno: Optional[str] = None
    quadro_economico: Optional[str] = None
    capitolo: Optional[str] = None
    peg_riga: Optional[str] = None
    
    # Flag e indicatori
    is_visto_contabile: bool = False
    source: str = "text"  # 'text', 'ocr', 'html', 'p7m_extraction_failed'
    accounting_relevant: bool = False
    missing_amount_expected: bool = False
    
    # Valutazioni
    veridicità_score: float = 0
    solidità_globale: float = 0
    
    # Competenze del personale
    is_personnel_competence_relevant: bool = False
    personnel_competences: str = "[]"  # JSON string
    decree_references: str = "[]"      # JSON string
    
    # Anomalie
    anomalie: Optional[str] = None
    
    # Hash e dati tecnici
    text_sha256: Optional[str] = None
    text_path: Optional[str] = None
    text_preview: Optional[str] = None
    
    # Compliance
    is_signed: bool = False
    is_accessible: bool = False
    pdf_version: Optional[float] = None
    compliance_score: int = 0
    
    # RUP (Responsabile Unico del Procedimento)
    rup_nome: Optional[str] = None
    rup_area: Optional[str] = None
    rup_ruolo: Optional[str] = None
    
    # Legal URN
    legal_urn: Optional[str] = None
    
    # Campo interno per memorizzare il testo completo (non serializzato)
    _text: str = field(default="", repr=False)
    
    # Gruppo atto (per aggregazione)
    atto_group: Optional[str] = None

    def model_dump(self) -> Dict[str, Any]:
        """Converte il dataclass in dizionario per serializzazione."""
        result = {}
        for field_name in self.__annotations__:
            if field_name == '_text':
                continue  # Non serializzare il campo interno
            value = getattr(self, field_name)
            result[field_name] = value
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ParsedDocument':
        """Crea un'istanza da un dizionario."""
        # Gestisci i campi speciali come liste
        if 'importi_raw' in data and isinstance(data['importi_raw'], str):
            import json
            try:
                data['importi_raw'] = json.loads(data['importi_raw'])
            except:
                data['importi_raw'] = []
        
        # Gestisci il campo _text separatamente
        text_content = data.pop('_text', '') if '_text' in data else ''
        
        instance = cls(**{k: v for k, v in data.items() if k in cls.__annotations__})
        instance._text = text_content
        return instance