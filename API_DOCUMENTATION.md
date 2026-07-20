# Documentazione API - Albo Pretorio Audit Delivery

## Struttura del Sistema

Il sistema dispone di due interfacce principali:

1. **CLI Moderna (Click-based)** - Interfaccia principale consigliata
2. **Sistema Legacy** - Per compatibilità con versioni precedenti

## CLI Moderna (Click-based)

La CLI moderna è accessibile tramite `python run.py <comando>` ed include i seguenti comandi principali:

### `enterprise`
Esegue il workflow enterprise per un ente specifico.

**Opzioni:**
- `--ente` (richiesto): Nome dell'ente locale da analizzare (es. milano, roma)
- `--workflow`: Tipo di workflow da eseguire: full, analyze-only, scrape-only (default: full)
- `--config`: Percorso al file di configurazione (default: config.yaml)

**Esempio:**
```bash
python run.py enterprise --ente=baiano --workflow=full
```

### `audit`
Esegue l'audit antifrode sugli atti comunali.

**Opzioni:**
- `--base`: Cartella base dei dati (default: data/baiano/albo_download)
- `--ente`: Identificativo ente (opzionale)
- `--use-llm`: Abilita arricchimento LLM (opzionale)
- `--llm-provider`: Provider LLM (openai, gemini, mistral...) (opzionale)
- `--llm-model`: Modello LLM da usare (opzionale)

**Esempio:**
```bash
python run.py audit --ente=baiano --use-llm --llm-provider=gemini --llm-model=gemini-pro
```

### `build-kg`
Costruisce il knowledge graph relazionale.

**Opzioni:**
- `--base`: Cartella base dei dati (default: data/baiano/albo_download)
- `--ente`: Identificativo ente (opzionale)

**Esempio:**
```bash
python run.py build-kg --ente=baiano
```

### `post-process-classification`
Applica post-elaborazione alle classificazioni dei documenti con OCR.

**Opzioni:**
- `--input` (richiesto): File CSV di input con documenti parsati
- `--output` (richiesto): File CSV di output con classificazioni migliorate

**Esempio:**
```bash
python run.py post-process-classification --input=data/input.csv --output=data/output.csv
```

### `analyze-topology`
Analizza la topologia del knowledge graph.

**Opzioni:**
- `--base`: Cartella base dei dati (default: data/baiano/albo_download)
- `--ente`: Identificativo ente (opzionale)

**Esempio:**
```bash
python run.py analyze-topology --ente=baiano
```

### `supervised-training`
Esegue il riaddestramento supervisionato con feedback umano.

**Opzioni:**
- `--base`: Cartella base dei dati (default: data/baiano/albo_download)
- `--ente`: Identificativo ente (opzionale)

**Esempio:**
```bash
python run.py supervised-training --ente=baiano
```

### `metrics-exporter`
Avvia il server per l'esportazione delle metriche e il monitoraggio.

**Opzioni:** Nessuna richiesta

**Esempio:**
```bash
python run.py metrics-exporter
```

### `gdpr-delete`
Implementa il diritto all'oblio (GDPR Art. 17) cancellando i dati utente.

**Opzioni:**
- `--user-identifier` (richiesto): Identificativo utente da cancellare (CF, PIVA, email, ecc.)
- `--data-path`: Percorso dei dati in cui cercare i dati utente (default: 'data/')

**Esempio:**
```bash
python run.py gdpr-delete --user-identifier=CF12345678901
```

### `privacy-report`
Genera un report di conformità GDPR per un ente specifico.

**Opzioni:**
- `--ente` (richiesto): Nome dell'ente per cui generare il report di conformità

**Esempio:**
```bash
python run.py privacy-report --ente=baiano
```

### `control-room`, `ui`, `dashboard`
Avvia la dashboard di controllo (Streamlit app).

**Opzioni:** Nessuna richiesta

**Esempio:**
```bash
python run.py control-room
```

## Sistema Legacy (Compatibilità)

I comandi legacy sono accessibili tramite lo stesso sistema (`python run.py <comando>`) ma rappresentano il sistema precedente di mapping comandi:

### `scrape`
Estrae dati dall'albo pretorio.

**Esempio:**
```bash
python run.py scrape --ente=baiano
```

### `analyze`
Analizza e fa il parsing dei documenti.

**Esempio:**
```bash
python run.py analyze --ente=baiano
```

### `pipeline`
Esegue la pipeline completa.

**Esempio:**
```bash
python run.py pipeline --ente=baiano
```

### `validate-csv`
Valida i file CSV prodotti.

**Esempio:**
```bash
python run.py validate-csv --ente=baiano
```

### `orchestrate`
Esegue la pipeline completa di coordinamento tra tutti i moduli avanzati (Risk Assessment, KPI, ML, Audit).

**Esempio:**
```bash
python run.py orchestrate --ente=baiano
```

### `risk-assessment`
Esegue la valutazione del rischio.

**Esempio:**
```bash
python run.py risk-assessment --ente=baiano
```

### `management-kpi`
Calcola i KPI di gestione.

**Esempio:**
```bash
python run.py management-kpi --ente=baiano
```

### `actuarial-analysis`
Esegue l'analisi attuariale e il provisioning.

**Esempio:**
```bash
python run.py actuarial-analysis --ente=baiano
```

## API Web

### Dashboard Web
Il sistema include una dashboard web accessibile tramite interfaccia Streamlit.

**Endpoint:** `http://localhost:8501` (dopo l'avvio con `control-room`)

**Funzionalità:**
- Monitoraggio dello stato dei processi
- Visualizzazione dei risultati di analisi
- Interfaccia per la configurazione
- Reportistica in tempo reale
- Esplorazione documenti con RAG

### API REST
Il sistema espone alcune API REST per l'integrazione:

#### Metrics Exporter
**Endpoint:** `http://localhost:8001/metrics`

**Metodo:** GET

**Descrizione:** Fornisce metriche di sistema in formato Prometheus

#### RAG Service
**Endpoint:** `http://localhost:8000/query` (disponibile se il servizio RAG è avviato)

**Metodo:** POST

**Contenuto richiesta:**
```json
{
  "query": "domanda da porre al sistema",
  "ente": "nome_ente",
  "top_k": 5
}
```

**Contenuto risposta:**
```json
{
  "response": "risposta generata dal sistema",
  "sources": ["fonte1", "fonte2", "..."],
  "confidence": 0.85
}
```

## Configurazione

### File di Configurazione
Il sistema utilizza file di configurazione YAML per impostare i parametri globali:

**Posizione:** `config/config.yaml`

**Struttura esempio:**
```yaml
scraper:
  delay: 2.0
  timeout: 30
  max_retries: 3

ocr:
  tesseract_cmd: "/usr/bin/tesseract"
  enabled: true

llm:
  default_provider: "openai"
  default_model: "gpt-4"
  api_key: "sk-..."

rag:
  top_k: 6
  similarity_threshold: 0.7

logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

## Ambiente di Esecuzione

### Variabili d'Ambiente
- `GOOGLE_API_KEY`: Chiave API per Google Gemini (se utilizzato)
- `OPENAI_API_KEY`: Chiave API per OpenAI (se utilizzato)
- `DATABASE_URL`: Stringa di connessione al database (se utilizzato)
- `LOG_LEVEL`: Livello di logging (DEBUG, INFO, WARNING, ERROR)