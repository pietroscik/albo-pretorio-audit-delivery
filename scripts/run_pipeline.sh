#!/bin/bash
set -e

ENTE=${1:-baiano}
BASE_DIR="data/$ENTE/albo_download"

echo "🚀 INIZIO PIPELINE COMPLETA PER L'ENTE: $ENTE 🚀"

echo "--- FASE 1: Estrazione Dati ---"
python run.py analyze --ente "$ENTE" --force --use-llm

echo "--- FASE 2: Report & Intelligence ---"
python run.py build-kg --base "$BASE_DIR"
python run.py analyze-topology --base "$BASE_DIR"
python run.py detect-anomalies --base "$BASE_DIR"
echo "✅ Tutti i report della Fase 2 generati in $BASE_DIR/report!"

echo "--- FASE 3: Addestramento Machine Learning ---"
python run.py train --base "$BASE_DIR"

echo "🎉 Pipeline terminata! Control Room: python run.py control-room"