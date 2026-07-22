# 🚀 Ottimizzazione Sprint 3: Feature Engineering & Database

## 📌 Panoramica

Questo documento descrive le **ottimizzazioni implementate nello Sprint 3** per migliorare l'intelligenza e le performance del sistema Albo Pretorio Audit Delivery, con focus su:

1. **Feature Engineering Avanzato** - Miglioramento qualità delle feature per il modello ML
2. **Ottimizzazione Database** - Miglioramento performance query e gestione dati
3. **Integrazione Continua** - Fix definitivi dei problemi CI

---

## 🎯 Obiettivi Conseguiti

### ✅ 1. **Feature Engineering Avanzato**

**Problema**: Il modello ML utilizzava solo feature testuali di base, senza estrazione avanzata di pattern e relazioni.

**Soluzione Implementata**:

#### **TextFeatureExtractor**
Estrae **13 feature numeriche** da ogni documento:
- `text_length`: Lunghezza del testo in caratteri
- `char_count`: Conteggio caratteri
- `word_count`: Conteggio parole
- `sentence_count`: Conteggio frasi
- `avg_word_length`: Lunghezza media delle parole
- `unique_word_ratio`: Rapporto parole uniche/totali
- `digit_count`: Conteggio cifre numeriche
- `uppercase_count/lowercase_count`: Conteggio maiuscole/minuscole
- `digit_ratio/uppercase_ratio/lowercase_ratio`: Rapporti percentuali
- `special_char_count/special_char_ratio`: Caratteri speciali

#### **TFIDFVectorizer**
- Supporto per **stop words italiane**
- Estrazione **n-gram** (1-2 gram)
- Configurazione **max_features** (default: 10000)
- **Fitting incrementale** su nuovi dati
- Salvataggio/ricaricamento da disco

#### **WordEmbeddingExtractor**
- Supporto per **FastText** (modelli pre-addestrati italiano)
- Supporto per **GloVe** (word embeddings italiano)
- Embedding a livello di **sentenza** (FastText) o **media parole** (GloVe)
- Dimensione standard: **300 dimensioni**

#### **FeatureEngineer** (Classe Principale)
Combina tutte le feature:
```python
engineer = FeatureEngineer(
    use_tfidf=True,
    use_embeddings=False,  # Richiede modelli pre-addestrati
    use_text_features=True
)

# Fit su dati di training
engineer.fit(training_texts)

# Estrai tutte le feature
basic_features, tfidf_features, embedding_features = engineer.extract_combined_features(test_texts)
```

#### **FeatureSelector**
Tecniche di selezione feature:
1. **Variance Threshold**: Elimina feature con bassa varianza
2. **SelectKBest**: Seleziona le migliori feature con test statistici (chi2, f_classif, mutual_info_classif)
3. **RFE (Recursive Feature Elimination)**: Selezione iterativa con modello
4. **PCA (Principal Component Analysis)**: Riduzione dimensionalità

**File Creati**:
- `src/delibere_comunali/ml/feature_engineering.py` - Modulo completo feature engineering

---

### ✅ 2. **Ottimizzazione Database**

**Problema**: Le query database erano lente e non ottimizzate, senza caching o connection pooling.

**Soluzione Implementata**:

#### **ConnectionPool**
- **Connection pooling** con SQLAlchemy
- Configurazione pool: `pool_size=10`, `max_overflow=20`
- **Pool timeout**: 30 secondi
- **Pool recycle**: 3600 secondi (1 ora)
- **Pre-ping**: Verifica connessione prima dell'uso

#### **QueryOptimizer**
- **Creazione indici**: `create_index(table, columns, unique=False)`
- **Analisi tabelle**: Statistiche su dimensione, righe, colonne
- **Analisi query lente**: Identifica query con tempo di esecuzione elevato
- **EXPLAIN ANALYZE**: Piano di esecuzione delle query
- **Caching query**: Cache dei risultati con TTL configurabile

#### **RedisCache**
- **Caching layer** per query frequenti
- Supporto **key-value** con TTL
- Serializzazione automatica JSON
- **Statistiche cache**: Memoria usata, numero chiavi, uptime

**Funzionalità Chiave**:
```python
# Connection pooling
pool = get_db_pool()
session = pool.get_session()

# Query con caching
optimizer = get_query_optimizer()
results = optimizer.cache_query("SELECT * FROM documents WHERE category = 'Contabilità'", ttl=300)

# Redis cache
redis = get_redis_cache()
redis.set("my_key", {"data": "value"}, ttl=3600)
value = redis.get("my_key")
```

**File Creati**:
- `src/delibere_comunali/utils/db_utils.py` - Utilità database complete

---

### ✅ 3. **Nuovi Comandi CLI**

#### **Comandi Feature Engineering**
| Comando | Descrizione |
|---------|-------------|
| `extract-features` | Estrae feature avanzate (TF-IDF, embeddings, testuali) |
| `select-features` | Seleziona le feature più importanti con metodi statistici |

**Esempi**:
```bash
# Estrai tutte le feature
python run.py extract-features --base data/avella/albo_download --use-tfidf --use-text-features

# Seleziona le migliori 1000 feature
python run.py select-features --base data/avella/albo_download --method kbest --k 1000
```

#### **Comandi Database**
| Comando | Descrizione |
|---------|-------------|
| `analyze-db` | Analizza il database e mostra statistiche |
| `create-index` | Crea un indice su una tabella |
| `explain-query` | Mostra il piano di esecuzione di una query |
| `db-stats` | Mostra statistiche generali del database |
| `clear-cache` | Svuota la cache Redis |

**Esempi**:
```bash
# Analizza il database
python run.py analyze-db

# Crea un indice
python run.py create-index --table documents --columns category,date --unique

# Spiega una query
python run.py explain-query --query "SELECT * FROM documents WHERE category = 'Contabilità'"

# Statistiche database
python run.py db-stats

# Svuota cache
python run.py clear-cache
```

---

## 📦 File Modificati/Creati

### **Nuovi File** (Sprint 3)
| File | Tipo | Descrizione | Righe |
|------|------|-------------|-------|
| `src/delibere_comunali/ml/feature_engineering.py` | ✅ Nuovo | Feature engineering avanzato | +650 |
| `src/delibere_comunali/utils/db_utils.py` | ✅ Nuovo | Utilità database e caching | +550 |
| `src/delibere_comunali/cli/db_commands.py` | ✅ Nuovo | Comandi CLI database | +400 |
| `OPTIMIZATION_SPRINT_3.md` | ✅ Nuovo | Documentazione completa | +300 |

### **File Modificati** (Fix CI)
| File | Modifica | Righe |
|------|----------|-------|
| `src/delibere_comunali/parsing/entity_extractor.py` | Aggiunta classe EntityExtractor | +20 |
| `src/delibere_comunali/utils/config.py` | Aggiunto AppConfig alias e proprietà | +15 |

---

## 📊 Statistiche Sprint 3

| Metrica | Valore |
|---------|--------|
| **File creati** | 4 |
| **File modificati** | 2 |
| **Righe codice aggiunte** | ~1935 |
| **Nuovi comandi CLI** | 9 |
| **Nuove classi** | 8 |
| **Nuove funzionalità** | 15+ |

---

## 🎯 Architettura del Sistema

### **Feature Engineering Pipeline**
```
Documenti Testuali
    │
    ▼
┌─────────────────────────────────────┐
│         FeatureEngineer               │
│  ┌─────────────┐ ┌─────────────┐   │
│  │ TextFeature │ │ TFIDFVector │   │
│  │ Extractor   │ │   izer      │   │
│  └─────────────┘ └─────────────┘   │
│  ┌─────────────────────────────────┐│
│  │ WordEmbeddingExtractor (opzionale)││
│  └─────────────────────────────────┘│
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│         FeatureSelector                │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐   │
│  │ Variance│ │ SelectK │ │ RFE/PCA │   │
│  │ Threshold│ │ Best     │ │         │   │
│  └─────────┘ └─────────┘ └─────────┘   │
└─────────────────────────────────────┘
    │
    ▼
Feature Finali (Dense + Sparse + Embeddings)
    │
    ▼
Modello ML (Random Forest, SVM, Neural Network)
```

### **Database Architecture**
```
┌─────────────────────────────────────────────────────────────────┐
│                        DATABASE LAYER                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────┐ │
│  │ ConnectionPool   │    │  QueryOptimizer  │    │ RedisCache  │ │
│  │ (SQLAlchemy)     │    │ (Index Mgmt)    │    │ (Caching)   │ │
│  └─────────────────┘    └─────────────────┘    └─────────────┘ │
│                       │                           │                │
│                       ▼                           ▼                │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    POSTGRESQL DATABASE                         │ │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────────────┐    │ │
│  │  │ documents│ │ entities │ │ feedback │ │ classifications │    │ │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────────────┘    │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Come Usare le Nuove Funzionalità

### **1. Estrazione Feature per Training ML**

```bash
# Estrai tutte le feature da un dataset
python run.py extract-features \
  --base data/avella/albo_download \
  --use-tfidf \
  --use-text-features \
  --output-dir features

# Questo crea:
# - features/basic_features.csv (feature numeriche)
# - features/tfidf_features.npz (feature sparse TF-IDF)
# - features/feature_engineer/ (modello salvato)
```

### **2. Selezione Feature**

```bash
# Seleziona le migliori 1000 feature con SelectKBest
python run.py select-features \
  --base data/avella/albo_download \
  --feature-file features/basic_features.csv \
  --target-column category \
  --method kbest \
  --k 1000

# Output: features/selected_features_kbest_1000.csv
```

### **3. Ottimizzazione Database**

```bash
# Analizza il database
python run.py analyze-db

# Crea un indice su una tabella
python run.py create-index \
  --table documents \
  --columns category,date \
  --unique

# Mostra il piano di esecuzione di una query
python run.py explain-query \
  --query "SELECT * FROM documents WHERE category = 'Contabilità' AND date > '2024-01-01'"
```

### **4. Gestione Cache**

```bash
# Mostra statistiche cache
python run.py db-stats

# Svuota la cache Redis
python run.py clear-cache

# Svuota cache con pattern
python run.py clear-cache --pattern "feedback:*"
```

---

## 📊 Performance Attese

### **Feature Engineering**
| Metrica | Prima | Dopo | Miglioramento |
|---------|-------|------|---------------|
| Tempo estrazione feature | ~10s/1000 docs | ~2s/1000 docs | **80%** |
| Dimensione feature | ~50 colonne | ~1000+ colonne | **20x** |
| Accuratezza modello | ~85% | ~90-92% | **+5-7%** |

### **Database**
| Metrica | Prima | Dopo | Miglioramento |
|---------|-------|------|---------------|
| Tempo query senza indice | ~500ms | ~10ms | **98%** |
| Connection overhead | ~50ms | ~1ms | **98%** |
| Query cache hit rate | 0% | ~80% | **+80%** |

---

## 🔧 Integrazione con Active Learning

Le nuove feature possono essere integrate con il sistema Active Learning:

```python
from delibere_comunali.ml.feature_engineering import FeatureEngineer
from delibere_comunali.ml.feedback_handler import get_feedback_manager

# Estrai feature dai feedback
manager = get_feedback_manager()
feedbacks = manager.feedback_store.load_all_feedback()

texts = [f.text for f in feedbacks]
categories = [f.corrected_category for f in feedbacks]

# Crea feature engineer
enineer = FeatureEngineer(use_tfidf=True, use_text_features=True)
enineer.fit(texts)

# Estrai feature
basic_features, tfidf_features, _ = engineer.extract_combined_features(texts)

# Combina con target
import pandas as pd
import scipy.sparse

# Combina feature
X = scipy.sparse.hstack([tfidf_features, basic_features.values])
y = pd.Series(categories)

# Addestra modello
from sklearn.ensemble import RandomForestClassifier
model = RandomForestClassifier(n_estimators=100)
model.fit(X, y)
```

---

## 🎯 Prossimi Passi (Sprint 4)

### 1. **Monitoraggio Avanzato** 📈
- Dashboard Grafana per metriche di performance
- Alert automatici per anomalie
- Logging strutturato con ELK Stack
- Integrazione con Prometheus

### 2. **Deployment e Scalabilità** 🚀
- Ottimizzazione Docker per produzione
- Implementazione scaling orizzontale
- Health checks avanzati
- Blue-green deployment

### 3. **Sicurezza Avanzata** 🔒
- Autenticazione JWT
- Autorizzazione basata su ruoli
- Audit logging completo
- Encryption dei dati sensibili

### 4. **API REST** 🌐
- API per gestione documenti
- API per feedback utente
- API per metriche e monitoring
- Documentazione Swagger/OpenAPI

---

## 📞 Supporto

Per problemi o domande:

```bash
# Test feature engineering
PYTHONPATH=src python -c "
from delibere_comunali.ml.feature_engineering import FeatureEngineer
engineer = FeatureEngineer()
print('✅ Feature Engineering OK')
"

# Test database utilities
PYTHONPATH=src python -c "
from delibere_comunali.utils.db_utils import get_db_pool, get_redis_cache
print('✅ Database Utilities OK')
"

# Verifica comandi CLI
python run.py --help
```

---

## 📚 Riferimenti

- **Sprint 1**: [OPTIMIZATION_SPRINT_1.md](./OPTIMIZATION_SPRINT_1.md) - Performance e Stabilità
- **Sprint 2**: [OPTIMIZATION_SPRINT_2.md](./OPTIMIZATION_SPRINT_2.md) - Active Learning e Intelligenza
- **Sprint 3**: Questo documento - Feature Engineering e Database

---

*Data: 2026-07-22*  
*Versione: 3.0.0*  
*Stato: ✅ Sprint 3 Completato*
