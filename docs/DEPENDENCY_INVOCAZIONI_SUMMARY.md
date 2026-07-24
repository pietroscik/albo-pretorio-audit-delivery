# Analisi Dipendenze e Invocazioni - Sistema Albo Pretorio Audit Delivery

## Panoramica del Sistema

Il sistema utilizza un **doppio sistema di comandi**:
1. **Comandi Click-based (Moderni)** - Implementati direttamente in `run.py` con decorator Click
2. **Comandi Legacy** - Accessibili tramite sistema di mapping per retrocompatibilità

## Dipendenze e Invocazioni Verificate

### 1. Struttura dei Moduli
Tutti i percorsi modulo definiti in `COMMAND_MAP` corrispondono a file esistenti:
- ✅ `delibere_comunali.scraping.new_albo_scraper`
- ✅ `delibere_comunali.parsing.analyze_albo`
- ✅ `delibere_comunali.cli.run_pipeline`
- ✅ `delibere_comunali.validation.csv_validator`
- ✅ `delibere_comunali.core.orchestrator`
- ✅ `delibere_comunali.core.data_coordinator`
- ✅ `delibere_comunali.core.enterprise_orchestration`
- ✅ `delibere_comunali.core.config_manager`
- ✅ `delibere_comunali.analysis.risk_assessment`
- ✅ `delibere_comunali.analysis.management_kpi`
- ✅ `delibere_comunali.analysis.actuarial_analysis`
- ✅ `delibere_comunali.parsing.post_process_classification`
- ✅ `delibere_comunali.processing.correction_handler`
- ✅ `delibere_comunali.rag.rag_app`

### 2. Script Legacy
Tutti gli script definiti come percorsi in `scripts/` esistono:
- ✅ `build_knowledge_graph.py`
- ✅ `analyze_topology.py`
- ✅ `detect_anomalies.py`
- ✅ `export_linked_data.py`
- ✅ `train_model.py`
- ✅ `validate_output.py`
- ✅ `clean_texts.py`
- ✅ `sync_texts.py`
- ✅ `generate_ground_truth.py`
- ✅ `visualizza_grafo.py`
- ✅ `explore_albo.py`
- ✅ `reconcile_semantic.py`
- ✅ `validate_fase0.py`
- ✅ `validate_ground_truth.py`
- ✅ `verify_output.py`
- ✅ `update_preview.py`
- ✅ `finance_validator.py`
- ✅ `randomForest.py`

### 3. Inconsistenze Identificate

#### 3.1. Comando `validate-output`
- **Mapping attuale**: `"validate-output": ("-m", "delibere_comunali.validation.output_validator")`
- **Problema**: Il modulo `delibere_comunali.validation.output_validator` esiste ma è implementato come wrapper che richiede l'argomento `--ente`, mentre altri comandi simili utilizzano `--base`
- **Stato**: Funzionante ma con interfaccia leggermente diversa

#### 3.2. Comando `validate-csv`
- **Mapping attuale**: `"validate-csv": ("-m", "delibere_comunali.validation.csv_validator")`
- **Stato**: Funzionante

#### 3.3. Comando `build-kg` (Script Legacy)
- **Mapping attuale**: `"build-kg": (str(PROJECT_ROOT / "scripts" / "build_knowledge_graph.py"),)`
- **Problema trovato**: Nel file `run.py` originale, il comando Click `build_kg` stava cercando di eseguire il modulo come script invece di eseguirlo correttamente
- **Stato attuale**: Risolto nei file aggiornati

### 4. Sistema di Wrapper per Script Legacy
Il sistema definito in `src/delibere_comunali/cli/scripts.py` funziona correttamente:
- Gli script legacy vengono eseguiti tramite `runpy.run_path()`
- Fallback a moduli se lo script non esiste
- Funziona come previsto

### 5. Comando Enterprise Workflow Options
- **Opzioni attuali**: `['full', 'analyze-only', 'scrape-only']`
- **Conformità**: Tutte le opzioni sono implementate correttamente nel codice

### 6. Comandi Streamlit
I comandi che richiedono Streamlit sono gestiti correttamente:
- `STREAMLIT_COMMANDS = {"rag", "apply-corrections", "risk-assessment", "actuarial-analysis", "management-kpi"}`
- Lanciati con il comando appropriato `streamlit run`

## Conclusione

Il sistema di dipendenze e invocazioni è **funzionante e consistente**. Le uniche piccole incongruenze trovate sono:

1. **Leggera differenza di interfaccia** per `validate-output` (usa `--ente` invece di `--base`)
2. Alcuni comandi hanno leggere differenze di firma tra implementazione e documentazione

Non sono state trovate discrepanze critiche che impediscano il funzionamento del sistema.

## Raccomandazioni

1. **Mantenere la retrocompatibilità** per i comandi legacy
2. **Documentare chiaramente** le differenze di interfaccia tra comandi moderni e legacy
3. **Aggiornare la documentazione** per riflettere le vere opzioni disponibili
4. **Considerare l'uniformazione** delle interfacce `--ente` vs `--base` nei futuri sviluppi