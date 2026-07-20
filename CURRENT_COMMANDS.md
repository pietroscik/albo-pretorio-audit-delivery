# Comandi Attualmente Disponibili

## Interfaccia Moderna (Click-based)

### Comandi Principali
- `python run.py enterprise` - Esegue il workflow enterprise per un ente specifico
- `python run.py audit` - Esegue l'audit antifrode sugli atti comunali
- `python run.py build-kg` - Costruisce il knowledge graph relazionale
- `python run.py post-process-classification` - Applica post-elaborazione alle classificazioni dei documenti con OCR
- `python run.py analyze-topology` - Analizza la topologia del knowledge graph
- `python run.py supervised-training` - Esegue il riaddestramento supervisionato con feedback umano
- `python run.py metrics-exporter` - Avvia il server per l'esportazione delle metriche e il monitoraggio

### Comandi di Sicurezza e Privacy
- `python run.py gdpr-delete` - Implementa il diritto all'oblio (GDPR Art. 17)
- `python run.py privacy-report` - Genera un report di conformità GDPR per un ente specifico

### Interfaccia Utente
- `python run.py control-room` - Avvia la dashboard di controllo (Streamlit app)
- `python run.py dashboard` - Alias per avviare la dashboard di controllo
- `python run.py ui` - Alias per avviare l'interfaccia utente

## Sistema Legacy (Compatibilità)

### Comandi Principali
- `python run.py scrape` - Estrazione dati dall'albo pretorio
- `python run.py analyze` - Analisi e parsing dei documenti
- `python run.py pipeline` - Esecuzione della pipeline completa
- `python run.py validate-csv` - Validazione dei file CSV prodotti

### Comandi Enterprise
- `python run.py orchestrate` - Esecuzione della pipeline completa di coordinamento
- `python run.py data-coord` - Interfaccia per il coordinatore dati centralizzato
- `python run.py config-mgmt` - Gestione della configurazione enterprise

### Comandi ML e Analytics
- `python run.py risk-assessment` - Esecuzione dell'analisi del rischio
- `python run.py management-kpi` - Calcolo dei KPI di gestione
- `python run.py actuarial-analysis` - Analisi attuariale e provisioning

### Comandi UI e RAG
- `python run.py rag` - Interfaccia RAG per ricerca semantica
- `python run.py apply-corrections` - Applicazione delle correzioni manuali

### Comandi di Utilità
- `python run.py detect-anomalies` - Rilevamento anomalie
- `python run.py export-linkeddata` - Esportazione linked data
- `python run.py validate-output` - Validazione output
- `python run.py clean-texts` - Pulizia testi
- `python run.py sync-texts` - Sincronizzazione testi
- `python run.py generate-groundtruth` - Generazione ground truth
- `python run.py visualize-graph` - Visualizzazione grafo
- `python run.py explore` - Esplorazione albo
- `python run.py reconcile` - Riconciliazione semantica
- `python run.py validate-fase0` - Validazione fase 0
- `python run.py validate-ground` - Validazione ground truth
- `python run.py verify-output` - Verifica output
- `python run.py update-preview` - Aggiornamento anteprima
- `python run.py finance-validate` - Validazione finanziaria
- `python run.py random-forest` - Modello Random Forest

## Utilizzo Tipico

### Pipeline Completa
```bash
# Modalità moderna
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
# Command Reference for Albo Pretorio Audit Delivery

This document provides an updated reference of available commands based on the current implementation.

## Current Command Structure

The application uses a dual command system:
1. **Click-based CLI commands** - Modern command interface implemented with Click decorators
2. **Legacy script commands** - Traditional script-based commands accessed through run.py wrapper

## Click-based CLI Commands

These commands are implemented directly in [run.py](run.py) using Click decorators:

### Core Commands
- `enterprise` - Executes enterprise workflow for an entity
  - Options: `--ente` (required), `--workflow`, `--config`
- `audit` - Performs anti-fraud audit on municipal acts
  - Options: `--base`, `--ente`, `--use-llm`, `--llm-provider`, `--llm-model`
- `build-kg` - Builds relational knowledge graph
  - Options: `--base`, `--ente`
- `post-process-classification` - Applies post-processing to OCR classifications
  - Options: `--input` (required), `--output` (required)
- `analyze-topology` - Analyzes knowledge graph topology
  - Options: `--base`, `--ente`
- `supervised-training` - Performs supervised retraining with human feedback
  - Options: `--base`, `--ente`
- `metrics-exporter` - Starts metrics export and monitoring server
  - No options required
- `gdpr-delete` - Implements right to be forgotten (GDPR Art. 17)
  - Options: `--user-identifier` (required), `--data-path`
- `privacy-report` - Generates GDPR compliance report for an entity
  - Options: `--ente` (required)

## Legacy Script Commands

These commands are accessed through the run.py wrapper system and correspond to individual Python scripts:

### Scraping Commands
- `scrape` - Extract data from public register
- `scraper` - Alternative scraping command

### Processing Commands
- `analyze` - Analyze and parse documents
- `pipeline` - Execute complete pipeline
- `run-pipeline` - Alternative pipeline command
- `validate-csv` - Validate CSV files produced

### UI/Dashboard Commands
- `control-room` - Launch control dashboard (Streamlit app)
- `ui` - Alternative dashboard command
- `dashboard` - Alternative dashboard command
- `rag` - RAG interface
- `apply-corrections` - Apply manual corrections

### Enterprise Orchestration Commands
- `orchestrate` - Execute full coordination pipeline between all advanced modules (Risk Assessment, KPI, ML, Audit)
- `data-coord` - Interact with centralized data coordinator for shared data management
- `enterprise` - Execute enterprise orchestration with configurable parameters (may be duplicated)
- `config-mgmt` - Manage enterprise configuration settings

### Advanced Analysis Commands
- `risk-assessment` - Execute risk assessment analysis
- `management-kpi` - Execute management KPI calculation
- `actuarial-analysis` - Execute actuarial analysis and provisioning

### Knowledge Graph Commands
- `build-kg` - Build knowledge graph (may be duplicated)
- `analyze-topology` - Analyze topology of knowledge graph (may be duplicated)
- `detect-anomalies` - Detect anomalies in data
- `export-linkeddata` - Export linked data

### ML and Training Commands
- `train` - Train machine learning models
- `supervised-training` - Supervised training with feedback (may be duplicated)
- `random-forest` - Random forest model execution

### Data Processing Commands
- `validate-output` - Validate output files
- `clean-texts` - Clean text data
- `sync-texts` - Synchronize text data
- `generate-groundtruth` - Generate ground truth data
- `post-process` - Post-process classification results (alias for post-process-classification)

### Visualization and Analysis Commands
- `visualize-graph` - Visualize knowledge graph
- `explore` - Explore public register data
- `reconcile` - Perform semantic reconciliation
- `finance-validate` - Perform financial validation

### Quality Assurance Commands
- `validate-fase0` - Validate phase 0
- `validate-ground` - Validate ground truth
- `verify-output` - Verify output quality
- `update-preview` - Update preview data

## Usage Examples

### Using Click-based Commands
```bash
# Run enterprise workflow
python run.py enterprise --ente=comune_di_esempio --workflow=full

# Perform audit
python run.py audit --ente=baiano --use-llm

# Build knowledge graph
python run.py build-kg --ente=baiano

# Post-process classifications
python run.py post-process-classification --input=data/input.csv --output=data/output.csv
```

### Using Legacy Script Commands
```bash
# Run complete pipeline
python run.py pipeline --ente=baiano

# Start control room
python run.py control-room

# Run analysis
python run.py analyze --ente=baiano

# Train models
python run.py train --ente=baiano
```

## Complete Pipeline Execution

To run the complete pipeline for an entity:

```bash
# Run the main pipeline
python run.py pipeline --ente=nome_ente

# Or use the script directly
./scripts/run_pipeline.sh nome_ente

# For enterprise-level orchestration
python run.py enterprise --ente=nome_ente --workflow=full
```

## Note on Command Duplication

Some commands may appear in both the Click-based system and the legacy script system. The Click-based commands generally offer more options and better integration with the overall system, while the legacy commands maintain backward compatibility.

## Getting Help

To see all available commands and their options:
```bash
python run.py --help
python run.py <command> --help
```