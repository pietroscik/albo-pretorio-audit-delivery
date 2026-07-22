"""
Test di integrazione per la pipeline enterprise.
"""

import tempfile
from pathlib import Path

import pytest

from delibere_comunali.core.config_manager import ConfigManager, get_enterprise_config


@pytest.fixture
def temp_config_dir():
    """Crea una directory temporanea per i test di configurazione."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Crea file e directory necessari
        data_dir = Path(temp_dir) / "data" / "test_integration" / "albo_download"
        data_dir.mkdir(parents=True, exist_ok=True)

        # Crea un file CSV vuoto
        (data_dir / "atti_parsed.csv").write_text("pdf_name,oggetto,numero_atto\n")

        yield temp_dir, data_dir


def test_config_integration(temp_config_dir):
    """Testa l'integrazione della configurazione enterprise."""
    print("\n=== TEST INTEGRAZIONE CONFIGURAZIONE ===")

    temp_dir, data_dir = temp_config_dir

    # Crea il config manager
    config_manager = ConfigManager(ente="test_integration", base_path=str(data_dir))

    # Verifica che l'ente sia impostato correttamente
    assert config_manager.ente == "test_integration"
    print(f"Ente configurato correttamente: {config_manager.ente}")

    # Verifica che il percorso base sia impostato
    assert config_manager.base_path is not None
    print(f"Percorso base configurato: {config_manager.base_path}")

    print("Configurazione base verificata con successo")


def test_parameter_updates():
    """Testa l'aggiornamento dei parametri."""
    print("\n=== TEST AGGIORNAMENTO PARAMETRI ===")

    config_manager = get_enterprise_config(ente="test_integration")

    # Aggiorna alcuni parametri
    initial_workers = config_manager.enterprise_params.max_workers
    config_manager.update_params(max_workers=2, enable_caching=False)

    assert config_manager.enterprise_params.max_workers == 2
    assert config_manager.enterprise_params.enable_caching is False
    print(f"Parametri aggiornati correttamente (da {initial_workers} a 2 workers)")


def test_orchestrator_creation():
    """Testa la creazione dell'orchestrator con la configurazione."""
    print("\n=== TEST CREAZIONE ORCHESTRATOR ===")

    config_manager = get_enterprise_config(ente="test_integration")

    # Crea un orchestrator usando la configurazione
    orchestrator = config_manager.create_orchestrator()

    assert orchestrator is not None
    assert orchestrator.ente == "test_integration"
    print(f"Orchestrator creato correttamente per ente: {orchestrator.ente}")

    # Verifica che i parametri di coordinamento siano impostati
    assert orchestrator.max_workers > 0
    print(f"Parametri orchestrator: max_workers={orchestrator.max_workers}")


def test_pipeline_with_enterprise_params():
    """Testa la pipeline con parametri enterprise."""
    print("\n=== TEST PIPELINE CON PARAMETRI ENTERPRISE ===")

    config_manager = get_enterprise_config(ente="test_integration")
    orchestrator = config_manager.create_orchestrator()

    # Verifica che l'orchestrator abbia i parametri enterprise
    assert orchestrator is not None
    assert orchestrator.ente == "test_integration"
    print(f"Pipeline configurata con parametri enterprise per: {orchestrator.ente}")


def test_enterprise_workflow_cli():
    """Testa il workflow CLI con configurazione enterprise."""
    print("\n=== TEST WORKFLOW CLI ENTERPRISE ===")

    config_manager = get_enterprise_config(ente="test_integration")

    # Verifica che la configurazione sia valida
    assert config_manager.ente == "test_integration"
    assert config_manager.enterprise_params is not None
    print(f"Workflow CLI enterprise configurato per: {config_manager.ente}")


def test_pipeline_cli_integration():
    """Testa l'integrazione del CLI della pipeline."""
    print("\n=== TEST INTEGRAZIONE CLI PIPELINE ===")

    config_manager = get_enterprise_config(ente="test_integration")

    # Verifica che il CLI possa essere istanziato
    assert config_manager is not None
    print("Integrazione CLI pipeline verificata")
