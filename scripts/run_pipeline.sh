#!/bin/bash
set -e

# === DETECT PYTHON COMMAND (Windows/Linux) ===
if command -v py &> /dev/null; then
    PYTHON_CMD="py"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ Python non trovato. Installa Python 3.9+"
    exit 1
fi

# === GET PROJECT ROOT ===
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# === PARAMETRI ===
ENTE=${1:-baiano}
BASE_DIR="$PROJECT_ROOT/data/$ENTE/albo_download"

echo "🚀 INIZIO PIPELINE COMPLETA PER L'ENTE: $ENTE 🚀"

echo "--- FASE 1: Estrazione Dati ---"
$PYTHON_CMD run.py analyze --ente "$ENTE" --force --use-llm

echo "--- FASE 2: Report & Intelligence ---"
$PYTHON_CMD run.py build-kg --base "$BASE_DIR"
$PYTHON_CMD run.py analyze-topology --base "$BASE_DIR"
$PYTHON_CMD run.py detect-anomalies --base "$BASE_DIR"
echo "✅ Tutti i report della Fase 2 generati in $BASE_DIR/report!"

echo "--- FASE 3: Addestramento Machine Learning ---"
$PYTHON_CMD run.py train --base "$BASE_DIR"

echo "🎉 Pipeline terminata! Control Room: $PYTHON_CMD run.py control-room"