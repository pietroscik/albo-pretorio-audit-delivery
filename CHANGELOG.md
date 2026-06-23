# Changelog

Tutte le modifiche rilevanti a **Albo Pretorio Audit Delivery** saranno documentate in questo file.

Il formato è basato su [Keep a Changelog](https://keepachangelog.com/it-IT/1.0.0/).

---

## [1.2.0] - 2026-06-16

### ✨ Nuove Funzionalità

#### Core Analysis Module (`analyze_albo.py`)
- **50+ regex patterns** per il rilevamento di competenze del personale, basati su analisi di 394 documenti reali da 7 librerie utente.
- **6 regex patterns** per il rilevamento di atti finanziari e contabili
- Funzione `is_accounting_relevant()` per identificare documenti contabili
- Funzione `is_personnel_competence_relevant()` per identificare documenti su competenze del personale
- Funzione `extract_personnel_competences()` per estrarre competenze strutturate
- Funzione `extract_decree_references()` per estrarre riferimenti a decreti sindacali
- Funzione `extract_full_metadata()` per estrazione completa dei metadati
- Funzione `process_directory_to_csv()` per processamento batch di directory
- Dataclass `PersonnelCompetence` e `DocumentMetadata`

#### RAG Chat Module (`src/web/rag_chat.py`)
- Supporto per filtri `only_personnel_competence` e parametro `k` in `esegui_query_rag_core()`.
- Integrazione ottimizzata con modelli Sentence Transformers.

#### Test Suite (`test_modifiche.py`)
- Implementazione test unitari per garantire la copertura dei pattern del personale e RAG filtrato.

## [1.1.0] - 2026-06-15

### ✨ Aggiunte (Features)
- **Domain Filtering**: Introdotto un filtro globale nella Control Room e nel motore RAG per isolare gli atti con rilevanza contabile (`accounting_relevant`). Questo migliora drasticamente la precisione delle analisi finanziarie e delle risposte dell'IA.
- **Assistente RAG Integrato**: L'assistente RAG è stato reintegrato come modulo all'interno della Control Room principale, consentendo un'interazione contestuale con i dati dell'ente selezionato.
- **Visualizzatore PDF in Audit HITL**: Aggiunto un visualizzatore PDF a due colonne nella sezione di validazione umana, per permettere un riscontro visivo immediato del documento durante la correzione dei dati.
- **Nuove Categorie Documentali**: Aggiunte le categorie "Delibera di Giunta" e "Delibera di Consiglio" nel motore di classificazione per una distinzione più accurata degli atti.

### 🐛 Correzioni (Bug Fixes)
- **Errore di Indentazione**: Risolti i `IndentationError` ricorrenti nei moduli RAG (`rag_app.py`, `src/web/rag_chat.py`) che impedivano l'avvio dell'applicazione.
- **Errore di Importazione**: Corretto l'`ImportError` in `app_control_room.py` facendo puntare l'importazione della funzione `esegui_query_rag_core` al modulo corretto.

### ⚙️ Miglioramenti (Improvements)
- **Normalizzazione Dati**: Migliorata la logica di normalizzazione per RUP e Beneficiari per accorpare nomi simili e scartare "rumore" burocratico.
- **Addestramento ML**: Il training del modello di classificazione ora utilizza una suddivisione stratificata (`stratify=y`) per gestire meglio le categorie con pochi esempi.

## [1.0.0] - 2026-05-01

### 🎉 Rilascio Iniziale
- Creazione della pipeline di estrazione dati da Albo Pretorio.
- Implementazione della Control Room con dashboard direzionale, esploratore atti e motore antifrode.
- Sviluppo dell'applicazione RAG standalone per la ricerca conversazionale.