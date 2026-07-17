from pathlib import Path
from typing import List

from ..models.administrative_event import (
    Actor,
    ActorType,
    AdministrativeEvent,
    DocumentType,
    EventType,
)
from ..models.parsed_document import ParsedDocument
from .routers.event_router import route_document


class DigitalTwinEventFactory:
    """
    Factory class responsible for creating AdministrativeEvent objects
    from parsed document data for the Digital Twin.
    """

    def create_event(self, doc: ParsedDocument) -> AdministrativeEvent:
        """
        Creates an AdministrativeEvent from a ParsedDocument object.
        """
        # 1. Route the document to determine its type in the Digital Twin context
        doc_type_enum, event_type_enum = route_document(doc._text)

        # 2. Build the list of actors involved
        actors: List[Actor] = []
        if doc.rup_nome and doc.rup_nome != "NON IDENTIFICATO":
            actors.append(
                Actor(
                    name=doc.rup_nome,
                    actor_type=ActorType.RUP,
                    role=doc.rup_ruolo,
                    area=doc.rup_area,
                )
            )
        if doc.beneficiario and doc.beneficiario not in [
            "NON IDENTIFICATO",
            "DIVERSI/NON APPLICABILE",
        ]:
            actors.append(Actor(name=doc.beneficiario, actor_type=ActorType.BENEFICIARIO))

        # 3. Create the event object
        event = AdministrativeEvent(
            event_type=event_type_enum,
            document_type=doc_type_enum,
            document_id=Path(doc.pdf_name).stem,
            document_number=doc.numero_atto,
            document_date=doc.data_atto,
            title=doc.oggetto,
            economic_value=doc.importo_max,
            cig=doc.cig,
            cup=doc.cup,
            actors=actors,
            confidence=0.8,  # Placeholder confidence, can be improved later
            raw_text=doc._text,
            metadata={"urn": doc.legal_urn, "source_file": doc.pdf_name},
        )
        return event