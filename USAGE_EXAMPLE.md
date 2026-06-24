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
python run.py build-kg --base data/baiano/albo_download
```

## 3. Utilizzo RAG da codice Python
```python
from src.web.rag_chat import esegui_query_rag_core

# Interrogazione standard
risposta = esegui_query_rag_core("Quali ditte hanno vinto gli appalti della scuola?", "baiano")
print(risposta)

# Interrogazione focalizzata ESCLUSIVAMENTE sui documenti finanziari
risposta_fin = esegui_query_rag_core("Quali ditte hanno vinto gli appalti?", "baiano", only_accounting=True)
print(risposta_fin)
```

## 4. Estrazione manuale dei Metadati
```python
from pathlib import Path
from analyze_albo import extract_full_metadata

pdf_path = Path("data/baiano/albo_download/pdf/Determina_123.pdf")
metadati = extract_full_metadata(pdf_path)

print(f"RUP: {metadati['responsabile']}")
print(f"Rilevanza Finanziaria: {metadati['accounting_relevant']}")
```

## 5. Pulizia Agentica Discrezionale
```bash
# Ripulisce falsi positivi (es. "Manifesti" scambiati per atti) senza riavviare la pipeline
python run.py clean-texts --base data/baiano/  # (dopo aver spostato la logica)
```

## 6. Riaddestramento Modello
```bash
# Addestra il Random Forest dopo aver fatto validazioni in Excel
python run.py train --base data/baiano/
```