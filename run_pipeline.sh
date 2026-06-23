#!/bin/bash
set -e # Esce immediatamente se un comando fallisce.

ENTE=${1:-baiano}
BASE_DIR="data/$ENTE/albo_download"

echo "🚀 INIZIO PIPELINE COMPLETA PER L'ENTE: $ENTE 🚀"

echo "--- FASE 1: Estrazione Dati ---"
# L'opzione --force è cruciale per ri-analizzare tutti i documenti con la logica di estrazione aggiornata
python analyze_albo.py --ente "$ENTE" --force --use-llm

echo "--- FASE 2: Report & Intelligence ---"
python build_knowledge_graph.py --base "$BASE_DIR"
python analyze_topology.py --base "$BASE_DIR"
python detect_anomalies.py --base "$BASE_DIR"
echo "✅ Tutti i report della Fase 2 sono stati generati con successo in $BASE_DIR/report!"

echo "--- FASE 3: Addestramento Machine Learning ---"
python train_model.py --base "$BASE_DIR"

echo "🎉 Pipeline terminata con successo! Ora puoi avviare la Control Room con: streamlit run app_control_room.py"