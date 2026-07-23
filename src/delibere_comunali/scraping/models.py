from dataclasses import dataclass, asdict
from typing import Optional, List

@dataclass
class AlboItem:
    page_url: str
    titolo: str
    numero: Optional[str]
    data_pubblicazione: Optional[str]
    tipologia: Optional[str]
    ufficio: Optional[str]
    oggetto: Optional[str]
    dettaglio_url: Optional[str]
    provincia: Optional[str] = None
    ente_nome: Optional[str] = None
    ente_codice_istat: Optional[str] = None
    allegati: List[str] = None
    
    def __post_init__(self):
        if self.allegati is None:
            self.allegati = []