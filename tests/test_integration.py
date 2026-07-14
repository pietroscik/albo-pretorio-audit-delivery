"""
Test di integrazione per la pipeline completa di Albo Pretorio Audit Delivery
"""
import pytest
import tempfile
import os
from pathlib import Path
import sys

# Aggiunge il percorso src per permettere l'import
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import corretto della funzione da run_pipeline
from delibere_comunali.cli.run_pipeline import resolve_base_path
from delibere_comunali.core.config_manager import ConfigManager
from delibere_comunali.core.enterprise_orchestration import EnterpriseOrchestrator


def test_resolve_base_path_integration():
    """Test della funzione resolve_base_path"""
    # Crea un ambiente temporaneo per il test
    with tempfile.TemporaryDirectory() as temp_dir:
        # Crea una struttura di directory di test
        test_path = Path(temp_dir) / "test_ente" / "albo_download"
        test_path.mkdir(parents=True)
        
        # Crea un file fittizio per far pensare che esista la struttura
        (test_path / "albo_metadati.csv").touch()
        
        # Test della funzione
        result = resolve_base_path(str(test_path), "test_ente")
        assert result == str(test_path)


def test_config_manager_integration():
    """Test del ConfigManager"""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_manager = ConfigManager(ente="test_comune", base_path=temp_dir)
        
        # Verifica che la configurazione sia stata creata correttamente
        assert config_manager.ente == "test_comune"
        assert config_manager.base_path == temp_dir
        
        # Verifica che i parametri enterprise siano accessibili come attributo
        params = config_manager.enterprise_params
        assert "ente" in str(params)
        assert "base_path" in str(params)


def test_enterprise_orchestrator_integration():
    """Test dell'EnterpriseOrchestrator"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Crea un orchestrator con configurazione minima (senza parametri opzionali non esistenti)
        orchestrator = EnterpriseOrchestrator(
            ente="test_comune",
            base_path=temp_dir
        )
        
        # Verifica che sia stato creato correttamente
        assert orchestrator.ente == "test_comune"
        assert orchestrator.base_path == temp_dir


def test_pipeline_with_enterprise_params():
    """Test dell'integrazione tra pipeline e parametri enterprise"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Crea una configurazione enterprise
        config_manager = ConfigManager(
            ente="test_comune",
            base_path=temp_dir
        )
        
        # Ottieni i parametri enterprise come attributo
        enterprise_params = config_manager.enterprise_params
        
        # Verifica che i parametri siano conformi alle aspettative
        assert enterprise_params.ente == "test_comune"
        assert enterprise_params.base_path == temp_dir
        assert hasattr(enterprise_params, 'enable_coordination')


if __name__ == "__main__":
    # Permette l'esecuzione diretta dello script per testing
    pytest.main([__file__, "-v"])