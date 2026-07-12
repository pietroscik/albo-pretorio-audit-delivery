# Schema dei Dati

## Introduzione

Questo documento descrive gli schemi dei dati utilizzati dal sistema "Albo Pretorio Audit Delivery", inclusi i formati di input/output e le strutture dati interne.

## Format di Input

### File CSV
#### albo_metadati.csv
- `pdf_name`: Nome del file PDF
- `data_atto`: Data del documento
- `numero_atto`: Numero del documento
- `oggetto`: Oggetto del documento
- `doc_type`: Tipo di documento
- `categoria`: Categoria del documento
- `responsabile`: Responsabile del procedimento
- `beneficiario`: Eventuale beneficiario
- `importo`: Eventuale importo
- `cig`: Codice identificativo gara (CIG)
- `cup`: Codice unico progetto (CUP)

#### allegati_parsed.csv
- `pdf_name`: Nome del file PDF
- `file_path`: Percorso del file
- `content`: Contenuto estratto
- `metadata`: Metadati estratti
- `parsed_date`: Data di parsing
- `status`: Stato del parsing

### File JSONL
#### documenti_corpus.jsonl
- `id`: Identificatore univoco del documento
- `content`: Contenuto testuale del documento
- `metadata`: Metadati del documento
- `entities`: Entità estratte dal documento

## Format di Output

### File CSV
#### atti_parsed.csv
- `pdf_name`: Nome del file PDF
- `data_atto`: Data del documento
- `numero_atto`: Numero del documento
- `oggetto`: Oggetto del documento
- `doc_type`: Tipo di documento
- `category`: Categoria classificata
- `confidence`: Confidenza della classificazione
- `responsabile`: Responsabile del procedimento
- `beneficiario`: Eventuale beneficiario
- `importo_max`: Importo massimo trovato
- `cig`: Codice identificativo gara (CIG)
- `cup`: Codice unico progetto (CUP)
- `iban`: Eventuale IBAN
- `piva_beneficiario`: Partita IVA del beneficiario

#### atti_audited.csv
- `pdf_name`: Nome del file PDF
- `original_category`: Categoria originale
- `corrected_category`: Categoria corretta (se applicabile)
- `audit_notes`: Note dell'audit
- `auditor`: Nome dell'auditor
- `audit_date`: Data dell'audit
- `status`: Stato del processo di audit

#### risk_assessment.csv
- `pdf_name`: Nome del file PDF
- `risk_score`: Punteggio di rischio
- `risk_level`: Livello di rischio (basso, medio, alto)
- `risk_factors`: Fattori di rischio identificati
- `mitigation_actions`: Azioni di mitigazione suggerite
- `review_required`: Richiede revisione manuale (booleano)

#### top_importi.csv
- `pdf_name`: Nome del file PDF
- `importo`: Importo trovato
- `descrizione`: Descrizione del contesto dell'importo
- `data_documento`: Data del documento
- `tipo_documento`: Tipo del documento

### File JSON
#### procedures.json
- `procedure_id`: Identificatore univoco della procedura
- `steps`: Passi della procedura
- `dependencies`: Dipendenze tra passi
- `responsible`: Responsabili coinvolti
- `timeline`: Scadenze previste

#### anomalies.json
- `anomaly_id`: Identificatore univoco dell'anomalia
- `type`: Tipo di anomalia
- `description`: Descrizione dell'anomalia
- `severity`: Severità (bassa, media, alta)
- `related_documents`: Documenti collegati
- `suggested_action`: Azione suggerita

#### quality_metrics.json
- `total_documents`: Numero totale di documenti
- `parsed_documents`: Numero di documenti parsati
- `classified_documents`: Numero di documenti classificati
- `accuracy_metrics`: Metriche di accuratezza
- `error_rate`: Tasso di errore
- `confidence_distribution`: Distribuzione della confidenza

#### coordinated_analysis_results.json
- `timestamp`: Timestamp dell'esecuzione
- `risk_results`: Risultati del risk assessment
- `kpi_results`: Risultati del calcolo KPI
- `ml_results`: Risultati dell'analisi ML
- `audit_results`: Risultati dell'audit
- `cache_stats`: Statistiche sulla cache

### File JSON-LD
#### albo_linked_data.jsonld
- `@context`: Contesto RDF
- `@graph`: Grafo delle entità
- `entities`: Entità identificate
- `relationships`: Relazioni tra entità
- `properties`: Proprietà delle entità

## Format di Configurazione Enterprise

### File JSON di Configurazione
#### enterprise_config.json
- `timestamp`: Timestamp della configurazione
- `ente`: Nome dell'ente
- `base_path`: Percorso base
- `enterprise_params`: Parametri enterprise
  - `enable_coordination`: Abilita coordinamento
  - `enable_parallel_processing`: Abilita elaborazione parallela
  - `max_workers`: Numero massimo di worker
  - `enable_caching`: Abilita caching
  - `skip_risk_assessment`: Salta risk assessment
  - `skip_kpi_calculation`: Salta calcolo KPI
  - `skip_ml_analysis`: Salta analisi ML
  - `skip_audit`: Salta audit
  - `batch_size`: Dimensione del batch
  - `chunk_size`: Dimensione del chunk
  - `similarity_threshold`: Soglia di similarità
  - `dry_run`: Modalità simulazione
  - `verbose`: Modalità verbosa
  - `log_level`: Livello di log

## Strutture Dati Interne

### DataEntry (nel DataCoordinator)
- `data_type`: Tipo di dato (Enumerazione DataType)
- `data`: Contenuto del dato
- `timestamp`: Timestamp dell'inserimento
- `source_module`: Modulo di origine
- `version`: Versione del dato
- `metadata`: Metadati aggiuntivi

### EnterpriseParams (nel ConfigManager)
- `ente`: Nome dell'ente
- `base_path`: Percorso base
- `output_path`: Percorso di output
- `enable_coordination`: Abilita coordinamento
- `enable_parallel_processing`: Abilita elaborazione parallela
- `max_workers`: Numero massimo di worker
- `enable_caching`: Abilita caching
- `skip_risk_assessment`: Salta risk assessment
- `skip_kpi_calculation`: Salta calcolo KPI
- `skip_ml_analysis`: Salta analisi ML
- `skip_audit`: Salta audit
- `batch_size`: Dimensione del batch
- `chunk_size`: Dimensione del chunk
- `similarity_threshold`: Soglia di similarità
- `dry_run`: Modalità simulazione
- `verbose`: Modalità verbosa
- `log_level`: Livello di log

## Sicurezza e Governance

Tutti gli schemi dati rispettano i principi di governance pubblica:
- Nessun dato sensibile è incluso negli schemi
- Tutti i dati trattati sono documenti ufficiali pubblici
- Le strutture dati consentono tracciamento e verifica
- I metadati supportano la trasparenza amministrativa