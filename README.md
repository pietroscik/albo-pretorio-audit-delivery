# Albo Pretorio Audit & Digital Twin Pipeline

Un sistema avanzato basato su AI per l'estrazione, la classificazione e l'analisi forense dei documenti pubblicati negli Albi Pretori dei Comuni italiani (Delibere, Determine, Ordinanze, ecc.).

Il sistema si allinea agli standard normativi di AgID, supportando la validazione delle firme digitali (PAdES/CAdES), la generazione di Legal URN (standard Normeinrete) e la costruzione di un "Digital Twin" dei procedimenti amministrativi.

## 🌟 Funzionalità Principali

*   **Estrazione Multimodale:** Estrazione testuale nativa da PDF tramite `pypdfium2`, OCR fallback dinamico tramite `pytesseract` e integrazione con Mistral OCR per i documenti più complessi.
*   **Entity Extraction Ibrida (RegEx + LLM):** Identificazione precisa di CIG, CUP, Importi (numerici e in lettere), Attori (RUP, Beneficiari), riferimenti normativi e competenze del personale. L'LLM (Google Gemini) interviene sui casi ad alta ambiguità.
*   **Classificazione Machine Learning:** Motore di classificazione basato su `RandomForestClassifier` e `TfidfVectorizer` per categorizzare gli atti. Include un meccanismo di **Active Learning** (Feedback Loop) tramite file Excel.
*   **Digital Twin & Audit:** Costruzione di procedure strutturate e individuazione di anomalie (Antifrode) attraverso `procedure_builder`.
*   **Conformità Normativa:** Verifica firme digitali (file `.p7m`), verifica dell'accessibilità dei PDF e aderenza agli standard PDND / SGPA.

## 📂 Struttura del Progetto

*   `run.py`: Entry point universale per tutti i comandi (Windows/Linux).
*   `src/delibere_comunali/`: Package principale con moduli Python.
    *   `scraping/`: Moduli per lo scraping (new_albo_scraper)
    *   `parsing/`: Moduli per il parsing (analyze_albo)
    *   `cli/`: Comandi CLI (run_pipeline, app_control_room, scripts wrapper)
    *   `rag/`: Moduli RAG (rag_app, rag_chat)
    *   `models/`: Modelli dati
    *   `utils/`: Utility (cache, config, logger, ecc.)
*   `scripts/`: Script di utilità legacy (build_knowledge_graph, analyze_topology, ecc.).
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

Il modo consigliato per avviare il sistema è utilizzare l'orchestratore, che gestirà in automatico le dipendenze tra i vari script.

**Esecuzione completa (Consigliata):**
```bash
python run.py pipeline --ente nome_del_comune
```

**Comandi diretti:**
```bash
python run.py scrape --ente baiano --use-llm
python run.py analyze --ente baiano --force
python run.py control-room  # Avvia la dashboard Streamlit
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

## 🔧 Requisiti di Sistema

*   Python 3.9+
*   Tesseract OCR installato nel sistema operativo.
*   Librerie necessarie (vedi `requirements.txt`): `pandas`, `scikit-learn`, `pypdfium2`, `pytesseract`, `joblib`, `google-generativeai`.
*   Variabili d'ambiente richieste (nel file `.env`):
    *   `GOOGLE_API_KEY`: Necessaria se si utilizza il flag `--use-llm`.