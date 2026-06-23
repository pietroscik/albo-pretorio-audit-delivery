#!/bin/bash
# Script per l'aggiornamento notturno della Piattaforma RegTech

cd /home/pietroscik/albo-pretorio-audit-delivery
source .venv/bin/activate

YESTERDAY=$(date -d "yesterday" '+%Y-%m-%d')
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Avvio Routine di Audit per la data: $YESTERDAY"

# Lista dei Comuni attivati nella piattaforma
COMUNI=("avella" "baiano")

for ENTE in "${COMUNI[@]}"; do
    echo "--- Processando l'Ente: $ENTE ---"
    
    # Costruiamo dinamicamente l'URL Corrente (NON lo storico)
    if [ "$ENTE" == "avella" ]; then
        URL="https://servizi.comune.avella.av.it/openweb/albo/albo_pretorio.php"
    elif [ "$ENTE" == "baiano" ]; then
        URL="https://baiano.soluzionipa.it/openweb/albo/albo_pretorio.php"
    fi
    
    # 1. Scraper Leggero (Solo sull'Albo Corrente per il delta di ieri)
    python new_albo_scraper.py --ente "$ENTE" --start-url "$URL" --date-from "$YESTERDAY" --date-to "$YESTERDAY" --delay 2.0
    
    # 2. Pipeline XAI (Usa il global_rf_model.joblib)
    python run_pipeline.py --ente "$ENTE"
done

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Routine notturna completata per tutta la Costellazione."
