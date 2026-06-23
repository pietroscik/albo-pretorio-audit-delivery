# tests/test_events.py
import pytest
import unittest
from datetime import datetime
from src.models.administrative_event import (
    AdministrativeEvent, EventType, DocumentType, Actor, ActorType
)
from src.models.procedure import Procedure, ProcedureStatus
from src.routers.event_router import classify_document, classify_event, route_document
from src.builders.procedure_builder import ProcedureBuilder

# --- Test per AdministrativeEvent ---
class TestAdministrativeEvent:
    def test_create_event(self):
        event = AdministrativeEvent(
            event_type=EventType.AFFIDAMENTO,
            document_type=DocumentType.DETERMINA,
            document_number="123/2025",
            document_date=datetime(2025, 6, 17),
            title="Affidamento servizio pulizie",
            economic_value=50000.0,
            cig="Z1234567890",
        )
        assert event.event_type == EventType.AFFIDAMENTO
        assert event.document_type == DocumentType.DETERMINA
        assert event.cig == "Z1234567890"

    def test_to_dict(self):
        event = AdministrativeEvent(
            event_type=EventType.LIQUIDAZIONE,
            document_number="456/2025",
            economic_value=25000.0,
        )
        data = event.to_dict()
        assert data["event_type"] == "LIQUIDAZIONE"
        assert data["economic_value"] == 25000.0

    def test_from_dict(self):
        data = {
            "event_type": "AFFIDAMENTO",
            "document_type": "DETERMINA",
            "economic_value": 30000.0,
            "cig": "X9876543210",
        }
        event = AdministrativeEvent.from_dict(data)
        assert event.event_type == EventType.AFFIDAMENTO
        assert event.cig == "X9876543210"

# --- Test per Procedure ---
class TestProcedure:
    def test_add_event(self):
        procedure = Procedure(procedure_id="CIG_Z123")
        event = AdministrativeEvent(
            event_type=EventType.AFFIDAMENTO,
            economic_value=10000.0,
        )
        procedure.add_event(event)
        assert len(procedure.events) == 1
        assert procedure.total_amount == 10000.0

# --- Test per EventRouter ---
class TestEventRouter:
    def test_classify_document_determina(self):
        text = "Determinazione n. 123 del 17/06/2025"
        assert classify_document(text) == DocumentType.DETERMINA

    def test_classify_document_delibera(self):
        text = "Deliberazione di Giunta n. 45 del 10/06/2025"
        assert classify_document(text) == DocumentType.DELIBERA

    def test_classify_document_bando(self):
        text = "Bando di gara per lavori pubblici n. 78/2025"
        assert classify_document(text) == DocumentType.BANDO

    def test_classify_event_liquidazione(self):
        text = "Si liquida la somma di € 50.000,00"
        assert classify_event(text, DocumentType.DETERMINA) == EventType.LIQUIDAZIONE

    def test_classify_event_affidamento(self):
        text = "Si affida il servizio di pulizia alla Ditta X"
        assert classify_event(text, DocumentType.DETERMINA) == EventType.AFFIDAMENTO

    def test_route_document(self):
        text = "Determinazione n. 123: si affida il servizio a Ditta Y"
        doc_type, event_type = route_document(text)
        assert doc_type == DocumentType.DETERMINA
        assert event_type == EventType.AFFIDAMENTO

# --- Test per ProcedureBuilder ---
class TestProcedureBuilder:
    def test_link_events_by_cig(self):
        builder = ProcedureBuilder()
        events = [
            AdministrativeEvent(
                event_type=EventType.AFFIDAMENTO,
                cig="Z123456",
                economic_value=50000.0,
            ),
            AdministrativeEvent(
                event_type=EventType.LIQUIDAZIONE,
                cig="Z123456",
                economic_value=50000.0,
            ),
        ]
        procedures = builder.link_events_by_cig(events)
        assert len(procedures) == 1
        assert procedures["CIG_Z123456"].total_amount == 100000.0

    def test_detect_anomalies(self):
        builder = ProcedureBuilder()
        events = [
            AdministrativeEvent(
                event_type=EventType.AFFIDAMENTO,
                cig="Z123456",
                document_date=datetime(2025, 1, 1),
                economic_value=10000.0,
            ),
        ] * 5
        builder.link_events_by_cig(events)
        anomalies = builder.detect_anomalies()
        assert "CIG_Z123456" in anomalies
        assert any("FRAMMENTAZIONE" in a for a in anomalies["CIG_Z123456"])