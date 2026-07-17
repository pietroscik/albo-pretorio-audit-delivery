# Implementazione del Modulo RAG (Retrieval Augmented Generation)

## Panoramica

Il modulo RAG (Retrieval Augmented Generation) implementa un sistema avanzato di ricerca semantica e generazione contestuale per l'interazione con i documenti pubblici elaborati dal sistema di audit dell'albo pretorio.

## Architettura del Sistema

### Componenti Principali

1. **[semantic_rag_engine.py](file:///c:/Users\39329\albo-pretorio-audit-delivery/src/delibere_comunali/rag/semantic_rag_engine.py)**: Motore semantico principale
   - Sistema di ricerca basato su FAISS per ricerca veloce in spazio vettoriale
   - Modelli di embedding multilingua per rappresentazione semantica
   - Integrazione con il sistema di privacy per garantire GDPR compliance
   - Filtri per categoria di documento
   - Sistema di generazione risposte contestuali

2. **[rag_app.py](file:///c:/Users\39329\albo-pretorio-audit-delivery/src/delibere_comunali/rag/rag_app.py)**: Interfaccia utente Streamlit
   - Interfaccia interattiva per interrogazioni in linguaggio naturale
   - Visualizzazione risultati con punteggi di similarità
   - Esportazione risultati in formato CSV
   - Statistiche sull'indice e sui documenti disponibili

## Funzionalità Chiave

### Ricerca Semantica
- Ricerca basata su similarità semantica anziché corrispondenza esatta
- Supporto per query in linguaggio naturale
- Ordinamento dei risultati per rilevanza (punteggio di similarità)
- Filtri per categoria di documento (deliberazioni, determinazioni, bandi, ecc.)

### Privacy e Sicurezza
- Integrazione con il sistema di privacy per pseudonimizzazione automatica
- Protezione dei dati sensibili durante le query
- Conformità GDPR durante l'interazione semantica

### Generazione Contestuale
- Sistema di generazione risposte basato sul contenuto specifico dei documenti recuperati
- Supporto per domande complesse che richiedono contesto da più documenti
- Fallback sicuro quando la risposta non è disponibile nel contesto

## Flusso di Interazione

1. **Input Utente**: L'utente inserisce una domanda in linguaggio naturale
2. **Elaborazione Query**: La query viene convertita in embedding semantico
3. **Ricerca in Indice**: L'embedding viene confrontato con l'indice FAISS
4. **Recupero Documenti**: Recupero dei documenti più rilevanti
5. **Filtraggio**: Applicazione di eventuali filtri (categoria, ente, ecc.)
6. **Generazione Risposta**: Creazione della risposta basata sui documenti recuperati
7. **Visualizzazione**: Presentazione dei risultati all'utente

## Configurazione

### Requisiti
- Indice FAISS già costruito (nella cartella `data/{ente}/albo_download/faiss_index/`)
- Corpus documentale disponibile (in formato JSONL)
- Modelli di embedding multilingua installati

### Parametri
- `ente`: Nome dell'ente pubblico da interrogare
- `k_results`: Numero di risultati da restituire (default: 5)
- `category_filter`: Filtro opzionale per categoria di documento
- `model_type`: Tipo di modello da utilizzare ("local", "gemini", "ollama")

## Integrazione con il Sistema

### Dipendenze
- Sistema di parsing e classificazione documenti
- Sistema di privacy e GDPR compliance
- Sistema di indicizzazione FAISS
- Sistema di metriche e osservabilità

### Flusso di Lavoro
1. I documenti vengono processati dal modulo di parsing
2. Vengono creati embeddings e costruito l'indice FAISS
3. Il modulo RAG rende disponibile l'interazione semantica
4. Le query vengono elaborate e i risultati forniti all'utente
5. Le metriche vengono raccolte per monitoraggio e miglioramento

## Casistiche d'Uso

### Domande Tipiche
- "Quali sono le deliberazioni recenti sul bilancio?"
- "Chi è il responsabile del procedimento per le opere pubbliche?"
- "Quali bandi sono stati pubblicati negli ultimi 30 giorni?"
- "Quali sono i fornitori principali del comune?"

### Filtri Avanzati
- Ricerca per categoria (deliberazioni, determinazioni, bandi)
- Ricerca per data di pubblicazione
- Ricerca per ente specifico

## Sicurezza e Governance

### Misure di Sicurezza
- Pseudonimizzazione automatica dei dati sensibili nelle query
- Controllo degli accessi basato sull'ente selezionato
- Logging delle query per audit trail
- Conformità GDPR integrata

### Governance
- Tracciamento completo delle interazioni
- Report di conformità GDPR
- Politiche di retention automatiche
- Implementazione del diritto all'oblio

## Monitoraggio e Metriche

### Metriche Rilevanti
- Numero di query processate
- Tempo medio di risposta
- Tasso di successo delle ricerche
- Tipologia di query più frequenti
- Categoria di documenti più richieste

### Endpoint di Monitoraggio
- `/health`: Stato del servizio RAG
- `/stats`: Statistiche sull'indice e sui documenti
- `/metrics`: Metriche di utilizzo e performance

## Best Practice

### Ottimizzazione Prestazioni
- Aggiornamento regolare dell'indice FAISS
- Pulizia e ottimizzazione del corpus documentale
- Monitoraggio continuo delle performance
- Scaling automatico in base al carico

### Qualità dei Risultati
- Validazione continua della qualità delle risposte
- Feedback loop con utenti esperti
- Aggiornamento continuo dei modelli di embedding
- Controllo della copertura documentale