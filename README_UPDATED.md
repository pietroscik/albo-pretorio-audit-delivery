# 🏛️ Albo Pretorio Intelligence & Audit Delivery

Piattaforma **RegTech** avanzata per l'analisi forense, l'estrazione semantica e la ricerca intelligente (RAG) sugli atti amministrativi degli Enti Locali (Determine, Delibere, Avvisi, ecc.).

## 🌟 Funzionalità Principali

- 🧠 **Estrazione Intelligente NLP/Regex**: Parsing massivo dei PDF (incluso OCR dinamico) per l'estrazione di importi, RUP, beneficiari, CIG, CUP e classificazione degli atti.
- 🤖 **Assistente RAG Multi-Tenant**: Motore di ricerca conversazionale basato su LLM (Gemini/Mistral) e FAISS, in grado di rispondere a domande ispettive citando le fonti esatte.
- 🎯 **Domain Filtering (Focus Contabilità)**: Filtro architetturale che isola automaticamente le delibere con rilevanza contabile/finanziaria, scartando il "rumore" amministrativo.
- 🕸️ **Knowledge Graph Relazionale**: Visualizzazione interattiva delle relazioni (es. RUP -> Atto -> Beneficiario).
- 🚨 **Motore Antifrode**: Rilevamento automatico di frazionamenti artificiosi, elusioni di soglia (Smurfing), CIG fantasma e anomalie temporali.
- 🧑‍🏫 **Audit HITL (Human-in-the-loop)**: Interfaccia per la validazione umana dei dati estratti e riaddestramento continuo del modello di Machine Learning (Active Learning).

## 🚀 Installazione e Configurazione

1. **Clona il repository e crea l'ambiente virtuale:**
   ```bash
   python -m venv .venv
   source .venv/Scripts/activate  # Windows
   ```
2. **Installa le dipendenze:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Configura le variabili d'ambiente:**
   Crea un file `.env` nella directory principale inserendo:
   ```env
   GOOGLE_API_KEY=la_tua_api_key_gemini
   MISTRAL_API_KEY=la_tua_api_key_mistral
   ```

## 🛠️ Utilizzo della Piattaforma

Il sistema si compone di diversi moduli eseguibili indipendentemente:

### 1. Esecuzione della Pipeline di Analisi
Per scaricare, analizzare e indicizzare i documenti di un Ente (es. `baiano`):
```bash
python run_pipeline.py --ente baiano
```
*Nota: usa `--use-llm` per forzare l'estrazione dei metadati complessi tramite Gemini.*

### 2. Avvio della Control Room (Dashboard Direzionale)
Interfaccia per l'analisi visiva, l'Audit HITL e il Benchmarking:
```bash
python -m streamlit run app_control_room.py
```

### 3. Avvio dell'Assistente RAG
Applicazione standalone per interrogare il corpus documentale tramite IA:
```bash
python -m streamlit run rag_app.py
```
*(Oppure naviga direttamente alla Control Room e apri il modulo Assistente IA integrato).*

### 4. Manutenzione del Modello ML
Per riaddestrare il classificatore Random Forest globale basandosi sui feedback umani:
```bash
python train_model.py --base data/baiano/albo_download
```

## 📂 Struttura Dati
Tutti i dati, i PDF scaricati, i database CSV (`allegati_parsed.csv`) e gli indici vettoriali FAISS sono isolati gerarchicamente nella cartella `data/{nome_ente}/albo_download/`.