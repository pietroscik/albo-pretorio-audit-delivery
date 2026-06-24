#!/bin/bash
set -e

# Usa il wrapper universale
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

ENTE=${1:-baiano}
BASE_DIR="$PROJECT_ROOT/data/$ENTE/albo_download"

echo "🚀 INIZIO PIPELINE COMPLETA PER L'ENTE: $ENTE 🚀"

echo "--- FASE 1: Estrazione Dati ---"
py run.py analyze --ente "$ENTE" --force --use-llm

echo "--- FASE 2: Report & Intelligence ---"
py run.py build-kg --base "$BASE_DIR"
py run.py analyze-topology --base "$BASE_DIR"
py run.py detect-anomalies --base "$BASE_DIR"
echo "✅ Tutti i report della Fase 2 generati in $BASE_DIR/report!"

echo "--- FASE 3: Addestramento Machine Learning ---"
py run.py train --base "$BASE_DIR"

echo "🎉 Pipeline terminata! Control Room: py run.py control-room"