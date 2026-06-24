#!/bin/bash
set -e

ENTE=${1:-baiano}
BASE_DIR="data/$ENTE/albo_download"

echo "🚀 INIZIO PIPELINE COMPLETA PER L'ENTE: $ENTE 🚀"

echo "--- FASE 1: Estrazione Dati ---"
python -m delibere_comunali.parsing.analyze_albo --ente "$ENTE" --force --use-llm

echo "--- FASE 2: Report & Intelligence ---"
python scripts/build_knowledge_graph.py --base "$BASE_DIR"
python scripts/analyze_topology.py --base "$BASE_DIR"
python scripts/detect_anomalies.py --base "$BASE_DIR"
echo "✅ Tutti i report della Fase 2 sono stati generati con successo in $BASE_DIR/report!"

echo "--- FASE 3: Addestramento Machine Learning ---"
python scripts/train_model.py --base "$BASE_DIR"

echo "🎉 Pipeline terminata con successo! Ora puoi avviare la Control Room con: streamlit run -m delibere_comunali.cli.app_control_room"