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
        doc_type_enum, event_type_enum = route_document(doc.text_preview or "")

        # 2. Build the list of actors involved
        actors: List[Actor] = []
        if doc.responsabile and doc.responsabile != "NON IDENTIFICATO":
            # Gestisci il caso in cui responsabile potrebbe essere una lista
            responsabile_name = doc.responsabile[0] if isinstance(doc.responsabile, list) else doc.responsabile
            actors.append(
                Actor(
                    name=responsabile_name,
                    actor_type=ActorType.RUP,
                    role=getattr(doc, 'rup_ruolo', None),
                    area=getattr(doc, 'rup_area', None),
                )
            )
        if doc.beneficiario:
            # Gestisci il caso in cui beneficiario potrebbe essere una lista
            beneficiario_name = doc.beneficiario
            if isinstance(beneficiario_name, list):
                # Prendi il primo beneficiario o concatena tutti i beneficiari
                if len(beneficiario_name) > 0:
                    beneficiario_name = beneficiario_name[0]  # Oppure ", ".join(beneficiario_name)
                else:
                    beneficiario_name = None
            
            if beneficiario_name and beneficiario_name not in [
                "NON IDENTIFICATO",
                "DIVERSI/NON APPLICABILE",
            ]:
                actors.append(Actor(name=beneficiario_name, actor_type=ActorType.BENEFICIARIO))

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
            raw_text=doc.text_preview or "",
            metadata={"urn": doc.legal_urn, "source_file": doc.pdf_name},
        )
        return event