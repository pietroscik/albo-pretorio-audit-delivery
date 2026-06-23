from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional
from enum import Enum

try:
    from dateutil import parser as dateparser
except Exception:  # pragma: no cover - optional dependency
    dateparser = None

class EventType(Enum):
    IMPEGNO = "Impegno di spesa"
    AFFIDAMENTO = "Affidamento"
    LIQUIDAZIONE = "Liquidazione"
    PAGAMENTO = "Pagamento"
    NOMINA = "Nomina"
    SELEZIONE = "Selezione"
    ALTRO = "Altro"

class DocumentType(Enum):
    DETERMINA = "Determinazione"
    DELIBERA = "Delibera"
    ORDINANZA = "Ordinanza"
    BANDO = "Bando"
    AVVISO = "Avviso"
    ATTO = "Atto"
    NUMERARIA = "Atto Numerario"
    ESITO = "Esito/Verbale"
    ALTRO = "Altro"

class ActorType(Enum):
    RUP = "RUP"
    BENEFICIARIO = "Beneficiario"

@dataclass
class Actor:
    name: str
    actor_type: ActorType
    role: Optional[str] = None
    area: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "actor_type": self.actor_type.name if isinstance(self.actor_type, ActorType) else self.actor_type,
            "role": self.role,
            "area": self.area,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Actor":
        actor_type = _coerce_enum(ActorType, data.get("actor_type"), ActorType.BENEFICIARIO)
        return cls(
            name=data.get("name", ""),
            actor_type=actor_type,
            role=data.get("role"),
            area=data.get("area"),
        )


def _coerce_enum(enum_cls, value, default):
    if isinstance(value, enum_cls):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        candidate = value.strip()
        if not candidate:
            return default
        try:
            return enum_cls[candidate.upper()]
        except KeyError:
            for member in enum_cls:
                if member.value.lower() == candidate.lower():
                    return member
    return default


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
        if dateparser is not None:
            try:
                return dateparser.parse(candidate, dayfirst=True)
            except Exception:
                return candidate
        return candidate
    return value


def _serialize_datetime(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time()).isoformat()
    return value

@dataclass
class AdministrativeEvent:
    event_type: EventType = EventType.ALTRO
    document_type: DocumentType = DocumentType.ALTRO
    document_id: str = ""
    document_number: Optional[str] = None
    document_date: Optional[Any] = None
    title: Optional[str] = None
    economic_value: Optional[float] = None
    cig: Optional[str] = None
    cup: Optional[str] = None
    actors: List[Actor] = field(default_factory=list)
    confidence: float = 0.0
    raw_text: str = ""
    metadata: Dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.event_type = _coerce_enum(EventType, self.event_type, EventType.ALTRO)
        self.document_type = _coerce_enum(DocumentType, self.document_type, DocumentType.ALTRO)
        self.document_date = _coerce_datetime(self.document_date)
        self.actors = [
            actor if isinstance(actor, Actor) else Actor.from_dict(actor)
            for actor in (self.actors or [])
        ]
        self.metadata = dict(self.metadata or {})

    def to_dict(self) -> Dict[str, Any]:
        document_date = _serialize_datetime(self.document_date)
        return {
            "event_type": self.event_type.name if isinstance(self.event_type, EventType) else self.event_type,
            "document_type": self.document_type.name if isinstance(self.document_type, DocumentType) else self.document_type,
            "document_id": self.document_id,
            "document_number": self.document_number,
            "document_date": document_date,
            "title": self.title,
            "economic_value": self.economic_value,
            "cig": self.cig,
            "cup": self.cup,
            "actors": [actor.to_dict() for actor in self.actors],
            "confidence": self.confidence,
            "raw_text": self.raw_text,
            "metadata": dict(self.metadata),
            "doc_id": self.document_id,
            "type": self.event_type.value if isinstance(self.event_type, EventType) else self.event_type,
            "date": document_date,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AdministrativeEvent":
        actors = data.get("actors") or []
        return cls(
            event_type=_coerce_enum(EventType, data.get("event_type", data.get("type")), EventType.ALTRO),
            document_type=_coerce_enum(DocumentType, data.get("document_type", data.get("doc_type")), DocumentType.ALTRO),
            document_id=data.get("document_id", data.get("doc_id", "")),
            document_number=data.get("document_number"),
            document_date=data.get("document_date", data.get("date")),
            title=data.get("title"),
            economic_value=data.get("economic_value"),
            cig=data.get("cig"),
            cup=data.get("cup"),
            actors=[actor if isinstance(actor, Actor) else Actor.from_dict(actor) for actor in actors],
            confidence=data.get("confidence", 0.0),
            raw_text=data.get("raw_text", ""),
            metadata=data.get("metadata", {}),
        )
