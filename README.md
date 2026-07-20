# Albo Pretorio Audit Delivery

Sistema di analisi, audit e compliance per albi pretori comunali. Il progetto implementa un motore di rilevazione frodi, ottimizzazione dei processi amministrativi e controllo antifrode basato su tecnologie AI/ML.

## Architettura del Sistema

Il sistema si compone di diversi moduli interagenti:

- **Scraping**: Estrazione dati dagli albi pretori
- **Parsing**: Analisi e estrazione delle informazioni dai documenti
- **Classificazione**: Classificazione automatica dei documenti in categorie specifiche
- **Risk Assessment**: Valutazione del rischio associato ai documenti
- **Knowledge Graph**: Costruzione di un grafo semantico delle entità
- **RAG (Retrieval Augmented Generation)**: Sistema di ricerca e generazione di risposte basato su documenti
- **Dashboard**: Interfaccia di controllo per la supervisione delle analisi
- **Enterprise Orchestration**: Sistema di coordinamento avanzato tra i vari moduli

## Comandi Principali

Il sistema dispone di due modalità di utilizzo:

### 1. Interfaccia Click-based (Consigliata)
Questa è l'interfaccia moderna e preferita, accessibile direttamente con `python run.py <comando>`:

#### Comandi Base
- `enterprise`: Esegue il workflow enterprise per un ente specifico
- `audit`: Esegue l'audit antifrode sugli atti comunali
- `build-kg`: Costruisce il knowledge graph relazionale
- `post-process-classification`: Applica post-elaborazione alle classificazioni dei documenti con OCR
- `analyze-topology`: Analizza la topologia del knowledge graph
- `supervised-training`: Esegue il riaddestramento supervisionato con feedback umano
- `metrics-exporter`: Avvia il server per l'esportazione delle metriche e il monitoraggio
- `gdpr-delete`: Implementa il diritto all'oblio (GDPR Art. 17)
- `privacy-report`: Genera un report di conformità GDPR per un ente specifico
- `control-room`: Avvia la dashboard di controllo (Streamlit app)
- `dashboard`: Alias per avviare la dashboard di controllo
- `ui`: Alias per avviare l'interfaccia utente

### 2. Sistema di Comandi Legacy
Accessibile tramite il sistema di mapping comandi per compatibilità con versioni precedenti:

#### Comandi Principali
- `scrape`: Estrazione dati dall'albo pretorio
- `analyze`: Analisi e parsing dei documenti
- `pipeline`: Esecuzione della pipeline completa
- `validate-csv`: Validazione dei file CSV prodotti

#### Comandi Enterprise
- `orchestrate`: Esecuzione della pipeline completa di coordinamento tra tutti i moduli avanzati (Risk Assessment, KPI, ML, Audit)
- `data-coord`: Interfaccia per il coordinatore dati centralizzato
- `config-mgmt`: Gestione della configurazione enterprise

#### Comandi ML e Analytics
- `risk-assessment`: Esecuzione dell'analisi del rischio
- `management-kpi`: Calcolo dei KPI di gestione
- `actuarial-analysis`: Analisi attuariale e provisioning

#### Comandi UI e RAG
- `control-room`: Dashboard di controllo (alias: `ui`, `dashboard`)
- `rag`: Interfaccia RAG per ricerca semantica
- `apply-corrections`: Applicazione delle correzioni manuali

## Utilizzo

### Esecuzione della pipeline completa
```bash
# Utilizzando l'interfaccia moderna (consigliata)
python run.py pipeline --ente=comune_di_esempio

# Con opzioni avanzate
python run.py pipeline --ente=comune_di_esempio --limit 10
```

### Esecuzione con parametri enterprise
```bash
# Esecuzione workflow enterprise completo
python run.py enterprise --ente=comune_di_esempio --workflow=full

# Esecuzione solo del risk assessment
python run.py enterprise --ente=comune_di_esempio --workflow=risk_only

# Esecuzione con configurazione personalizzata
python run.py enterprise --ente=comune_di_esempio --workflow=full --config-file=/path/to/config.json
```

### Esecuzione di singoli moduli
```bash
# Esecuzione dell'audit
python run.py audit --ente=baiano --use-llm

# Costruzione del knowledge graph
python run.py build-kg --ente=baiano

# Analisi della topologia
python run.py analyze-topology --ente=baiano

# Post-process delle classificazioni
python run.py post-process-classification --input=data/input.csv --output=data/output.csv
```

### Avvio della dashboard di controllo
```bash
# Modalità moderna (consigliata)
python run.py control-room

# Modalità legacy
python run.py control-room
```

### Gestione privacy e GDPR
```bash
# Genera report di conformità GDPR per un ente
python run.py privacy-report --ente=baiano

# Cancella dati utente (diritto all'oblio)
python run.py gdpr-delete --user-identifier=CF12345678901
```

## Struttura del Progetto

```
albo-pretorio-audit-delivery/
├── src/
│   ├── delibere_comunali/           # Codice sorgente principale
│   │   ├── cli/                    # Interfacce a riga di comando
│   │   ├── core/                   # Funzionalità principali
│   │   ├── parsing/                # Moduli di parsing e analisi
│   │   ├── processing/             # Elaborazione dati
│   │   ├── analysis/               # Analisi e valutazioni
│   │   ├── ml/                     # Machine learning
│   │   ├── knowledge_graph/        # Gestione knowledge graph
│   │   ├── rag/                    # RAG (Retrieval Augmented Generation)
│   │   ├── web/                    # Interfacce web
│   │   └── utils/                  # Utilità varie
│   ├── scripts/                    # Script di utilità
│   └── tests/                      # Test
├── data/                           # Dati scaricati e output
│   └── {ente}/                     # Dati specifici per ente
│       ├── albo_download/          # Dati grezzi scaricati
│       ├── parsed_data/            # Dati parsati
│       └── reports/                # Report generati
├── config/                         # File di configurazione
├── docs/                           # Documentazione
├── run.py                          # Entry point principale
└── scripts/                        # Script di utilità
    ├── run_pipeline.sh             # Script pipeline completo
    └── daily_run.sh                # Script esecuzione quotidiana
```

## Configurazione

Il sistema può essere configurato attraverso:

1. **File di configurazione YAML** (vedi la directory [config/](config/))
2. **Variabili d'ambiente**
3. **Parametri a riga di comando**

## Monitoraggio e Sicurezza

- **Metrics Exporter**: Sistema di raccolta e visualizzazione metriche
- **Privacy Guard**: Implementazione del GDPR con tracciamento dei dati sensibili
- **Audit Trail**: Tracciamento completo delle operazioni
- **Role-Based Access Control**: Controllo degli accessi basato sui ruoli

## Licenza

GPL-3.0 license