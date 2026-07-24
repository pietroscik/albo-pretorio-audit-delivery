# Esempi di Utilizzo del Sistema
## Panoramica

Questa guida mostra come utilizzare il sistema per eseguire audit e analisi sugli albi pretori comunali, con particolare attenzione ai comandi ufficialmente supportati.

## Modalità Enterprise (Consigliata)

### Esecuzione Completa (Scraping + Analisi)
```bash
# Esempio con il Comune di Sperone
python run.py enterprise --ente sperone --workflow full

# Esempio con un altro comune
python run.py enterprise --ente avella --workflow full
```

### Solo Fase di Scraping
```bash
# Solo raccolta dati e download documenti
python run.py enterprise --ente sperone --workflow scrape-only
```

### Solo Fase di Analisi
```bash
# Solo analisi dei dati già scaricati
python run.py enterprise --ente sperone --workflow analyze-only
```

## Utilizzo Diretto dei Moduli (Per Debugging)

### Solo Scraping
```bash
# Esegui solo lo scraper per un ente specifico
python -m src.delibere_comunali.scraping.new_albo_scraper --ente sperone --max-pages 5 --delay 2

# Esegui senza scaricare documenti (solo metadati)
python -m src.delibere_comunali.scraping.new_albo_scraper --ente sperone --max-pages 5 --no-download
```

### Solo Analisi
```bash
# Esegui solo l'analisi sui dati esistenti
python -m src.delibere_comunali.parsing.analyze_albo --ente sperone
```

### Costruzione del Knowledge Graph
```bash
# Genera il grafo della conoscenza per un ente
python run.py build-kg --ente sperone
```

### Training del Modello di Classificazione
```bash
# Training del modello di classificazione
python run.py train-classifier --ente=baiano

# Training supervisionato
python run.py supervised-training --ente=baiano
```

### Post-Elaborazione Classificazioni
```bash
# Post-process delle classificazioni OCR
python run.py post-process-classification --input=data/input.csv --output=data/output.csv
```

## Esempi Specifici per Halleyweb/AgID

### Comune di Sperone (Nuova Infrastruttura Halleyweb)
```bash
# Esecuzione completa
python run.py enterprise --ente sperone --workflow full

# Solo scraping (utilizza Playwright per gestire JavaScript)
python run.py enterprise --ente sperone --workflow scrape-only

# Dettagli avanzati per Halleyweb
python -m src.delibere_comunali.scraping.new_albo_scraper --ente sperone --max-pages 1 --delay 2
```

## Parametri Comuni

### Controllo del Numero di Pagine
```bash
# Limita lo scraping a un certo numero di pagine
python run.py enterprise --ente sperone --workflow scrape-only --max-pages 3
```

### Controllo del Rate Limit
```bash
# Imposta ritardo tra le richieste per essere più gentili col server
python -m src.delibere_comunali.scraping.new_albo_scraper --ente sperone --delay 3
```

### KPI di Gestione
```bash
# Calcolo KPI di gestione
python run.py management-kpi --ente=baiano
```

### Analisi Attuariale
```bash
# Esecuzione analisi attuariale
python run.py actuarial-analysis --ente=baiano
```

## Esempi di Output Attesi

Dopo un'esecuzione completa, dovrebbero essere presenti i seguenti file:

### In `data/{ente}/albo_download/`:
- `albo_metadati.csv` - Metadati estratti dagli atti
- `allegati_parsed.csv` - Allegati strutturati
- `pdf/` - Documenti PDF scaricati
- `report/` - Report di analisi
- `texts/` - Testi estratti dai documenti

### File Globali:
- `data/report_globali/alert_antifrode.md` - Alert antifrode aggregati
- `knowledge_graph/knowledge_graph.gexf` - Grafo della conoscenza
- `executive_summary.md` - Sommario esecutivo

## Comandi di Utilità

### Controllo Stato
```bash
# Controlla lo stato di un ente
python run.py status --ente sperone
```

### Validazione
```bash
# Valida l'output generato
python run.py validate --ente sperone
```

### Esplorazione Dati
```bash
# Esplora i dati disponibili
python run.py explore --ente sperone
```

## Note di Utilizzo

1. **Prima esecuzione**: Per un nuovo ente, iniziare sempre con `--workflow scrape-only` per raccogliere i dati.

2. **Esecuzioni successive**: Usare `--workflow analyze-only` per rieseguire l'analisi sui dati esistenti senza nuovo scraping.

3. **Halleyweb**: I siti basati su Halleyweb (come Sperone) richiedono Playwright e potrebbero impiegare più tempo per l'elaborazione.

4. **Supporto P7M**: I file firmati digitalmente (.p7m) vengono automaticamente estratti al contenuto PDF.

5. **Conformità AgID**: Il sistema è conforme agli standard AgID e gestisce correttamente i nuovi siti basati su Bootstrap Italia.

## Workflow Enterprise Opzioni

Il comando `enterprise` supporta diverse opzioni di workflow:
- `--workflow=full` (predefinito): Esegue tutti i moduli disponibili
- `--workflow=analyze-only`: Esegue solo l'analisi senza scraping
- `--workflow=scrape-only`: Esegue solo lo scraping senza analisi

## Opzioni Comuni

Molti comandi accettano le seguenti opzioni comuni:

- `--ente`: Nome dell'ente locale (obbligatorio per la maggior parte dei comandi)
- `--base`: Directory base per i dati (default: data/{ente}/albo_download)
- `--use-llm`: Abilita l'arricchimento con LLM
- `--llm-provider`: Provider LLM da utilizzare (openai, gemini, mistral, ecc.)
- `--llm-model`: Modello LLM specifico da utilizzare
- `--force`: Forza l'esecuzione anche se i risultati sono già presenti

## Risoluzione Problemi Comuni

### Comando non trovato
Se ricevi un messaggio "comando non trovato", assicurati di:
1. Essere nella directory principale del progetto
2. Avere installato tutte le dipendenze
3. Usare il nome corretto del comando (controlla con `python run.py --help`)

### Errori di permessi
Se ricevi errori di permessi durante l'esecuzione:
1. Controlla di avere i permessi di lettura/scrittura sulla directory `data/`
2. Verifica che il processo abbia accesso ai file di configurazione

### Porta già in uso
Se ricevi errori relativi a porte già in uso (es. 8501 per la dashboard):
1. Chiudi eventuali istanze precedenti dell'applicazione
2. Usa un'altra porta se disponibile