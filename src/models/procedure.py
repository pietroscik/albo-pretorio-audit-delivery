from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional

from src.models.administrative_event import AdministrativeEvent


class ProcedureStatus(Enum):
    IN_CORSO = "IN_CORSO"
    COMPLETO = "COMPLETO"
    ANNULLATO = "ANNULLATO"
    SOSPESO = "SOSPESO"
    SCADUTO = "SCADUTO"


def _coerce_datetime(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    if isinstance(value, str):
        candidate = value.strip()
        if not candidate:
            return None
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(candidate, fmt)
            except ValueError:
                continue
        return candidate
    return value


def _serialize_datetime(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time()).isoformat()
    return value


def _coerce_status(value):
    if isinstance(value, ProcedureStatus):
        return value
    if isinstance(value, str):
        candidate = value.strip()
        if candidate:
            try:
                return ProcedureStatus[candidate.upper()]
            except KeyError:
                for member in ProcedureStatus:
                    if member.value.lower() == candidate.lower():
                        return member
    return ProcedureStatus.IN_CORSO


@dataclass(init=False)
class Procedure:
    procedure_id: str
    events: List[AdministrativeEvent] = field(default_factory=list)
    title: Optional[str] = None
    total_amount: float = 0.0
    status: ProcedureStatus = ProcedureStatus.IN_CORSO
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    anomalies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __init__(
        self,
        procedure_id: Optional[str] = None,
        *,
        primary_key: Optional[str] = None,
        events: Optional[Iterable[AdministrativeEvent]] = None,
        title: Optional[str] = None,
        total_amount: float = 0.0,
        status: ProcedureStatus | str = ProcedureStatus.IN_CORSO,
        start_date: Optional[Any] = None,
        end_date: Optional[Any] = None,
        anomalies: Optional[Iterable[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.procedure_id = procedure_id or primary_key or ""
        self.events = list(events or [])
        self.title = title
        self.total_amount = float(total_amount or 0.0)
        self.status = _coerce_status(status)
        self.start_date = _coerce_datetime(start_date)
        self.end_date = _coerce_datetime(end_date)
        self.anomalies = list(anomalies or [])
        self.metadata = dict(metadata or {})
        if self.events:
            self._rebuild_from_events()

    @property
    def primary_key(self) -> str:
        return self.procedure_id

    @primary_key.setter
    def primary_key(self, value: str) -> None:
        self.procedure_id = value

    @property
    def total_value(self) -> float:
        return self.total_amount

    @total_value.setter
    def total_value(self, value: float) -> None:
        self.total_amount = float(value or 0.0)

    def _rebuild_from_events(self) -> None:
        self.total_amount = 0.0
        self.start_date = None
        self.end_date = None
        inferred_title = self.title
        for event in self.events:
            self._update_metadata(event, preserve_title=bool(inferred_title))
            if not inferred_title and event.title:
                inferred_title = event.title
        self.title = inferred_title

    def _update_metadata(self, event: AdministrativeEvent, preserve_title: bool = False) -> None:
        if event.economic_value is not None:
            self.total_amount += float(event.economic_value)

        event_date = _coerce_datetime(event.document_date)
        if isinstance(event_date, datetime):
            if self.start_date is None or event_date < self.start_date:
                self.start_date = event_date
            if self.end_date is None or event_date > self.end_date:
                self.end_date = event_date

        if not preserve_title and event.title and not self.title:
            self.title = event.title

    def add_event(self, event: AdministrativeEvent) -> None:
        self.events.append(event)
        self._update_metadata(event)

    def to_dict(self) -> Dict[str, Any]:
        events = []
        for event in self.events:
            if hasattr(event, "to_dict"):
                event_data = event.to_dict()
            else:
                event_data = {}
            event_data.setdefault("doc_id", getattr(event, "document_id", None))
            event_data.setdefault("type", getattr(getattr(event, "event_type", None), "value", getattr(event, "event_type", None)))
            event_data.setdefault("date", _serialize_datetime(getattr(event, "document_date", None)))
            events.append(event_data)

        return {
            "procedure_id": self.procedure_id,
            "primary_key": self.procedure_id,
            "title": self.title,
            "events": events,
            "total_amount": self.total_amount,
            "total_value": self.total_amount,
            "status": self.status.value,
            "start_date": _serialize_datetime(self.start_date),
            "end_date": _serialize_datetime(self.end_date),
            "anomalies": list(self.anomalies),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Procedure":
        events = [AdministrativeEvent.from_dict(event) if isinstance(event, dict) else event for event in data.get("events", [])]
        return cls(
            procedure_id=data.get("procedure_id", data.get("primary_key", "")),
            events=events,
            title=data.get("title"),
            total_amount=data.get("total_amount", data.get("total_value", 0.0)),
            status=data.get("status", ProcedureStatus.IN_CORSO),
            start_date=data.get("start_date"),
            end_date=data.get("end_date"),
            anomalies=data.get("anomalies", []),
            metadata=data.get("metadata", {}),
        )
