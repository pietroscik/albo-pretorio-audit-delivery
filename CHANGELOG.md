# Changelog

Tutte le modifiche importanti al progetto "Albo Pretorio Audit Delivery" saranno documentate in questo file.

Il formato è basato su [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
e il progetto aderisce al [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Sistema di gestione della configurazione enterprise
- Orchestrator avanzato per coordinamento moduli
- Coordinatore dati centralizzato
- Sistema di workflow enterprise configurabili
- Nuovi comandi CLI: `config-mgmt`, `enterprise`, `data-coord`, `orchestrate`

### Changed
- Migliorata l'architettura di coordinamento tra moduli
- Ottimizzata la gestione dei parametri di sistema
- Estesa la documentazione tecnica e normativa

## [1.1.0] - 2026-07-13

### Added
- Implementazione completa del sistema enterprise
- Integrazione con pipeline esistente mantenendo retro-compatibilità
- Validazione e test automatizzati del sistema enterprise
- Documentazione completa e aggiornata
- Sistema di coordinamento avanzato tra moduli
- Supporto per workflow configurabili

### Changed
- Esteso il sistema di coordinamento tra i moduli con supporto per workflow enterprise
- Migliorata comunicazione tra i moduli con standardizzazione dei dati condivisi
- Aggiunti nuovi parametri CLI per controllare i workflow enterprise
- Aggiornata documentazione per utilizzo avanzato

## [1.0.0] - 2026-07-12

### Added
- Sistema base per l'analisi degli albi pretori
- Moduli di scraping, parsing, classificazione
- Sistema di risk assessment
- Knowledge graph builder
- Sistema RAG (Retrieval Augmented Generation)
- Dashboard di controllo

### Changed
- Implementazione della pipeline completa di analisi
- Integrazione tra tutti i moduli principali
- Sistema di reporting completo