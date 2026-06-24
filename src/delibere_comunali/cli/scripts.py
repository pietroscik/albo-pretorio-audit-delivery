"""Wrapper per script legacy in scripts/ - Permette di esporli come entry point."""

import subprocess
import sys
from pathlib import Path

# Path alla root del progetto
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent

def build_kg_main():
    """Wrapper per scripts/build_knowledge_graph.py"""
    sys.argv[0] = "build_knowledge_graph.py"
    exec(open(PROJECT_ROOT / "scripts" / "build_knowledge_graph.py").read())

def analyze_topology_main():
    """Wrapper per scripts/analyze_topology.py"""
    sys.argv[0] = "analyze_topology.py"
    exec(open(PROJECT_ROOT / "scripts" / "analyze_topology.py").read())

def detect_anomalies_main():
    """Wrapper per scripts/detect_anomalies.py"""
    sys.argv[0] = "detect_anomalies.py"
    exec(open(PROJECT_ROOT / "scripts" / "detect_anomalies.py").read())

def train_model_main():
    """Wrapper per scripts/train_model.py"""
    sys.argv[0] = "train_model.py"
    exec(open(PROJECT_ROOT / "scripts" / "train_model.py").read())

def validate_output_main():
    """Wrapper per scripts/validate_output.py"""
    sys.argv[0] = "validate_output.py"
    exec(open(PROJECT_ROOT / "scripts" / "validate_output.py").read())

def validate_csv_main():
    """Wrapper per scripts/validate_csv_schema.py"""
    sys.argv[0] = "validate_csv_schema.py"
    exec(open(PROJECT_ROOT / "scripts" / "validate_csv_schema.py").read())

def export_linked_data_main():
    """Wrapper per scripts/export_linked_data.py"""
    sys.argv[0] = "export_linked_data.py"
    exec(open(PROJECT_ROOT / "scripts" / "export_linked_data.py").read())

def clean_texts_main():
    """Wrapper per scripts/clean_texts.py"""
    sys.argv[0] = "clean_texts.py"
    exec(open(PROJECT_ROOT / "scripts" / "clean_texts.py").read())

def sync_texts_main():
    """Wrapper per scripts/sync_texts.py"""
    sys.argv[0] = "sync_texts.py"
    exec(open(PROJECT_ROOT / "scripts" / "sync_texts.py").read())

def generate_groundtruth_main():
    """Wrapper per scripts/generate_ground_truth.py"""
    sys.argv[0] = "generate_ground_truth.py"
    exec(open(PROJECT_ROOT / "scripts" / "generate_ground_truth.py").read())

def visualize_graph_main():
    """Wrapper per scripts/visualizza_grafo.py"""
    sys.argv[0] = "visualizza_grafo.py"
    exec(open(PROJECT_ROOT / "scripts" / "visualizza_grafo.py").read())