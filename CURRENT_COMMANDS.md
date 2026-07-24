# Comandi Attualmente Disponibili

## Interfaccia Moderna (Click-based)

### Comandi Principali
- `python run.py enterprise` - Esegue il workflow enterprise per un ente specifico
  - Opzioni: `--ente` (obbligatorio), `--workflow` (full, analyze-only, scrape-only), `--config`
- `python run.py audit` - Esegue l'audit antifrode sugli atti comunali
  - Opzioni: `--base`, `--ente`, `--use-llm`, `--llm-provider`, `--llm-model`
- `python run.py build-kg` - Costruisce il knowledge graph relazionale
  - Opzioni: `--base`, `--ente`
- `python run.py post-process-classification` - Applica post-elaborazione alle classificazioni dei documenti con OCR
  - Opzioni: `--input` (obbligatorio), `--output` (obbligatorio)
- `python run.py analyze-topology` - Analizza la topologia del knowledge graph
  - Opzioni: `--base`, `--ente`
- `python run.py supervised-training` - Esegue il riaddestramento supervisionato con feedback umano
  - Opzioni: `--base`, `--ente`
- `python run.py train-classifier` - Addestra il modello di classificazione con ottimizzazione degli iperparametri
  - Opzioni: `--ente` (obbligatorio)
- `python run.py metrics-exporter` - Avvia il server per l'esportazione delle metriche e il monitoraggio
  - Nessuna opzione richiesta

### Comandi di Sicurezza e Privacy
- `python run.py gdpr-delete` - Implementa il diritto all'oblio (GDPR Art. 17)
  - Opzioni: `--user-identifier` (obbligatorio), `--data-path`
- `python run.py privacy-report` - Genera un report di conformità GDPR per un ente specifico
  - Opzioni: `--ente` (obbligatorio)

### Interfaccia Utente
- `python run.py control-room` - Avvia la dashboard di controllo (Streamlit app)
- `python run.py dashboard` - Alias per avviare la dashboard di controllo
- `python run.py ui` - Alias per avviare l'interfaccia utente

## Sistema Legacy (Compatibilità)

I seguenti comandi sono disponibili attraverso il sistema di mapping legacy e possono essere eseguiti come `python run.py <comando>`:

### Comandi Principali
- `scrape` - Estrazione dati dall'albo pretorio
- `analyze` - Analisi e parsing dei documenti
- `pipeline` - Esecuzione della pipeline completa
- `validate-csv` - Validazione dei file CSV prodotti

### Comandi Enterprise
- `orchestrate` - Esecuzione della pipeline completa di coordinamento
- `data-coord` - Interfaccia per il coordinatore dati centralizzato
- `config-mgmt` - Gestione della configurazione enterprise

### Comandi ML e Analytics
- `risk-assessment` - Esecuzione dell'analisi del rischio
- `management-kpi` - Calcolo dei KPI di gestione
- `actuarial-analysis` - Analisi attuariale e provisioning

### Comandi UI e RAG
- `rag` - Interfaccia RAG per ricerca semantica
- `apply-corrections` - Applicazione delle correzioni manuali

### Comandi di Utilità
- `detect-anomalies` - Rilevamento anomalie
- `export-linkeddata` - Esportazione linked data
- `validate-output` - Validazione output
- `clean-texts` - Pulizia testi
- `sync-texts` - Sincronizzazione testi
- `generate-groundtruth` - Generazione ground truth
- `visualize-graph` - Visualizzazione grafo
- `explore` - Esplorazione albo
- `reconcile` - Riconciliazione semantica
- `validate-fase0` - Validazione fase 0
- `validate-ground` - Validazione ground truth
- `verify-output` - Verifica output
- `update-preview` - Aggiornamento anteprima
- `finance-validate` - Validazione finanziaria
- `random-forest` - Modello Random Forest
- `train` - Training del modello ML
- `run-pipeline` - Esecuzione della pipeline (alternativa a pipeline)
- `scraper` - Alternativa allo scraping

## Utilizzo Tipico

### Pipeline Completa
```bash
# Modalità moderna (consigliata)
python run.py enterprise --ente=baiano --workflow=full

# Modalità legacy
python run.py pipeline --ente=baiano
```

### Dashboard
```bash
# Modalità moderna (consigliata)
python run.py control-room

# Modalità legacy
python run.py control-room
```

### Singolo Modulo
```bash
# Eseguire solo l'audit
python run.py audit --ente=baiano

# Eseguire solo la costruzione del knowledge graph
python run.py build-kg --ente=baiano
```

## Note Importanti

1. **I comandi moderni sono preferiti** rispetto ai comandi legacy per le nuove implementazioni
2. **Entrambi i sistemi sono attivi** e funzionanti contemporaneamente
3. **La retrocompatibilità è mantenuta** per gli script esistenti
4. **I comandi legacy richiedono** spesso parametri specifici diversi dai comandi moderni
5. **Il comando enterprise** supporta workflow opzioni: `full`, `analyze-only`, `scrape-only`
6. **I comandi legacy disponibili** sono: actuarial-analysis, analyze, analyze-topology, apply-corrections, build-kg, clean-texts, config-mgmt, dashboard, data-coord, detect-anomalies, enterprise, explore, export-linkeddata, finance-validate, generate-groundtruth, management-kpi, orchestrate, pipeline, post-process-classification, rag, random-forest, reconcile, risk-assessment, run-pipeline, scrape, scraper, sync-texts, train, update-preview, validate-csv, validate-fase0, validate-ground, validate-output, verify-output, visualize-graph