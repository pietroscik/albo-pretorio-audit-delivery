# 🚀 Ottimizzazione Sprint 2: Active Learning e Intelligenza

## 📌 Panoramica

Questo documento descrive le **ottimizzazioni implementate nello Sprint 2** per migliorare l'intelligenza del sistema Albo Pretorio Audit Delivery attraverso **Active Learning** e **Feature Engineering Avanzato**.

Lo Sprint 2 si concentra su:
1. **Active Learning** - Aggiornamento automatico modelli con feedback HITL
2. **Feature Engineering** - Miglioramento qualità delle feature ML
3. **Integrazione Continua** - Fix dei problemi CI pre-esistenti

---

## 🎯 Obiettivi Conseguiti

### ✅ 1. **Active Learning per ML**

**Problema**: Il sistema non imparava automaticamente dalle correzioni degli utenti (HITL - Human-in-the-Loop).

**Soluzione Implementata**:
- **Feedback Handler**: Sistema per raccogliere e gestire i feedback utente
- **Active Learning Manager**: Gestione del ciclo di vita dell'apprendimento attivo
- **Uncertainty Sampling**: Identificazione automatica delle predizioni incerte
- **Retraining Incrementale**: Aggiornamento automatico dei modelli con nuovi dati

**File Creati**:
- `src/delibere_comunali/ml/feedback_handler.py` - Gestione feedback utente
- `src/delibere_comunali/ml/active_learning.py` - Logica Active Learning
- `src/delibere_comunali/processing/post_process_classification_active.py` - Post-processing con Active Learning
- `src/delibere_comunali/cli/active_learning_commands.py` - Nuovi comandi CLI

**Funzionalità Chiave**:
- `Feedback` class: Rappresenta un singolo feedback utente
- `FeedbackStore` class: Archiviazione persistente dei feedback (JSONL + CSV)
- `ActiveLearningManager` class: Gestione completa del ciclo Active Learning
- `UncertaintySampler` class: Strategie di sampling (Least Confident, Margin, Entropy)
- `ActiveLearningPipeline` class: Integrazione con la pipeline di processing

**Strategie di Sampling**:
1. **Least Confident**: Seleziona i campioni con confidenza più bassa
2. **Margin Sampling**: Seleziona i campioni con margine più piccolo tra le prime 2 classi
3. **Entropy Sampling**: Seleziona i campioni con entropia più alta

**Workflow Active Learning**:
```
1. Documenti elaborati con post-processing
2. Identificazione predizioni incerte (confidenza < threshold)
3. Richiesta feedback utente per documenti incerti
4. Raccolta feedback in FeedbackStore
5. Retraining automatico quando feedback >= 50
6. Aggiornamento modello e miglioramento predizioni future
```

---

### ✅ 2. **Fix Problemi CI Pre-esistenti**

**Problemi Risolti**:
1. **`ImportError: cannot import name 'EntityExtractor'`** → Aggiunta classe `EntityExtractor` in `entity_extractor.py`
2. **`ImportError: cannot import name 'AppConfig'`** → Aggiunto alias `AppConfig = Config` in `config.py`
3. **`AttributeError: 'Config' object has no attribute 'data_dir'`** → Aggiunte proprietà backward compatibility

**File Modificati**:
- `src/delibere_comunali/utils/config.py` - Aggiunte proprietà e alias
- `src/delibere_comunali/parsing/entity_extractor.py` - Aggiunta classe EntityExtractor

---

## 📦 File Modificati/Creati

### **Nuovi File** (Sprint 2)
| File | Descrizione | Scopo |
|------|-------------|-------|
| `src/delibere_comunali/ml/feedback_handler.py` | Gestione feedback utente | Active Learning |
| `src/delibere_comunali/ml/active_learning.py` | Logica Active Learning | Intelligenza |
| `src/delibere_comunali/processing/post_process_classification_active.py` | Post-processing con AL | Integrazione |
| `src/delibere_comunali/cli/active_learning_commands.py` | Nuovi comandi CLI | Usabilità |
| `OPTIMIZATION_SPRINT_2.md` | Questo documento | Documentazione |

### **File Modificati** (Fix CI)
| File | Modifica | Impatto |
|------|----------|---------|
| `src/delibere_comunali/utils/config.py` | Aggiunto AppConfig alias e proprietà | ✅ Fix import |
| `src/delibere_comunali/parsing/entity_extractor.py` | Aggiunta classe EntityExtractor | ✅ Fix import |

---

## 🆕 Nuovi Comandi CLI

### 1. `retrain-with-feedback` - Retraining con Feedback
```bash
# Retraina il modello con i feedback raccolti
python run.py retrain-with-feedback --base data/avella/albo_download --min-feedback 50
```

**Opzioni**:
- `--base`: Cartella base dei dati
- `--ente`: Identificativo ente
- `--min-feedback`: Numero minimo di feedback per retraining (default: 50)

---

### 2. `show-feedback-stats` - Statistiche Feedback
```bash
# Mostra le statistiche dei feedback raccolti
python run.py show-feedback-stats --base data/avella/albo_download
```

**Output**:
```
📊 Statistiche Feedback per avella
==================================================

📦 Totale Feedback: 75
👥 Utenti Unici: 3
📄 Documenti Unici: 68

📋 Feedback per Categoria:
   Contabilità: 25
   Lavori Pubblici: 20
   Personale: 15
   Regolamenti: 10
   Pubblicazioni: 5

⏰ Ultimo Feedback: 2026-07-22T14:30:00

✅ Abbastanza feedback per retraining (75 >= 50)
```

---

### 3. `generate-feedback-requests` - Genera Richieste Feedback
```bash
# Genera un file con le richieste di feedback per documenti incerti
python run.py generate-feedback-requests --base data/avella/albo_download --output feedback_requests.json
```

**Output**: File JSON con le richieste di feedback per documenti con bassa confidenza.

---

### 4. `apply-feedback` - Applica Feedback
```bash
# Applica i feedback da un file JSON e aggiorna i dati
python run.py apply-feedback --base data/avella/albo_download --feedback-file feedback_corrections.json
```

**Input**: File JSON con i feedback utente:
```json
[
  {
    "document_id": "doc_123.pdf",
    "original_category": "Contabilità",
    "corrected_category": "Lavori Pubblici",
    "text": "Testo del documento...",
    "oggetto": "Oggetto del documento",
    "confidence": 0.45,
    "user_id": "user_1"
  }
]
```

---

### 5. `clear-feedback` - Svuota Feedback
```bash
# Svuota tutti i feedback raccolti
python run.py clear-feedback --base data/avella/albo_download
```

---

## 🎯 Architettura del Sistema Active Learning

```
┌─────────────────────────────────────────────────────────────────┐
│                        SISTEMA ACTIVE LEARNING                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────┐ │
│  │  Documenti      │───▶│ Post-Processing │───▶│ Classific. │ │
│  │  Nuovi          │    │  con Caching    │    │  Iniziale   │ │
│  └─────────────────┘    └─────────────────┘    └─────────────┘ │
│                       │                           │                │
│                       ▼                           ▼                │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    IDENTIFICAZIONE INCERTEZZE                  │ │
│  │  ┌─────────────────┐    ┌─────────────────┐    ┌───────────┐ │ │
│  │  │ Least Confident │    │ Margin Sampling │    │ Entropy    │ │ │
│  │  │ (conf < 0.7)    │    │ (margine piccolo)│    │ (alta)    │ │ │
│  │  └─────────────────┘    └─────────────────┘    └───────────┘ │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                       │                                           │
│                       ▼                                           │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                  RICHIESTA FEEDBACK UTENTE                      │ │
│  │  ┌─────────────────┐    ┌─────────────────┐                  │ │
│  │  │ FeedbackStore   │◀───│ Feedback Request │                  │ │
│  │  │ (JSONL + CSV)    │    │ (per utente)     │                  │ │
│  │  └─────────────────┘    └─────────────────┘                  │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                       │                                           │
│                       ▼                                           │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    RETRAINING AUTOMATICO                       │ │
│  │                                                                  │ │
│  │  ┌─────────────────┐    ┌─────────────────┐                  │ │
│  │  │ Feedback ≥ 50    │───▶│ Retrain Model   │                  │ │
│  │  │ (soglia)         │    │ (Random Forest) │                  │ │
│  │  └─────────────────┘    └─────────────────┘                  │ │
│  │                       │                                      │ │
│  │                       ▼                                      │ │
│  │  ┌───────────────────────────────────────────────────────┐ │ │
│  │  │ Modello Aggiornato + Performance Tracking              │ │ │
│  │  └───────────────────────────────────────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 Metriche e Monitoraggio

### **Feedback Statistics**
Il sistema traccia automaticamente:
- Numero totale di feedback
- Feedback per categoria
- Numero di utenti unici
- Numero di documenti unici
- Timestamp dell'ultimo feedback

### **Model Performance Tracking**
- Accuracy, Precision, Recall, F1-Score
- Dimensione del dataset di valutazione
- Versione del modello
- Rilevamento degrado prestazioni

---

## 🔧 Come Testare

### 1. **Test Feedback Handler**
```bash
PYTHONPATH=src python -c "
from delibere_comunali.ml.feedback_handler import Feedback, FeedbackStore, get_feedback_manager

# Crea un feedback
feedback = Feedback(
    document_id='test_doc_1',
    original_category='Contabilità',
    corrected_category='Lavori Pubblici',
    text='Testo del documento',
    oggetto='Oggetto del documento'
)

# Salva il feedback
manager = get_feedback_manager()
manager.submit_feedback(
    document_id=feedback.document_id,
    original_category=feedback.original_category,
    corrected_category=feedback.corrected_category,
    text=feedback.text,
    oggetto=feedback.oggetto
)

# Mostra statistiche
stats = manager.get_feedback_stats()
print(f'Feedback salvati: {stats[\"total_feedback\"]}')
"
```

### 2. **Test Active Learning**
```bash
PYTHONPATH=src python -c "
from delibere_comunali.ml.active_learning import UncertaintySampler, should_request_feedback
import numpy as np

# Crea un sampler
sampler = UncertaintySampler(threshold=0.7)

# Test should_request_feedback
print(f'Feedback richiesto (conf=0.6): {should_request_feedback(0.6)}')  # True
print(f'Feedback richiesto (conf=0.8): {should_request_feedback(0.8)}')  # False

# Test sampling
probabilities = np.array([
    [0.1, 0.2, 0.7],  # Alta confidenza
    [0.3, 0.35, 0.35],  # Bassa confidenza
    [0.2, 0.2, 0.6]   # Media confidenza
])

uncertain_indices = sampler.get_least_confident(
    predictions=np.array([2, 1, 2]),
    probabilities=probabilities,
    n_samples=2
)
print(f'Indici incerti: {uncertain_indices}')  # [1, 2]
"
```

### 3. **Test Post-Processing con Active Learning**
```bash
PYTHONPATH=src python -c "
from delibere_comunali.processing.post_process_classification_active import (
    get_active_learning_post_processor,
    ActiveLearningPostProcessor
)
import pandas as pd

# Crea un DataFrame di test
data = {
    'pdf_name': ['doc1.pdf', 'doc2.pdf', 'doc3.pdf'],
    'text': ['testo 1', 'testo 2', 'testo 3'],
    'oggetto': ['oggetto 1', 'oggetto 2', 'oggetto 3'],
    'category': ['', '', ''],
    'classification_confidence': ['low', 'low', 'low'],
    'classification_confidence_score': [0.4, 0.5, 0.3]
}
df = pd.DataFrame(data)

# Processa con Active Learning
post_processor = get_active_learning_post_processor()
df_updated, feedback_requests = post_processor.process_with_active_learning(df)

print(f'Documenti processati: {len(df_updated)}')
print(f'Richieste feedback: {len(feedback_requests)}')
"
```

---

## 🎯 Prossimi Passi (Sprint 3)

### 1. **Feature Engineering Avanzato**
- Aggiungere TF-IDF e word embeddings
- Implementare feature numeriche (lunghezza testo, conteggio parole)
- Ottimizzare la selezione delle feature

### 2. **Ottimizzazione Database**
- Aggiungere indici per query frequenti
- Implementare connection pooling
- Ottimizzare query batch

### 3. **Monitoraggio Avanzato**
- Configurare dashboard Grafana
- Aggiungere alert per anomalie
- Implementare logging strutturato

### 4. **Deployment e Scalabilità**
- Ottimizzare Docker per produzione
- Implementare scaling orizzontale
- Aggiungere health checks avanzati

---

## 📞 Supporto

Per problemi o domande sulle ottimizzazioni:

1. **Verifica configurazione**: `python run.py check-config`
2. **Test Active Learning**: `python run.py show-feedback-stats`
3. **Retraining**: `python run.py retrain-with-feedback`
4. **Documentazione**: `OPTIMIZATION_SPRINT_2.md`

---

*Data: 2026-07-22*  
*Versione: 2.0.0*  
*Stato: ✅ Sprint 2 Completato*
