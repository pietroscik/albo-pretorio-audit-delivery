#!/bin/bash

# Script per l'esecuzione completa della pipeline di analisi albo pretorio
# Questo script coordina l'esecuzione di tutti i moduli del sistema

set -e  # Ferma lo script se si verifica un errore

echo "🚀 Avvio della pipeline di analisi albo pretorio"

# Verifica che il parametro ente sia stato fornito
if [ $# -eq 0 ]; then
    echo "❌ Errore: Specificare il nome dell'ente come parametro"
    echo "Esempio: $0 baiano"
    exit 1
fi

ENTE=$1
echo "🏢 Ente selezionato: $ENTE"

# Directory base per i dati
DATA_DIR="data/$ENTE"
ALBO_DOWNLOAD="$DATA_DIR/albo_download"

# Crea le directory necessarie se non esistono
mkdir -p "$DATA_DIR"
mkdir -p "$ALBO_DOWNLOAD"

echo "💾 Directory dati pronta in: $DATA_DIR"

# Passaggio 1: Estrazione dati (se necessario)
echo "🔍 Passaggio 1: Estrazione dati"
if command -v python &> /dev/null; then
    echo "Esecuzione scraping per l'ente: $ENTE"
    python -c "
import sys
sys.path.insert(0, '.')
from delibere_comunali.scraping.new_albo_scraper import main
import argparse

# Simula argomenti da linea di comando
class Args:
    pass

args = Args()
args.ente = '$ENTE'
args.base = '$ALBO_DOWNLOAD'
args.start_url = None
args.out = None
args.max_pages = 10
args.delay = 1.0
args.timeout = 30
args.user_agent = 'Mozilla/5.0 (compatible; AlboPretorioBot/1.0)'
args.page_from = 0
args.page_to = 5
args.page_step = 1
args.only_types = None
args.exclude_types = None
args.date_from = None
args.date_to = None
args.title_regex = None
args.no_download = False
args.max_attachments_per_item = 5
args.save_html = False

main(args)
"
else
    echo "⚠️ Python non trovato, saltando scraping"
fi

# Passaggio 2: Parsing e analisi documenti
echo "📝 Passaggio 2: Parsing e analisi documenti"
if command -v python &> /dev/null; then
    echo "Esecuzione analisi per l'ente: $ENTE"
    python run.py analyze --ente="$ENTE" || echo "⚠️ Errore nell'analisi, continuando comunque..."
else
    echo "⚠️ Python non trovato, saltando analisi"
fi

# Passaggio 3: Costruzione del knowledge graph
echo "🌐 Passaggio 3: Costruzione knowledge graph"
if command -v python &> /dev/null; then
    python run.py build-kg --ente="$ENTE" || echo "⚠️ Errore nella costruzione del KG, continuando comunque..."
else
    echo "⚠️ Python non trovato, saltando knowledge graph"
fi

# Passaggio 4: Analisi del rischio
echo "⚠️ Passaggio 4: Analisi del rischio"
if command -v python &> /dev/null; then
    python run.py risk-assessment --ente="$ENTE" || echo "⚠️ Errore nell'analisi del rischio, continuando comunque..."
else
    echo "⚠️ Python non trovato, saltando analisi del rischio"
fi

# Passaggio 5: Calcolo KPI
echo "📊 Passaggio 5: Calcolo KPI di gestione"
if command -v python &> /dev/null; then
    python run.py management-kpi --ente="$ENTE" || echo "⚠️ Errore nel calcolo KPI, continuando comunque..."
else
    echo "⚠️ Python non trovato, saltando calcolo KPI"
fi

# Passaggio 6: Audit antifrode
echo "🔍 Passaggio 6: Audit antifrode"
if command -v python &> /dev/null; then
    python run.py audit --ente="$ENTE" || echo "⚠️ Errore nell'audit, continuando comunque..."
else
    echo "⚠️ Python non trovato, saltando audit"
fi

# Passaggio 7: Validazione output
echo "✅ Passaggio 7: Validazione output"
if command -v python &> /dev/null; then
    python run.py validate-output --ente="$ENTE" || echo "⚠️ Errore nella validazione output, continuando comunque..."
else
    echo "⚠️ Python non trovato, saltando validazione"
fi

# Passaggio 8: Post-process classificazioni
echo "🔄 Passaggio 8: Post-process classificazioni"
if command -v python &> /dev/null; then
    # Cerca i file CSV generati e applica il post-process se esistono
    INPUT_CSV="$ALBO_DOWNLOAD/allegati_parsed.csv"
    OUTPUT_CSV="$ALBO_DOWNLOAD/allegati_post_processed.csv"
    
    if [ -f "$INPUT_CSV" ]; then
        python run.py post-process-classification --input="$INPUT_CSV" --output="$OUTPUT_CSV" || echo "⚠️ Errore nel post-process, continuando comunque..."
    else
        echo "⚠️ File CSV di input non trovato: $INPUT_CSV"
    fi
else
    echo "⚠️ Python non trovato, saltando post-process"
fi

# Passaggio 9: Generazione report
echo "📄 Passaggio 9: Generazione report"
if command -v python &> /dev/null; then
    python run.py privacy-report --ente="$ENTE" || echo "⚠️ Errore nella generazione del report privacy, continuando comunque..."
else
    echo "⚠️ Python non trovato, saltando generazione report"
fi

echo "🎉 Pipeline completata per l'ente: $ENTE"
echo "📊 I risultati sono disponibili in: $DATA_DIR"
echo "📈 I report sono stati generati in: $DATA_DIR/reports/"

# Opzionale: Avviso per avviare la dashboard
echo ""
echo "💡 Suggerimento: Avvia la dashboard con 'python run.py control-room' per visualizzare i risultati"