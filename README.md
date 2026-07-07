# Albo Pretorio Audit Delivery

## Panoramica

Questo progetto contiene un sistema avanzato di audit e analisi del comportamento procedurale del Comune di Avella, basato sull'analisi automatica degli atti pubblici presenti nell'albo pretorio.

## Obiettivo

Il sistema è progettato per:
- Analizzare automaticamente i documenti dell'albo pretorio
- Classificare i documenti in diverse categorie (Determinazioni, Delibere, Visti Contabili, ecc.)
- Rilevare anomalie e potenziali frodi amministrative
- Fornire una visione olistica del comportamento procedurale
- Monitorare la qualità e la trasparenza della gestione pubblica

## Risultati Principali

### Miglioramenti del Sistema
- **Classificazioni ambigue**: Ridotte da 1,486 a 141 documenti (-90.5%)
- **Categoria "Affari Generali"**: Ridotta dal 86.2% al 12.1% dei documenti
- **Documenti senza categoria**: Solo 50 su 1,724 (2.89%)
- **Tipo documento sconosciuto**: Solo 39 documenti (2.25%)

### Scoperte Importanti
- **Spesa totale analizzata**: 1.273.630.779,03 €
- **Indice concentrazione HHI**: 6835.71 (molto elevato)
- **Top fornitore**: "NON IDENTIFICATO" (oltre 1 miliardo €)
- **CIG Fantasma**: 290 atti contabili senza CIG tracciabile
- **Beneficiari Assenti**: Oltre 1 miliardo € attribuito a "NON IDENTIFICATO"
- **Sindrome della Soglia (Smurfing)**: 4 casi identificati

### Pattern di Comportamento
- **VINCENZO BIANCARDI**: 100 atti gestiti (possibile concentrazione di potere)
- **ELISABETTA NISI**: Coinvolta in molte anomalie di smurfing
- **Top beneficiari**: "DIVERSI/NON APPLICABILE" con 100 atti

## File Principali Generati

- `CRTICALITY_TIMELINE.md`: Cronologia delle criticità e miglioramenti
- `PROCEDURAL_BEHAVIOR_OVERVIEW.md`: Visione olistica del comportamento procedurale
- `data/avella/albo_download/report/`: Cartella contenente tutti i report dettagliati
- `data/avella/albo_download/atti_parsed.csv`: Dati estratti dagli atti
- `data/avella/albo_download/documenti_corpus.jsonl`: Corpus di documenti per RAG

## Comandi Principali

- `python run.py pipeline --ente avella --skip-scrape`: Esegue l'intero pipeline di analisi
- `python run.py analyze --ente avella`: Esegue solo l'analisi dei documenti
- `python run.py audit --ente avella`: Esegue solo il controllo di audit
- `python run.py build-kg --ente avella`: Costruisce il grafo della conoscenza

## Criticità Identificate

1. **Concentrazione di potere**: Uno solo RUP gestisce 100 atti
2. **Mancata tracciabilità**: Solo 39.1% di documenti con CIG
3. **Tempi procedurali lunghi**: 203 giorni medi per approvazione
4. **Mancata identificazione controparti**: Elevata percentuale di "NON IDENTIFICATO"
5. **Concentrazione economica eccessiva**: HHI di 6835.71

## Azioni Consigliate

1. **Implementare sistemi di controllo**: Blocco automatico per documenti senza CIG/CUP
2. **Ridurre concentrazione di potere**: Distribuire carichi di lavoro tra più RUP
3. **Migliorare identificazione controparti**: Processo di verifica obbligatoria
4. **Automatizzare controlli antifrode**: Sistemi di monitoraggio continuo
5. **Ottimizzare tempi procedurali**: Ridurre i 203 giorni medi di approvazione
# Albo Pretorio Audit & Digital Twin Pipeline

[![CI](https://github.com/pietroscik/albo-pretorio-audit-delivery/actions/workflows/ci.yml/badge.svg)](https://github.com/pietroscik/albo-pretorio-audit-delivery/actions/workflows/ci.yml)

Un sistema avanzato basato su AI per l'estrazione, la classificazione e l'analisi forense dei documenti pubblicati negli Albi Pretori dei Comuni italiani (Delibere, Determine, Ordinanze, ecc.).

Il sistema si allinea agli standard normativi di AgID, supportando la validazione delle firme digitali (PAdES/CAdES), la generazione di Legal URN (standard Normeinrete) e la costruzione di un "Digital Twin" dei procedimenti amministrativi.

## 🌟 Funzionalità Principali

*   **Estrazione Multimodale:** Estrazione testuale nativa da PDF tramite `pypdfium2`, OCR fallback dinamico tramite `pytesseract` e integrazione con Mistral OCR per i documenti più complessi.
*   **Entity Extraction Ibrida (RegEx + LLM):** Identificazione precisa di CIG, CUP, Importi (numerici e in lettere), Attori (RUP, Beneficiari), riferimenti normativi e competenze del personale. L'LLM (Google Gemini) interviene sui casi ad alta ambiguità.
*   **Classificazione Machine Learning:** Motore di classificazione basato su `RandomForestClassifier` e `TfidfVectorizer` per categorizzare gli atti. Include un meccanismo di **Active Learning** (Feedback Loop) tramite file Excel e **regole di classificazione avanzate** per migliorare l'accuratezza.
*   **Digital Twin & Audit:** Costruzione di procedure strutturate e individuazione di anomalie (Antifrode) attraverso `procedure_builder`.
*   **Conformità Normativa:** Verifica firme digitali (file `.p7m`), verifica dell'accessibilità dei PDF e aderenza agli standard PDND / SGPA.
*   **Risk Assessment:** Sistema avanzato di valutazione del rischio per identificare potenziali criticità nei procedimenti amministrativi.
*   **Analisi Attuariale:** Modulo per calcolare provvigioni e rischi finanziari legati ai procedimenti amministrativi.
*   **KPI Manageriali:** Calcolo di indicatori chiave di performance per la gestione dei procedimenti amministrativi.
*   **Post-processing Avanzato:** Sistema di correzione e affinamento dei risultati della classificazione automatica.
*   **Risoluzione Entità Avanzata:** Algoritmi sofisticati per la risoluzione delle entità coinvolte nei procedimenti amministrativi.
*   **Validazione Finanziaria:** Sistema di controllo e validazione degli aspetti finanziari dei documenti pubblicati.

## 📂 Struttura del Progetto

*   `run.py`: Entry point universale per tutti i comandi (Windows/Linux).
*   `src/delibere_comunali/`: Package principale con moduli Python.
    *   `scraping/`: Moduli per lo scraping (new_albo_scraper)
    *   `parsing/`: Moduli per il parsing (analyze_albo)
    *   `cli/`: Comandi CLI (run_pipeline, app_control_room, scripts wrapper)
    *   `rag/`: Moduli RAG (rag_app, rag_chat)
    *   `models/`: Moduli per modellazione dati
    *   `utils/`: Utility (cache, config, logger, ecc.)
    *   `processing/`: Moduli per post-elaborazione e audit
    *   `risk_assessment/`: Moduli per la valutazione del rischio
    *   `actuarial_analysis/`: Moduli per l'analisi attuariale
    *   `management_kpi/`: Moduli per il calcolo dei KPI manageriali
*   `scripts/`: Script di utilità legacy e avanzati (build_knowledge_graph, analyze_topology, advanced_resolution, ecc.).
*   `data/{ente}/`: Cartelle contenenti gli output per ogni ente.

## 🚀 Come avviare la Pipeline

### Entry Point Universale
Il modo consigliato è usare `run.py` che funziona su **Windows e Linux**:

**Esecuzione completa (Consigliata):**
```bash
# Windows (Git Bash) e Linux
python run.py pipeline --ente nome_del_comune

# Oppure usando il comando installato (dopo pip install -e .)
albo-pretorio pipeline --ente nome_del_comune
```

**Comandi diretti:**
```bash
python run.py scrape --ente baiano --use-llm
python run.py analyze --ente baiano --force
python run.py control-room  # Avvia la dashboard Streamlit
python run.py risk-assessment --ente baiano  # Valutazione del rischio
python run.py actuarial-analysis --ente baiano  # Analisi attuariale
python run.py management-kpi --ente baiano  # Calcolo KPI manageriali
python run.py post-process-classification --ente baiano  # Post-processing classificazione
python run.py apply-corrections --ente baiano  # Applica correzioni da feedback
```

**Nuovi comandi disponibili:**
```bash
python run.py risk-assessment --ente <nome>                    # Valutazione del rischio
python run.py actuarial-analysis --ente <nome>                # Analisi attuariale
python run.py management-kpi --ente <nome>                     # Calcolo KPI manageriali
python run.py post-process-classification --ente <nome>       # Post-processing avanzato
python run.py apply-corrections --ente <nome>                 # Applica correzioni
python run.py audit --ente <nome>                             # Engine di audit avanzato
python run.py advanced-resolution --ente <nome>               # Risoluzione avanzata entità
python run.py finance-validate --ente <nome>                  # Validazione finanziaria
python run.py visualize-graph --ente <nome>                   # Visualizzazione grafica
```

**Esempi di utilizzo avanzato:**
```bash
# Esegui pipeline completa con skip ML
python run.py pipeline --ente baiano --skip-ml

# Esegui solo analisi di rischio con output dettagliato
python run.py risk-assessment --ente baiano --verbose

# Analisi attuariale con specifici parametri
python run.py actuarial-analysis --ente baiano --alpha 0.05 --beta 2.0

# Post-processing con applicazione di regole specifiche
python run.py post-process-classification --ente baiano --apply-rules

# Dashboard Streamlit con opzioni avanzate
streamlit run src/delibere_comunali/cli/app_control_room.py -- --ente baiano
```

**Opzioni dell'Orchestratore:**
*   `--ente <nome>`: Specifica il comune da analizzare (es. `avella`, `baiano`).
*   `--skip-ml`: Salta la fase di addestramento e predizione del Machine Learning.
*   `--use-llm`: Abilita le chiamate API a Google Gemini per i documenti complessi o la lettura dei quadri economici (Vision).
*   `--force`: Ignora la cache dei PDF già elaborati e forza la ri-estrazione.
*   `--strict-validation`: Interrompe la pipeline se rileva warning nei dati esportati.

## 📊 Formati di Output

Il sistema genera molteplici artefatti all'interno della cartella `data/{ente}/albo_download/`:
1.  **`albo_analisi.xlsx`**: Il file Excel principale per la rendicontazione. Include fogli specifici per KPI, top fornitori, e i fogli `revisione_ml` e `anomalie_da_addestrare` per il feedback umano.
2.  **`atti_parsed.csv`**: Raggruppamento per atto amministrativo.
3.  **`documenti_features.csv`**: Vettorizzazione delle caratteristiche testuali per l'addestramento del Machine Learning.
4.  **`documenti_corpus.jsonl`**: Corpus testuale strutturato, pronto per essere ingerito in database vettoriali o sistemi RAG (Retrieval-Augmented Generation).
5.  **`procedures.json` / `anomalies.json`**: Dump della struttura del Digital Twin.
6.  **File aggiuntivi per le nuove funzionalità:** Includono report di rischio, analisi attuariali e KPI manageriali.

## 🔧 Requisiti di Sistema

*   Python 3.9+
*   Tesseract OCR installato nel sistema operativo.
*   Librerie necessarie (vedi `requirements.txt`): `pandas`, `scikit-learn`, `pypdfium2`, `pytesseract`, `joblib`, `google-generativeai`, `seaborn`, `plotly`, `faiss-cpu`, `streamlit`.
*   Variabili d'ambiente richieste (nel file `.env`):
    *   `GOOGLE_API_KEY`: Necessaria se si utilizza il flag `--use-llm`.

## ⚙️ Configurazione Ambiente

### 1. Installazione dipendenze Python

```bash
# Installa il pacchetto con tutte le dipendenze (consigliato)
pip install -e ".[dev]"

# Oppure via requirements.txt
pip install -r requirements.txt
```

### 2. Installazione Tesseract OCR

```bash
# Ubuntu / Debian
sudo apt-get install tesseract-ocr tesseract-ocr-ita

# macOS
brew install tesseract tesseract-lang

# Windows
# Scarica il programma di installazione da: https://github.com/UB-Mannheim/tesseract/wiki
# e aggiungi il percorso d'installazione alla variabile d'ambiente PATH
```

### 3. Configurazione variabili d'ambiente

```bash
# Copia il template .env.example e compila i valori
cp .env.example .env
```

Apri `.env` e inserisci almeno la tua `GOOGLE_API_KEY` se vuoi usare il flag `--use-llm`.  
Tutte le altre variabili sono opzionali e hanno valori di default ragionevoli.