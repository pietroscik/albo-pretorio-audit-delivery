# Ottimizzazione della Dashboard Web

## Riassunto

Questa ottimizzazione trasforma la dashboard da un modulo monolitico a un sistema modulare basato su componenti riutilizzabili e oggetti dati standardizzati.

## Cambiamenti Principali

### 1. Livello Dati: Dal CSV agli Eventi Digitali

**Prima:**
- Caricamento diretto di `allegati_parsed.csv` tramite Pandas
- Accesso diretto alle colonne del DataFrame nel codice UI

**Dopo:**
- Nuovo modulo `src/delibere_comunali/web/data_loader.py`
- Astrazione del caricamento dati attraverso oggetti standardizzati:
  - `ParsedDocument` dal modulo `models.parsed_document`
  - `AdministrativeEvent` dal modulo `models.administrative_event`
- Funzioni di conversione `dataframe_to_parsed_documents()` e `dataframe_to_administrative_events()`

### 2. Livello UI: Componentizzazione dei Widget

**Prima:**
- Tutto il codice UI in un unico file `dashboard.py`
- Logica di visualizzazione mescolata con logica di business

**Dopo:**
- Nuova directory `src/delibere_comunali/web/components/`
- Componenti modulari:
  - `financial_metrics.py`: Metriche finanziarie e KPI
  - `tabular_view.py`: Visualizzazione tabellare
  - `knowledge_graph.py`: Visualizzazione interattiva del Knowledge Graph
- Dashboard ridotta a orchestratore di componenti

### 3. Livello Visuale: Knowledge Graph Navigabile

**Implementato:**
- Visualizzazione interattiva del Knowledge Graph usando `pyvis`
- Statistiche delle entità (RUP, beneficiari, documenti)
- Grafico delle relazioni tra entità
- Supporto per navigazione e filtro delle connessioni

## Benefici

1. **Mantenibilità**: Ogni componente può essere sviluppato e testato separatamente
2. **Riutilizzo**: I componenti possono essere riutilizzati in altre dashboard
3. **Standardizzazione**: Tutti i dati sono ora basati sugli oggetti standard `ParsedDocument` e `AdministrativeEvent`
4. **Scalabilità**: Facile aggiunta di nuovi widget senza modificare il core della dashboard
5. **Chiarezza**: Separazione netta tra logica di business e logica di presentazione

## Come Estendere

Per aggiungere nuovi componenti:
1. Creare un nuovo modulo in `src/delibere_comunali/web/components/`
2. Implementare funzioni che accettano oggetti standardizzati come parametri
3. Importare e utilizzare il componente in `dashboard.py`

Per aggiungere nuove funzionalità di visualizzazione:
1. Estendere i modelli `ParsedDocument` o `AdministrativeEvent` se necessario
2. Aggiornare le funzioni di conversione nel modulo `data_loader.py`
3. Creare il componente UI appropriato

## Dipendenze Richieste

Le seguenti librerie sono richieste per la visualizzazione del Knowledge Graph:
- `networkx` (già incluso in requirements.txt)
- `pyvis` (già incluso in requirements.txt)
- `matplotlib` (già incluso in requirements.txt)