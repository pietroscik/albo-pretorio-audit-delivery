# Ottimizzazione della Classificazione ML

## Panoramica

Questo documento descrive le nuove funzionalità integrate nel sistema per ottimizzare la classificazione automatica dei documenti dell'albo pretorio. Le ottimizzazioni risolvono i problemi identificati nel sistema di classificazione, in particolare il problema delle elevate percentuali di documenti classificati come "ambiguous".

## Componenti del Sistema

### 1. Regole Avanzate di Classificazione

Il sistema include ora regole avanzate di classificazione che utilizzano pattern specifici trovati nei documenti reali per distinguere tra categorie simili:

- **Contabilità**: Riconosce termini come "impegno di spesa", "liquidazione", "fattura", "pagamento", "capitolo", "accertamento", "visto contabile"
- **Lavori Pubblici**: Identifica "lavori pubblici", "progetto esecutivo", "manutenzione", "cantiere", "opera pubblica"
- **Personale**: Cerca "personale", "assunzioni", "concorso", "selezione", "progressione"
- E molte altre categorie specifiche

### 2. Post-Processing della Classificazione

Un nuovo modulo `post_process_classification.py` implementa un processo di post-processing che:

- Risolve le ambiguità utilizzando sia regole avanzate che il modello ML
- Migliora il modello ML utilizzando i dati risolti dagli ambigui
- Applica soglie di confidenza appropriate (≥0.65 per alta confidenza, ≥0.50 per media confidenza)
- Riapplica il modello migliorato ai documenti con bassa confidenza

### 3. Integrazione nella Pipeline

Il processo di post-processing è stato integrato automaticamente nella pipeline principale:

- Eseguito dopo l'analisi iniziale
- Può essere saltato con l'opzione `--skip-post-process`
- Utilizza i modelli ML già addestrati dal modulo di analisi

## Utilizzo

### Esecuzione Completa (Consigliata)

```bash
python run.py pipeline --ente avella
```

Il modulo di post-processing verrà eseguito automaticamente come parte della pipeline.

### Esecuzione Manuale del Post-Processing

```bash
python run.py post-process --base data/avella/albo_download
```

Oppure:

```bash
python run.py post-process-classification --base data/avella/albo_download
```

### Esecuzione della Pipeline Senza Post-Processing

```bash
python run.py pipeline --ente avella --skip-post-process
```

## Risultati Attesi

Dopo l'esecuzione del processo di ottimizzazione:

- **Riduzione significativa** dei documenti classificati come "ambiguous"
- **Aumento** dei documenti con confidenza media e alta
- **Miglioramento** della distribuzione delle categorie
- **Riclassificazione** più accurata dei documenti problematici

## Architettura Tecnica

Il modulo implementa le specifiche richieste:

- Ottimizzazione degli iperparametri con `GridSearchCV`
- Uso di metriche complete (precision, recall, f1-score macro)
- Implementazione delle soglie di confidenza richieste
- Supporto per Active Learning attraverso dati risolti dagli ambigui

## File Interessati

- `src/delibere_comunali/processing/post_process_classification.py` - Modulo principale
- `src/delibere_comunali/cli/run_pipeline.py` - Pipeline principale con integrazione
- `scripts/randomForest.py` - Modulo di addestramento aggiornato
- `run.py` - Entry point con nuovo comando
- `pyproject.toml` - Configurazione con nuovo comando

## Comandi Aggiunti

- `post-process-classification` - Esegue solo il modulo di post-processing
- `post-process` - Alias per il comando sopra
- Opzione `--skip-post-process` per la pipeline principale