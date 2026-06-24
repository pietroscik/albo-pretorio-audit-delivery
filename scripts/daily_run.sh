#!/bin/bash
# Script per l'aggiornamento notturno - Cross-platform

# Ottieni la data di ieri (Windows/Linux)
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    # Git Bash su Windows
    YESTERDAY=$(powershell -Command "(Get-Date).AddDays(-1).ToString('yyyy-MM-dd')")
    DATE_CMD='date +%Y-%m-%d\ %H:%M:%S'
else
    # Linux/Unix
    YESTERDAY=$(date -d "yesterday" +%Y-%m-%d)
    DATE_CMD='date +%Y-%m-%d\ %H:%M:%S'
fi

echo "[`$DATE_CMD`] Avvio Routine di Audit per la data: $YESTERDAY"

COMUNI=("avella" "baiano")

for ENTE in "${COMUNI[@]}"; do
    echo "--- Processando l'Ente: $ENTE ---"

    if [ "$ENTE" == "avella" ]; then
        URL="https://servizi.comune.avella.av.it/openweb/albo/albo_pretorio.php"
    elif [ "$ENTE" == "baiano" ]; then
        URL="https://baiano.soluzionipa.it/openweb/albo/albo_pretorio.php"
    fi

    # Usa run.py per tutto
    python run.py scrape --ente "$ENTE" --start-url "$URL" --date-from "$YESTERDAY" --date-to "$YESTERDAY" --delay 2.0
    python run.py pipeline --ente "$ENTE"
done

echo "[`$DATE_CMD`] Routine notturna completata."