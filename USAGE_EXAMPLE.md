# 📖 Esempi Pratici d'Uso (Cookbook)

Di seguito alcuni esempi pratici per utilizzare la piattaforma via terminale o via codice.

## 1. Pipeline Automatica Base
```bash
# Scarica, estrae e analizza gli atti di un ente
python run.py pipeline --ente baiano
```

## 2. Comandi Individuali
```bash
# Estrazione dati
python run.py scrape --ente baiano --use-llm

# Analisi dati
python run.py analyze --ente baiano --force

# Costruzione knowledge graph
python run.py build-kg --ente baiano

# Control room (dashboard Streamlit)
python run.py control-room
```

## 3. Nuove Funzionalità Avanzate

### 3.1. Valutazione del Rischio
```bash
# Esegui analisi di rischio per un ente
python run.py risk-assessment --ente baiano
```

### 3.2. Analisi Attuariale
```bash
# Calcola provvigioni e rischi finanziari
python run.py actuarial-analysis --ente baiano
```

### 3.3. Calcolo KPI Manageriali
```bash
# Calcola indicatori chiave di performance
python run.py management-kpi --ente baiano
```

### 3.4. Post-processing Classificazione
```bash
# Affina i risultati della classificazione automatica
python run.py post-process-classification --ente baiano
```

### 3.5. Applicazione Correzioni da Feedback
```bash
# Applica correzioni basate su feedback umano
python run.py apply-corrections --ente baiano
```

## 4. Utilizzo RAG da codice Python
```python
from src.delibere_comunali.rag.rag_chat import esegui_query_rag_core

# Interrogazione standard
risposta = esegui_query_rag_core("Quali ditte hanno vinto gli appalti della scuola?", "baiano")
print(risposta)

# Interrogazione focalizzata ESCLUSIVAMENTE sui documenti finanziari
risposta_fin = esegui_query_rag_core("Quali ditte hanno vinto gli appalti?", "baiano", only_accounting=True)
print(risposta_fin)
```

## 5. Estrazione manuale dei Metadati
```python
from pathlib import Path
from src.delibere_comunali.parsing.analyze_albo import extract_full_metadata

pdf_path = Path("data/baiano/albo_download/pdf/Determina_123.pdf")
metadati = extract_full_metadata(pdf_path)

print(f"RUP: {metadati['responsabile']}")
print(f"Rilevanza Finanziaria: {metadati['accounting_relevant']}")
```

## 6. Pulizia Agentica Discrezionale
```bash
# Ripulisce falsi positivi (es. "Manifesti" scambiati per atti) senza riavviare la pipeline
python run.py clean-texts --ente baiano
```

## 7. Riaddestramento Modello
```bash
# Addestra il Random Forest dopo aver fatto validazioni in Excel
python run.py train --ente baiano
```

## 8. Risoluzione Avanzata delle Entità
```bash
# Esegue risoluzione avanzata delle entità coinvolte nei procedimenti
python run.py advanced-resolution --ente baiano
```

## 9. Validazione Finanziaria
```bash
# Esegue validazione degli aspetti finanziari dei documenti
python run.py finance-validate --ente baiano
```

## 10. Visualizzazione Grafica
```bash
# Avvia l'interfaccia di visualizzazione grafica
python run.py visualize-graph --ente baiano
```

## 11. Comandi Aggiuntivi Utili
```bash
# Lista completa dei comandi disponibili
python run.py

# Validazione output
python run.py validate-csv --ente baiano

# Esplorazione dati
python run.py explore --ente baiano

# Rilevamento anomalie
python run.py detect-anomalies --ente baiano
```