# Guida alla Parameterizzazione Enterprise

## Panoramica

Il sistema di audit dell'albo pretorio ha raggiunto uno stato enterprise con un sistema di coordinamento avanzato tra diversi moduli. Questa guida illustra come gestire efficacemente i parametri in questo ambiente complesso.

## Architettura del Sistema

### Componenti Chiave

1. **CentralOrchestrator**: Coordinatore centrale che gestisce i moduli avanzati (Risk Assessment, KPI, ML, Audit)
2. **DataCoordinator**: Sistema centralizzato per la gestione dei dati condivisi tra i moduli
3. **ConfigManager**: Gestore unificato per tutti i parametri del sistema enterprise
4. **EnterpriseOrchestrator**: Orchestrator con parametri configurabili per workflow enterprise

## Sistema di Parameterizzazione

### Configurazione Unificata

Il nuovo `ConfigManager` offre un'interfaccia unificata per gestire tutti i parametri del sistema:

```bash
# Visualizza la configurazione attiva
python run.py config-mgmt --ente=comune_di_test --action=show

# Salva la configurazione in un file
python run.py config-mgmt --ente=comune_di_test --action=save --config-path=/path/to/config.json

# Carica la configurazione da un file
python run.py config-mgmt --ente=comune_di_test --action=load --config-path=/path/to/config.json

# Ottieni raccomandazioni sui parametri in base alle risorse
python run.py config-mgmt --ente=comune_di_test --action=recommend

# Validazione della configurazione
python run.py config-mgmt --ente=comune_di_test --action=validate
```

### Parametri Enterprise

La classe `EnterpriseParams` definisce tutti i parametri configurabili:

#### Parametri Generali
- `ente`: Nome dell'ente comunale da analizzare
- `base_path`: Percorso base per i dati
- `output_path`: Percorso per i risultati di output

#### Parametri di Coordinamento
- `enable_coordination`: Abilita/disabilita la coordinazione tra moduli
- `enable_parallel_processing`: Attiva/disattiva l'elaborazione parallela
- `max_workers`: Numero massimo di worker per l'elaborazione parallela
- `enable_caching`: Abilita/disabilita la cache

#### Parametri di Analisi
- `skip_risk_assessment`: Salta l'analisi del rischio
- `skip_kpi_calculation`: Salta il calcolo dei KPI
- `skip_ml_analysis`: Salta l'analisi ML
- `skip_audit`: Salta l'audit

#### Parametri di Performance
- `batch_size`: Dimensione dei batch per l'elaborazione
- `chunk_size`: Dimensione dei chunk per l'embedding RAG
- `similarity_threshold`: Soglia di similarità per la ricerca

## Utilizzo Pratico

### Esecuzione di Workflow Enterprise

```bash
# Esecuzione completa con tutti i moduli
python run.py enterprise --ente=comune_di_test --workflow=full

# Esecuzione solo del risk assessment
python run.py enterprise --ente=comune_di_test --workflow=risk_only

# Esecuzione con parametri specifici
python run.py enterprise --ente=comune_di_test --workflow=full \
  --skip-ml --skip-audit --base-path=/custom/path

# Esecuzione con salvataggio dei risultati
python run.py enterprise --ente=comune_di_test --workflow=full \
  --save-results --verbose

# Esecuzione in modalità dry-run (simulazione)
python run.py enterprise --ente=comune_di_test --workflow=minimal \
  --dry-run --verbose
```

### Gestione Avanzata dei Parametri

Puoi anche aggiornare specifici parametri durante l'esecuzione:

```bash
# Aggiornare parametri specifici
python run.py config-mgmt --ente=comune_di_test \
  --update-param max_workers 8 \
  --update-param batch_size 20 \
  --update-param enable_caching true
```

### File di Configurazione

Puoi creare file di configurazione JSON per memorizzare impostazioni specifiche:

```json
{
  "timestamp": "2026-07-12T19:36:42.123456",
  "ente": "comune_di_test",
  "base_path": "./data/comune_di_test/albo_download",
  "enterprise_params": {
    "ente": "comune_di_test",
    "base_path": "./data/comune_di_test/albo_download",
    "output_path": "./output",
    "enable_coordination": true,
    "enable_parallel_processing": true,
    "max_workers": 4,
    "enable_caching": true,
    "skip_risk_assessment": false,
    "skip_kpi_calculation": false,
    "skip_ml_analysis": false,
    "skip_audit": false,
    "batch_size": 10,
    "chunk_size": 512,
    "similarity_threshold": 0.7,
    "dry_run": false,
    "verbose": false,
    "log_level": "INFO"
  },
  "app_config_summary": {
    "scraper_enabled": true,
    "ocr_enabled": true,
    "llm_enabled": true,
    "rag_enabled": true,
    "performance_settings": {
      "max_workers": 4,
      "batch_size": 10,
      "cache_enabled": true
    }
  }
}
```

## Comandi Disponibili

### Comandi Principali
- `orchestrate`: Esegue la pipeline completa di coordinamento
- `data-coord`: Interfaccia per il coordinatore dati centralizzato
- `enterprise`: Esegue orchestrazioni enterprise con parametri configurabili
- `config-mgmt`: Gestisce la configurazione enterprise

### Comandi di Analisi
- `risk-assessment`: Esegue l'analisi del rischio
- `management-kpi`: Esegue il calcolo dei KPI
- `actuarial-analysis`: Esegue l'analisi attuariale

### Comandi di Supporto
- `scrape`: Estrazione dati dall'albo pretorio
- `analyze`: Analisi dei documenti
- `pipeline`: Esegue la pipeline completa
- `rag`: Interfaccia RAG per interrogazioni
- `control-room`: Dashboard di controllo

## Best Practice

### 1. Ambiente Multi-Tenants
Usa il parametro `--ente` per separare i dati di diversi enti:

```bash
python run.py enterprise --ente=comune_milano --workflow=full
python run.py enterprise --ente=comune_roma --workflow=full
```

### 2. Configurazione Ottimizzata
Usa il comando di raccomandazione per ottimizzare i parametri in base alle risorse:

```bash
python run.py config-mgmt --ente=comune_di_test --action=recommend
```

### 3. Validazione della Configurazione
Valida sempre la configurazione prima di esecuzioni lunghe:

```bash
python run.py config-mgmt --ente=comune_di_test --action=validate
```

### 4. Uso della Cache
Abilita la cache per migliorare le prestazioni in esecuzioni ripetute:

```bash
python run.py config-mgmt --ente=comune_di_test \
  --update-param enable_caching true
```

## Esempi di Workflow Comuni

### 1. Analisi Completa con Ottimizzazione
```bash
# Ottieni raccomandazioni
python run.py config-mgmt --ente=comune_di_test --action=recommend

# Aggiorna i parametri ottimizzati
python run.py config-mgmt --ente=comune_di_test \
  --update-param max_workers 8 \
  --update-param batch_size 15

# Esegui l'analisi completa
python run.py enterprise --ente=comune_di_test --workflow=full --save-results
```

### 2. Analisi Incrementale
```bash
# Esegui solo il risk assessment iniziale
python run.py enterprise --ente=comune_di_test --workflow=risk_only

# Successivamente esegui altri moduli
python run.py enterprise --ente=comune_di_test --workflow=kpi_only

# Infine esegui l'analisi completa con feedback
python run.py enterprise --ente=comune_di_test --workflow=full --save-results
```

### 3. Test Rapidi
```bash
# Esegui un'analisi minimale per test
python run.py enterprise --ente=comune_di_test --workflow=minimal --dry-run
```

## Risoluzione dei Problemi

### Problemi Comuni

1. **Mancanza di dati**: Verifica che i file `atti_parsed.csv` o `atti_parsed.jsonl` esistano nella directory corretta.

2. **Errore di coordinamento**: Controlla che tutti i moduli richiesti siano disponibili e che la configurazione sia valida.

3. **Problemi di performance**: Riduci `max_workers` o `batch_size` se il sistema è sovraccarico.

4. **Mancanza di chiavi API**: Assicurati che le variabili d'ambiente siano impostate correttamente.

## Sicurezza e Accesso

Tutti i parametri sensibili (come chiavi API) sono gestiti attraverso variabili d'ambiente e il sistema di configurazione Pydantic. Il sistema non memorizza mai chiavi sensibili nei file di configurazione.

## Monitoraggio e Logging

Il sistema registra tutte le operazioni in log dettagliati e salva i risultati in formato strutturato per un'analisi successiva.