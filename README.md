# Albo Pretorio Audit Delivery

## Panoramica

Questo progetto contiene un sistema avanzato di audit e analisi del comportamento procedurale del Comune di Avella, basato sull'analisi automatica degli atti pubblici presenti nell'albo pretorio. Il sistema include un modulo centrale di coordinamento (CentralOrchestrator) che coordina tutti i moduli avanzati per garantire un'analisi integrata e coerente.

## Obiettivo

Il sistema è progettato per:
- Analizzare automaticamente i documenti dell'albo pretorio
- Classificare i documenti in diverse categorie (Determinazioni, Delibere, Visti Contabili, ecc.)
- Rilevare anomalie e potenziali frodi amministrative
- Fornire una visione olistica del comportamento procedurale
- Monitorare la qualità e la trasparenza della gestione pubblica
- Coordinare in modo integrato i diversi moduli di analisi (Risk Assessment, KPI, ML, Audit)

## Risultati Principali

### Miglioramenti del Sistema
- **Classificazioni ambigue**: Ridotte da 1,486 a 141 documenti (-90.5%)
- **Categoria "Affari Generali"**: Ridotta dal 86.2% al 12.1% dei documenti
- **Documenti senza categoria**: Solo 50 su 1,724 (2.89%)
- **Tipo documento sconosciuto**: Solo 39 documenti (2.25%)

### Scoperte Importanti
- **Spesa totale analizzata**: 1.273.630.779,03 €
- **Indice concentrazione HHI**: 6835.71 (molto elevato)
- **Top fornitore**: "NON IDENTIFICATO" (oltre 1 miliardo €)
- **CIG Fantasma**: 290 atti contabili senza CIG tracciabile
- **Beneficiari Assenti**: Oltre 1 miliardo € attribuito a "NON IDENTIFICATO"
- **Sindrome della Soglia (Smurfing)**: 4 casi identificati

### Pattern di Comportamento
- **VINCENZO BIANCARDI**: 100 atti gestiti (possibile concentrazione di potere)
- **ELISABETTA NISI**: Coinvolta in molte anomalie di smurfing
- **Top beneficiari**: "DIVERSI/NON APPLICABILE" con 100 atti

## File Principali Generati

- `CRTICALITY_TIMELINE.md`: Cronologia delle criticità e miglioramenti
- `PROCEDURAL_BEHAVIOR_OVERVIEW.md`: Visione olistica del comportamento procedurale
- `CORE_INTEGRATION.md`: Documentazione del sistema di coordinamento centrale
- `data/avella/albo_download/report/`: Cartella contenente tutti i report dettagliati
- `data/avella/albo_download/atti_parsed.csv`: Dati estratti dagli atti
- `data/avella/albo_download/documenti_corpus.jsonl`: Corpus di documenti per RAG
- `data/avella/albo_download/report/coordinated_analysis_results.json`: Risultati coordinati tra tutti i moduli

## Comandi Principali

- `python run.py pipeline --ente avella --skip-scrape`: Esegue l'intero pipeline di analisi
- `python run.py analyze --ente avella`: Esegue solo l'analisi dei documenti
- `python run.py audit --ente avella`: Esegue solo il controllo di audit
- `python run.py build-kg --ente avella`: Costruisce il grafo della conoscenza
- `python run.py orchestrate --ente avella`: Esegue la coordinazione tra tutti i moduli avanzati (Risk Assessment, KPI, ML, Audit)

## Nuovi Comandi di Coordinamento

- `python run.py orchestrate --ente <nome>`: Esegue la pipeline completa di coordinamento tra tutti i moduli avanzati
- `python run.py data-coord --ente <nome>`: Interagisce con il coordinatore dati centrale

## Criticità Identificate

1. **Concentrazione di potere**: Uno solo RUP gestisce 100 atti
2. **Mancata tracciabilità**: Solo 39.1% di documenti con CIG
3. **Tempi procedurali lunghi**: 203 giorni medi per approvazione
4. **Mancata identificazione controparti**: Elevata percentuale di "NON IDENTIFICATO"
5. **Concentrazione economica eccessiva**: HHI di 6835.71

## Azioni Consigliate

1. **Implementare sistemi di controllo**: Blocco automatico per documenti senza CIG/CUP
2. **Ridurre concentrazione di potere**: Distribuire carichi di lavoro tra più RUP
3. **Migliorare identificazione controparti**: Processo di verifica obbligatoria
4. **Automatizzare controlli antifrode**: Sistemi di monitoraggio continuo
5. **Ottimizzare tempi procedurali**: Ridurre i 203 giorni medi di approvazione