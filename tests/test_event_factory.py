from unittest.mock import patch

import pytest

from delibere_comunali.models.administrative_event import (
    ActorType,
    DocumentType,
    EventType,
)
from delibere_comunali.models.parsed_document import ParsedDocument
from delibere_comunali.processing.event_factory import DigitalTwinEventFactory


@pytest.fixture
def sample_parsed_document():
    """Fornisce un ParsedDocument di esempio per i test."""
    return ParsedDocument(
        pdf_name="test_delibera_123.pdf",
        pdf_path="/fake/path/test_delibera_123.pdf",
        oggetto="Affidamento servizio di pulizia",
        numero_atto="123",
        data_atto="2024-07-15",
        importo_max=1500.5,
        cig="Z123456789",
        cup="A12B34567890123",
        responsabile="MARIO ROSSI",
        ufficio="SERVIZI TECNICI",
        beneficiario="PULIZIE S.R.L.",
        legal_urn="urn:nir:comune.test;dirigente:determina:2024-07-15;123",
        text_preview="Questo e il testo di una determina di affidamento.",
    )


@patch("delibere_comunali.processing.event_factory.route_document")
def test_create_event_with_all_actors(mock_route_document, sample_parsed_document):
    """Verifica la creazione di un evento quando sia il RUP che il Beneficiario sono presenti."""
    # Configura il mock per il router
    mock_route_document.return_value = (DocumentType.DETERMINA, EventType.AFFIDAMENTO)

    factory = DigitalTwinEventFactory()
    event = factory.create_event(sample_parsed_document)

    # Verifiche
    mock_route_document.assert_called_once_with(sample_parsed_document.text_preview)

    assert event.event_type == EventType.AFFIDAMENTO
    assert event.document_type == DocumentType.DETERMINA
    assert event.document_id == "test_delibera_123"
    assert event.title == "Affidamento servizio di pulizia"
    assert event.economic_value == 1500.5
    assert len(event.actors) == 2

    rup_actor = next((a for a in event.actors if a.actor_type == ActorType.RUP), None)
    assert rup_actor is not None
    assert rup_actor.name == "MARIO ROSSI"


@patch("delibere_comunali.processing.event_factory.route_document")
def test_create_event_without_actors(mock_route_document, sample_parsed_document):
    """Verifica la creazione di un evento quando non ci sono attori."""
    # Crea un documento senza RUP
    doc_no_actors = ParsedDocument(
        pdf_name="test_delibera_456.pdf",
        pdf_path="/fake/path/test_delibera_456.pdf",
        oggetto="Approvazione regolamento",
        numero_atto="456",
        data_atto="2024-07-16",
        importo_max=500.0,
        legal_urn="urn:nir:comune.test;giunta:delibera:2024-07-16;456",
        text_preview="Questo e il testo di una delibera senza attori.",
    )

    # Configura il mock per il router
    mock_route_document.return_value = (DocumentType.DELIBERA, EventType.APPROVAZIONE)

    factory = DigitalTwinEventFactory()
    event = factory.create_event(doc_no_actors)

    # Verifiche
    mock_route_document.assert_called_once_with(doc_no_actors.text_preview)

    assert event.event_type == EventType.APPROVAZIONE
    assert event.document_type == DocumentType.DELIBERA
    assert event.document_id == "test_delibera_456"
    assert event.title == "Approvazione regolamento"
    assert event.economic_value == 500.0
    # Potrebbe non avere attori se non ci sono RUP o Beneficiari
    assert isinstance(event.actors, list)
