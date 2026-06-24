#!/bin/bash
# Script per l'aggiornamento notturno - Cross-platform

# === DETECT PYTHON COMMAND ===
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

# === GET YESTERDAY'S DATE (Cross-platform) ===
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    # Git Bash su Windows
    YESTERDAY=$(powershell -Command "(Get-Date).AddDays(-1).ToString('yyyy-MM-dd')")
else
    # Linux/Unix
    YESTERDAY=$(date -d "yesterday" +%Y-%m-%d)
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Avvio Routine di Audit per la data: $YESTERDAY"

COMUNI=("avella" "baiano")

for ENTE in "${COMUNI[@]}"; do
    echo "--- Processando l'Ente: $ENTE ---"

    if [ "$ENTE" == "avella" ]; then
        URL="https://servizi.comune.avella.av.it/openweb/albo/albo_pretorio.php"
    elif [ "$ENTE" == "baiano" ]; then
        URL="https://baiano.soluzionipa.it/openweb/albo/albo_pretorio.php"
    fi

    # Usa run.py per tutto
    $PYTHON_CMD run.py scrape --ente "$ENTE" --start-url "$URL" --date-from "$YESTERDAY" --date-to "$YESTERDAY" --delay 2.0
    $PYTHON_CMD run.py pipeline --ente "$ENTE"
done

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Routine notturna completata."