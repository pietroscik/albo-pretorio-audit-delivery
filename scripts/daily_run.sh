#!/bin/bash
# Script per l'aggiornamento notturno - Versione Windows/Git Bash

# Ottieni la data di ieri (funziona in Git Bash)
YESTERDAY=$(date --date="yesterday" +%Y-%m-%d 2>/dev/null || powershell -Command "(Get-Date).AddDays(-1).ToString('yyyy-MM-dd')")
echo "[$(date +'%Y-%m-%d %H:%M:%S')] Avvio Routine di Audit per la data: $YESTERDAY"

# Lista dei Comuni
COMUNI=("avella" "baiano")

for ENTE in "${COMUNI[@]}"; do
    echo "--- Processando l'Ente: $ENTE ---"

    if [ "$ENTE" == "avella" ]; then
        URL="https://servizi.comune.avella.av.it/openweb/albo/albo_pretorio.php"
    elif [ "$ENTE" == "baiano" ]; then
        URL="https://baiano.soluzionipa.it/openweb/albo/albo_pretorio.php"
    fi

    # 1. Scraper
    py -m delibere_comunali.scraping.new_albo_scraper --ente "$ENTE" --start-url "$URL" --date-from "$YESTERDAY" --date-to "$YESTERDAY" --delay 2.0

    # 2. Pipeline
    py -m delibere_comunali.cli.run_pipeline --ente "$ENTE"
done

echo "[$(date +'%Y-%m-%d %H:%M:%S')] Routine notturna completata per tutta la Costellazione."
