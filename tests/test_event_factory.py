import pytest
from unittest.mock import patch
from pathlib import Path

from delibere_comunali.models.parsed_document import ParsedDocument
from delibere_comunali.processing.event_factory import DigitalTwinEventFactory
from delibere_comunali.models.administrative_event import DocumentType, EventType, ActorType

@pytest.fixture
def sample_parsed_document():
    """Fornisce un ParsedDocument di esempio per i test."""
    return ParsedDocument(
        pdf_name="test_delibera_123.pdf",
        pdf_path="/fake/path/test_delibera_123.pdf",
        oggetto="Affidamento servizio di pulizia",
        numero_atto="123",
        data_atto="2024-07-15",
        importo_max=1500.50,
        cig="Z123456789",
        cup="A12B34567890123",
        rup_nome="MARIO ROSSI",
        rup_ruolo="RESPONSABILE",
        rup_area="SERVIZI TECNICI",
        beneficiario="PULIZIE S.R.L.",
        legal_urn="urn:nir:comune.test;dirigente:determina:2024-07-15;123",
        _text="Questo è il testo di una determina di affidamento."
    )

@patch('delibere_comunali.processing.event_factory.route_document')
def test_create_event_with_all_actors(mock_route_document, sample_parsed_document):
    """Verifica la creazione di un evento quando sia il RUP che il Beneficiario sono presenti."""
    # Configura il mock per il router
    mock_route_document.return_value = (DocumentType.DETERMINA, EventType.AFFIDAMENTO)

    factory = DigitalTwinEventFactory()
    event = factory.create_event(sample_parsed_document)

    # Verifiche
    mock_route_document.assert_called_once_with(sample_parsed_document._text)
    
    assert event.event_type == EventType.AFFIDAMENTO
    assert event.document_type == DocumentType.DETERMINA
    assert event.document_id == "test_delibera_123"
    assert event.title == "Affidamento servizio di pulizia"
    assert event.economic_value == 1500.50
    assert len(event.actors) == 2
    
    rup_actor = next((a for a in event.actors if a.actor_type == ActorType.RUP), None)
    assert rup_actor is not None
    assert rup_actor.name == "MARIO ROSSI"

    beneficiary_actor = next((a for a in event.actors if a.actor_type == ActorType.BENEFICIARIO), None)
    assert beneficiary_actor is not None
    assert beneficiary_actor.name == "PULIZIE S.R.L."

@patch('delibere_comunali.processing.event_factory.route_document')
def test_create_event_without_actors(mock_route_document, sample_parsed_document):
    """Verifica la creazione di un evento quando gli attori non sono identificati."""
    # Modifica il documento per non avere attori identificati
    sample_parsed_document.rup_nome = "NON IDENTIFICATO"
    sample_parsed_document.beneficiario = "DIVERSI/NON APPLICABILE"
    
    mock_route_document.return_value = (DocumentType.DELIBERA, EventType.APPROVAZIONE)

    factory = DigitalTwinEventFactory()
    event = factory.create_event(sample_parsed_document)

    assert event.event_type == EventType.APPROVAZIONE
    assert len(event.actors) == 0