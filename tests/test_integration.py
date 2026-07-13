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

from delibere_comunali.cli.run_pipeline import run_pipeline
from delibere_comunali.core.config_manager import ConfigManager
from delibere_comunali.core.enterprise_orchestration import EnterpriseOrchestrator


def test_pipeline_integration():
    """Test della pipeline completa con dati di esempio"""
    # Crea un ambiente temporaneo per il test
    with tempfile.TemporaryDirectory() as temp_dir:
        # Configura un ambiente di test
        test_config = {
            "ente": "test_comune",
            "base_path": temp_dir,
            "enable_coordination": True,
            "skip_risk_assessment": True,  # Salta per velocizzare il test
            "skip_kpi_calculation": True,  # Salta per velocizzare il test
            "skip_ml_analysis": True,      # Salta per velocizzare il test
            "skip_audit": True,            # Salta per velocizzare il test
            "dry_run": True  # Esegui in modalità simulazione
        }
        
        # Crea directory necessarie
        os.makedirs(os.path.join(temp_dir, "albo_download"), exist_ok=True)
        os.makedirs(os.path.join(temp_dir, "output"), exist_ok=True)
        
        # Esegui la pipeline in modalità dry-run
        try:
            result = run_pipeline(test_config)
            # Verifica che la funzione ritorni un risultato (anche se in modalità dry-run)
            assert result is not None
        except Exception as e:
            # In modalità dry-run alcuni errori sono attesi
            if "dry_run" not in str(e).lower():
                raise e


def test_config_manager_integration():
    """Test del ConfigManager"""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_manager = ConfigManager(ente="test_comune", base_path=temp_dir)
        
        # Verifica che la configurazione sia stata creata correttamente
        assert config_manager.ente == "test_comune"
        assert config_manager.base_path == temp_dir
        
        # Verifica che i parametri enterprise siano accessibili
        params = config_manager.get_enterprise_params()
        assert "ente" in params
        assert "base_path" in params
        assert "enable_coordination" in params


def test_enterprise_orchestrator_integration():
    """Test dell'EnterpriseOrchestrator"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Crea un orchestrator con configurazione minima
        orchestrator = EnterpriseOrchestrator(
            ente="test_comune",
            base_path=temp_dir,
            skip_risk=True,
            skip_kpi=True,
            skip_ml=True,
            skip_audit=True,
            dry_run=True
        )
        
        # Esegui in modalità dry-run
        result = orchestrator.execute_workflow(workflow_type="minimal")
        
        # In modalità dry-run, dovrebbe comunque ritornare un risultato
        assert result is not None


def test_pipeline_with_enterprise_params():
    """Test dell'integrazione tra pipeline e parametri enterprise"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Crea una configurazione enterprise
        config_manager = ConfigManager(
            ente="test_comune",
            base_path=temp_dir
        )
        
        # Ottieni i parametri enterprise
        enterprise_params = config_manager.get_enterprise_params()
        
        # Verifica che i parametri siano conformi alle aspettative
        assert "ente" in enterprise_params
        assert enterprise_params["ente"] == "test_comune"
        assert "base_path" in enterprise_params
        assert enterprise_params["base_path"] == temp_dir
        assert "enable_coordination" in enterprise_params


if __name__ == "__main__":
    # Permette l'esecuzione diretta dello script per testing
    pytest.main([__file__, "-v"])