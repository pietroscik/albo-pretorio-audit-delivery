# Albo Pretorio Audit Delivery

Sistema enterprise per l'analisi, classificazione e audit dei documenti presenti negli albi pretori comunali italiani.

## Funzionalità

- **Scraping**: Estrazione automatica dei documenti dagli albi pretori
- **Parsing**: Analisi e estrazione delle informazioni dai documenti
- **Classificazione**: Classificazione automatica dei documenti in categorie specifiche
- **Risk Assessment**: Valutazione del rischio associato ai documenti
- **Knowledge Graph**: Costruzione di un grafo semantico delle entità
- **RAG (Retrieval Augmented Generation)**: Sistema di ricerca e generazione di risposte basato su documenti
- **Dashboard**: Interfaccia di controllo per la supervisione delle analisi
- **Enterprise Orchestration**: Sistema di coordinamento avanzato tra i vari moduli

## Comandi Principali

### Comandi Base
- `scrape`: Estrazione dati dall'albo pretorio
- `analyze`: Analisi e parsing dei documenti
- `pipeline`: Esecuzione della pipeline completa
- `validate-csv`: Validazione dei file CSV prodotti
- `control-room`: Dashboard di controllo (alias: `ui`, `dashboard`)
- `audit`: Motore di audit
- `post-process-classification`: Post-processing della classificazione
- `apply-corrections`: Applicazione delle correzioni manuali

### Comandi Enterprise
- `orchestrate`: Esecuzione della pipeline completa di coordinamento tra tutti i moduli avanzati (Risk Assessment, KPI, ML, Audit)
- `data-coord`: Interfaccia per il coordinatore dati centralizzato
- `enterprise`: Esecuzione di workflow enterprise con parametri configurabili
- `config-mgmt`: Gestione della configurazione enterprise

### Comandi ML e Analytics
- `risk-assessment`: Esecuzione dell'analisi del rischio
- `management-kpi`: Calcolo dei KPI di gestione
- `actuarial-analysis`: Analisi attuariale e provisioning

### Script Legacy
- `build-kg`: Costruzione del knowledge graph
- `analyze-topology`: Analisi topologica
- `detect-anomalies`: Rilevamento anomalie
- `export-linkeddata`: Esportazione dati collegati
- `train`: Training del modello ML
- `validate-output`: Validazione output
- `clean-texts`: Pulizia testi
- `sync-texts`: Sincronizzazione testi
- `generate-groundtruth`: Generazione ground truth
- `visualize-graph`: Visualizzazione grafo
- `explore`: Esplorazione albo
- `reconcile`: Riconciliazione semantica
- `validate-fase0`: Validazione fase 0
- `validate-ground`: Validazione ground truth
- `verify-output`: Verifica output
- `update-preview`: Aggiornamento anteprima
- `finance-validate`: Validazione finanziaria
- `random-forest`: Modello Random Forest

## Utilizzo

### Esecuzione della pipeline completa
```bash
python run.py pipeline --ente=comune_di_esempio
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

### Gestione configurazione enterprise
```bash
# Visualizzazione configurazione
python run.py config-mgmt --ente=comune_di_esempio --action=show

# Salvataggio configurazione
python run.py config-mgmt --ente=comune_di_esempio --action=save

# Caricamento configurazione da file
python run.py config-mgmt --ente=comune_di_esempio --action=load --config-path=/path/to/config.json

# Validazione configurazione
python run.py config-mgmt --ente=comune_di_esempio --action=validate

# Raccomandazioni automatiche
python run.py config-mgmt --ente=comune_di_esempio --action=recommend
```

### Esecuzione della pipeline con workflow enterprise
```bash
# Pipeline completa con workflow enterprise
python run.py pipeline --ente=comune_di_esempio --enterprise-workflow=full

# Pipeline con workflow specifico
python run.py pipeline --ente=comune_di_esempio --enterprise-workflow=risk_only

# Pipeline con configurazione enterprise personalizzata
python run.py pipeline --ente=comune_di_esempio --enterprise-workflow=full --enterprise-config=/path/to/config.json
```

### Dashboard RAG
```bash
python run.py rag
```

### Dashboard Control Room
```bash
python run.py control-room
```

## Requisiti

- Python 3.8+
- Dipendenze specificate in [requirements.txt](file:///c:/Users\39329\albo-pretorio-audit-delivery/requirements.txt)
- Tesseract OCR per l'estrazione del testo dai PDF scansionati
- Chiave API Google Gemini (opzionale, per funzionalità avanzate di RAG)

## Struttura del Progetto

```
src/
├── delibere_comunali/
│   ├── core/              # Componenti centrali (orchestrator, data coordinator)
│   ├── parsing/           # Moduli di parsing ed estrazione
│   ├── scraping/          # Moduli di scraping
│   ├── ml/                # Moduli di machine learning
│   ├── risk_assessment/   # Moduli di valutazione del rischio
│   ├── management_kpi/    # Moduli di calcolo KPI
│   ├── knowledge_graph/   # Moduli di costruzione del knowledge graph
│   ├── rag/               # Moduli RAG
│   ├── utils/             # Utilità varie
│   └── ...
scripts/                  # Script autonomi per funzionalità specifiche
data/                     # Dati di input/output
output/                   # Output dei vari moduli
lib/                      # Librerie esterne
```

## Documentazione

- [Architettura del Sistema](file:///c:/Users\39329\albo-pretorio-audit-delivery/ARCHITECTURE.md)
- [Guida alla Parameterizzazione Enterprise](file:///c:/Users\39329\albo-pretorio-audit-delivery/ENTERPRISE_PARAMETERIZATION_GUIDE.md)
- [Mappa I/O del Sistema](file:///c:/Users\39329\albo-pretorio-audit-delivery/IO_MAP.md)
- [Guida alla Coordinazione](file:///c:/Users\39329\albo-pretorio-audit-delivery/COORDINATION_GUIDE.md)
- [Sommario dei Cambiamenti](file:///c:/Users\39329\albo-pretorio-audit-delivery/CHANGES_SUMMARY.md)
- [Visione e Missione](file:///c:/Users\39329\albo-pretorio-audit-delivery/VISION_MISSION.md)