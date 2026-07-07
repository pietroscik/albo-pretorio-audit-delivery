# Funzionalità degli Script e Moduli del Sistema

## Panoramica

Il sistema è organizzato in moduli funzionali specializzati, ciascuno con uno scopo specifico nell'ecosistema di audit dell'albo pretorio. Ogni modulo contribuisce alla visione complessiva di un sistema intelligente e discrezionale per il monitoraggio delle pubbliche amministrazioni.

## Moduli Principali

### 1. Parsing e Estrazione Dati
- **`new_albo_scraper.py`**: Scarica documenti PDF dall'albo pretorio
- **`analyze_albo.py`**: Estrae testo, metadati e informazioni strutturate dai PDF
- **`enhanced_extractor.py`**: Estrazione avanzata con supporto OCR e LLM

### 2. Classificazione e Machine Learning
- **`train_model.py`**: Addestra modelli ML per la classificazione documentale
- **`randomForest.py`**: Implementazione di classificatori Random Forest
- **`enhance_ml_model.py`**: Ottimizzazione dei modelli ML esistenti
- **`post_process_classification.py`**: Post-elaborazione dei risultati di classificazione

### 3. Audit e Controllo Umano
- **`app_control_room.py`**: Interfaccia Streamlit per l'audit HITL (Human-in-the-Loop)
- **`audit_engine.py`**: Motore automatico di rilevamento anomalie
- **`apply_feedback_corrections.py`**: Applica correzioni dai feedback umani
- **`resolve_ambiguities.py`**: Risoluzione automatica delle ambiguità

### 4. Analisi Avanzate
- **`risk_calculator.py`**: Valutazione del rischio per ogni atto amministrativo
- **`provisioning.py`**: Analisi attuariale degli impegni di spesa
- **`kpi_calculator.py`**: Calcolo di indicatori di governance e controllo di gestione

### 5. Elaborazione e Validazione
- **`enhance_metadata.py`**: Miglioramento dei metadati estratti
- **`enhance_doc_type.py`**: Classificazione avanzata per tipo di documento
- **`validate_output.py`**: Validazione della qualità dei risultati
- **`analyze_classification_stats.py`**: Statistiche dettagliate sui risultati di classificazione

### 6. Grafico della Conoscenza
- **`build_knowledge_graph.py`**: Costruzione del grafo delle relazioni
- **`visualizza_grafo.py`**: Visualizzazione interattiva del knowledge graph
- **`analyze_topology.py`**: Analisi topologica delle concentrazioni

## Funzionalità Avanzate

### Discrezionalità dei Dati
Il sistema implementa meccanismi per bilanciare trasparenza e protezione delle informazioni:

1. **Masking Automatico**: Nasconde informazioni personali identificabili
2. **Aggregazione**: Mostra dati aggregati anziché individuali quando possibile
3. **Controllo Granulare**: Permette di selezionare quali informazioni esporre

### Integrazione di Competenze Specialistiche
- **Risk Management**: Valutazione del rischio basata su importo, urgenza, ricorrenza fornitori
- **Analisi Attuariale**: Calcolo di provisioning, analisi di sopravvivenza, proiezioni finanziarie
- **Controllo di Gestione**: KPI di efficienza, efficacia, economicità e trasparenza

### Feedback Continuo
- **Ciclo di Feedback**: I risultati umani vengono reinseriti nel sistema per migliorare l'accuratezza
- **Apprendimento Attivo**: Selezione delle istanze più informative per la revisione umana
- **Adattamento Contestuale**: Il sistema si adatta alle specificità locali grazie ai feedback

## Interfaccia Utente

### Control Room (Streamlit)
- **Dashboard Completo**: Vista d'insieme delle metriche e risultati
- **Audit Interattivo**: Interfaccia per la revisione manuale dei documenti
- **Esplorazione RAG**: Chatbot basato su Retrieval-Augmented Generation
- **Visualizzazione Grafi**: Esplorazione interattiva del knowledge graph

## Comandi CLI

Il sistema offre un'interfaccia a linea di comando unificata tramite `run.py`:

- `scrape`: Scarica documenti
- `analyze`: Analizza documenti scaricati
- `train`: Addestra modelli ML
- `pipeline`: Esegue l'intera pipeline
- `control-room`: Avvia l'interfaccia Streamlit
- `risk-assessment`: Esegue valutazione del rischio
- `actuarial-analysis`: Esegue analisi attuariale
- `management-kpi`: Genera indicatori di governance
- `apply-corrections`: Applica correzioni dai feedback

## Sicurezza e Conformità

- **Verifica Firme Digitali**: Supporto per convalida di firme PAdES/CAdES
- **Accessibilità PDF**: Controllo conformità agli standard di accessibilità
- **Tracciamento Provenienza**: Ogni dato mantiene traccia della sua origine
- **Gestione Privacy**: Implementa principi di privacy by design

## Estensibilità

Il sistema è progettato per essere facilmente estendibile:
- **Architettura Modulare**: Nuove funzionalità possono essere aggiunte senza modificare il core
- **Plugin System**: Supporto per moduli esterni e integrazioni
- **API Standard**: Interfacce ben definite per l'integrazione con sistemi esterni