# src/models/procedure.py
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from datetime import datetime
import uuid
from enum import Enum
from .administrative_event import AdministrativeEvent, EventType

class ProcedureStatus(Enum):
    """Stato di un procedimento."""
    IN_CORSO = "IN_CORSO"
    COMPLETO = "COMPLETO"
    ANNULLATO = "ANNULLATO"
    SOSPESO = "SOSPESO"
    SCADUTO = "SCADUTO"

@dataclass
class Procedure:
    """Rappresenta un procedimento amministrativo (es: una gara)."""
    procedure_id: str  # = CIG o hash(oggetto + ente + data)
    events: List[AdministrativeEvent] = field(default_factory=list)
    title: Optional[str] = None
    total_amount: float = 0.0
    status: ProcedureStatus = ProcedureStatus.IN_CORSO
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    anomalies: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)

    def add_event(self, event: AdministrativeEvent):
        """Aggiunge un evento al procedimento."""
        self.events.append(event)
        self._update_metadata(event)

    def _update_metadata(self, event: AdministrativeEvent):
        """Aggiorna metadati e stato del procedimento."""
        # Aggiorna importo totale
        if event.economic_value:
            self.total_amount += event.economic_value

        # Aggiorna date
        if event.document_date:
            if not self.start_date or event.document_date < self.start_date:
                self.start_date = event.document_date
            if not self.end_date or event.document_date > self.end_date:
                self.end_date = event.document_date

        # Aggiorna titolo (prende il primo disponibile)
        if event.title and not self.title:
            self.title = event.title

    def to_dict(self) -> Dict:
        """Converte il procedimento in dizionario."""
        return {
            "procedure_id": self.procedure_id,
            "title": self.title,
            "events": [e.to_dict() for e in self.events],
            "total_amount": self.total_amount,
            "status": self.status.value,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "anomalies": self.anomalies,
            "metadata": self.metadata,
        }