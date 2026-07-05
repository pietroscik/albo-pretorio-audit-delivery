"""Wrapper per script legacy in scripts/ - Permette di esporli come entry point."""

import os
import runpy
import sys
from pathlib import Path

def get_project_root() -> Path:
    """Ritorna la root del progetto in modo robusto."""
    # Partiamo dal file corrente
    current = Path(__file__).resolve()

    # Risaliamo fino a trovare pyproject.toml (root marker)
    for _ in range(6):  # Max 6 livelli su
        if (current / "pyproject.toml").exists():
            return current
        current = current.parent

    # Fallback: risaliamo 5 livelli (scripts.py -> cli -> delibere_comunali -> src -> project)
    return Path(__file__).resolve().parent.parent.parent.parent.parent

PROJECT_ROOT = get_project_root()

def _run_legacy(script_name: str, module_fallback: str | None = None):
    script_path = PROJECT_ROOT / "scripts" / script_name
    if script_path.exists():
        sys.argv[0] = script_name
        runpy.run_path(str(script_path), run_name="__main__")
        return
    if module_fallback:
        print(f"⚠️  Script {script_name} non trovato, uso modulo: {module_fallback}")
        runpy.run_module(module_fallback, run_name="__main__")
        return
    raise FileNotFoundError(
        f"❌ Script non trovato: {script_path}\n"
        f"   Assicurati che la cartella scripts/ sia presente nella root del progetto."
    )

def build_kg_main():
    _run_legacy("build_knowledge_graph.py", "delibere_comunali.cli.run_pipeline")

def detect_anomalies_main():
    _run_legacy("detect_anomalies.py")

def export_linked_data_main():
    _run_legacy("export_linked_data.py")

def analyze_topology_main():
    _run_legacy("analyze_topology.py")

def train_model_main():
    _run_legacy("train_model.py")

def validate_output_main():
    _run_legacy("validate_output.py")

def validate_csv_main():
    _run_legacy("validate_output.py")
    
def clean_texts_main():
    _run_legacy("clean_texts.py")

def sync_texts_main():
    _run_legacy("sync_texts.py")

def generate_groundtruth_main():
    _run_legacy("generate_ground_truth.py")

def visualize_graph_main():
    _run_legacy("visualizza_grafo.py")