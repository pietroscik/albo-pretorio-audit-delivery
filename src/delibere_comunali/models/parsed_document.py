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
    legal_urn: Optional[str] = None  # Added this field
    
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
    text_chars: Optional[int] = None
    text_words: Optional[int] = None
    unique_words: Optional[int] = None
    euro_mentions: Optional[int] = None
    cig_mentions: Optional[int] = None
    cup_mentions: Optional[int] = None
    date_mentions: Optional[int] = None
    years_mentioned: Optional[str] = None
    extraction_method: Optional[str] = None
    trace_json: Optional[str] = None
    layout_confidence: Optional[float] = None
    layout_rilevato: Optional[str] = None  # Added this field
    classification_confidence_score: Optional[float] = None
    classification_method: Optional[str] = None
    filename_meta: Optional[str] = None
    oggetto_orig: Optional[str] = None
    tipologia: Optional[str] = None
    doc_type_meta: Optional[str] = None
    source_meta: Optional[str] = None
    pdf_name_meta: Optional[str] = None
    classification_terms_meta: Optional[str] = None
    beneficiario_raw: Optional[str] = None
    
    # Compliance
    is_signed: bool = False
    is_accessible: bool = False
    pdf_version: Optional[float] = None
    compliance_score: int = 0
    doc_type_feat: Optional[float] = None
    category_feat: Optional[float] = None
    subcategory_feat: Optional[float] = None
    classification_confidence_feat: Optional[float] = None
    source_feat: Optional[str] = None
    text_sha256_feat: Optional[float] = None
    text_chars_feat: Optional[float] = None
    text_words_feat: Optional[float] = None
    unique_words_feat: Optional[float] = None
    euro_mentions_feat: Optional[float] = None
    cig_feat: Optional[str] = None
    cup_feat: Optional[str] = None
    cig_mentions_feat: Optional[float] = None
    cup_mentions_feat: Optional[float] = None
    date_mentions_feat: Optional[float] = None
    years_mentioned_feat: Optional[float] = None
    importo_max_feat: Optional[float] = None
    importo_sum_feat: Optional[float] = None
    importi_count_feat: Optional[float] = None
    accounting_relevant_feat: Optional[bool] = None
    missing_amount_expected_feat: Optional[bool] = None
    importo_lettere_feat: Optional[float] = None
    piva_beneficiario_feat: Optional[str] = None
    iban_feat: Optional[str] = None
    codice_appalti_feat: Optional[str] = None
    tipo_procedura_feat: Optional[str] = None
    quadro_economico_feat: Optional[str] = None
    anomalie_feat: Optional[str] = None
    extraction_method_feat: Optional[str] = None
    trace_json_feat: Optional[str] = None
    beneficiario_raw_feat: Optional[str] = None
    layout_confidence_feat: Optional[float] = None
    legal_urn_feat: Optional[str] = None
    is_signed_feat: Optional[bool] = None
    is_accessible_feat: Optional[bool] = None
    pdf_version_feat: Optional[float] = None
    compliance_score_feat: Optional[int] = None
    veridicità_score_feat: Optional[float] = None
    solidità_globale_feat: Optional[float] = None
    is_personnel_competence_relevant_feat: Optional[bool] = None
    personnel_competences_feat: Optional[str] = None
    decree_references_feat: Optional[str] = None
    solidità_globale_prec: Optional[float] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ParsedDocument':
        """
        Create a ParsedDocument instance from a dictionary, ignoring unknown fields.
        """
        # Get all field names of this dataclass
        field_names = {field.name for field in cls.__dataclass_fields__.values()}
        
        # Filter the input data to only include known fields
        filtered_data = {k: v for k, v in data.items() if k in field_names}
        
        # Create instance with filtered data
        return cls(**filtered_data)
