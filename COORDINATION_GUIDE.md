# Guida alla Coordinazione

## Introduzione

Questa guida descrive come coordinare i diversi moduli del sistema "Albo Pretorio Audit Delivery" per ottenere risultati ottimali attraverso un'analisi integrata.

## Architettura del Sistema di Coordinazione

### Componenti Principali

#### CentralOrchestrator
Il [CentralOrchestrator](src/delibere_comunali/core/orchestrator.py#L151-L158) è il coordinatore centrale che gestisce l'interazione tra i diversi moduli avanzati:

- **Risk Assessment**: Analisi del rischio associato ai documenti
- **Management KPI**: Calcolo dei KPI di gestione
- **ML Diagnostics**: Diagnostica dei modelli ML
- **Audit Engine**: Motore di audit

#### DataCoordinator
Il [DataCoordinator](src/delibere_comunali/core/data_coordinator.py#L72-L82) gestisce i dati condivisi tra i moduli, permettendo una comunicazione strutturata:

- Memorizzazione centralizzata dei dati
- Registro delle dipendenze tra moduli
- Log delle modifiche ai dati
- Serializzazione sicura

#### ConfigManager
Il [ConfigManager](src/delibere_comunali/core/config_manager.py#L58-L279) gestisce tutti i parametri del sistema enterprise:

- Unificazione dei sistemi di configurazione
- Validazione della configurazione
- Raccomandazioni automatiche
- Caricamento/salvataggio da file

#### EnterpriseOrchestrator
L'[EnterpriseOrchestrator](src/delibere_comunali/core/enterprise_orchestration.py#L26-L192) esegue workflow enterprise con parametri configurabili:

- Supporto per diversi tipi di workflow
- Integrazione con il sistema di coordinamento esistente
- Modalità dry-run per test sicuri

## Modalità di Coordinazione

### 1. Coordinamento Completo (`orchestrate`)

Esegue tutti i moduli con coordinamento avanzato:

```bash
python run.py orchestrate --ente=comune_di_esempio
```

Opzioni:
- `--load-data`: Percorso specifico per i dati parsati
- `--skip-risk`: Salta l'esecuzione del risk assessment
- `--skip-kpi`: Salta l'esecuzione del calcolo KPI
- `--skip-ml`: Salta l'esecuzione dell'analisi ML
- `--skip-audit`: Salta l'esecuzione dell'audit
- `--sequential`: Forza esecuzione sequenziale (disabilita parallelizzazione)
- `--no-cache`: Disabilita il caching
- `--workers`: Numero massimo di thread worker per parallelizzazione
- `--clear-cache`: Svuota la cache prima di eseguire

### 2. Coordinamento Dati (`data-coord`)

Interfaccia per il coordinatore dati centralizzato:

```bash
python run.py data-coord --ente=comune_di_esempio --action=summary
```

Azioni disponibili:
- `list`: Lista tutte le chiavi disponibili
- `get`: Ottiene un dato specifico
- `save`: Salva un dato specifico
- `load`: Carica dati da persistenza
- `clear`: Cancella tutti i dati
- `summary`: Mostra sommario dei dati

### 3. Workflow Enterprise (`enterprise`)

Esegue workflow enterprise con parametri configurabili:

```bash
python run.py enterprise --ente=comune_di_esempio --workflow=full
```

Tipi di workflow:
- `full`: Esegue tutti i moduli
- `risk_only`: Esegue solo il risk assessment
- `kpi_only`: Esegue solo il calcolo KPI
- `ml_only`: Esegue solo l'analisi ML
- `audit_only`: Esegue solo l'audit
- `minimal`: Esegue un'analisi minimale per test rapidi

Opzioni:
- `--base-path`: Percorso base per i dati
- `--load-data`: Percorso specifico per i dati parsati
- `--skip-risk`: Salta l'esecuzione del risk assessment
- `--skip-kpi`: Salta l'esecuzione del calcolo KPI
- `--skip-ml`: Salta l'esecuzione dell'analisi ML
- `--skip-audit`: Salta l'esecuzione dell'audit
- `--config-file`: File di configurazione da caricare
- `--dry-run`: Esegue una simulazione senza salvare risultati
- `--save-results`: Salva i risultati in formato strutturato
- `--verbose`: Modalità verbosa

### 4. Gestione Configurazione (`config-mgmt`)

Gestisce la configurazione enterprise:

```bash
python run.py config-mgmt --ente=comune_di_esempio --action=show
```

Azioni disponibili:
- `show`: Visualizza la configurazione attiva
- `save`: Salva la configurazione in un file
- `load`: Carica la configurazione da un file
- `validate`: Validazione della configurazione
- `recommend`: Ottiene raccomandazioni sui parametri

Opzioni:
- `--config-path`: Percorso specifico per il file di configurazione
- `--update-param`: Aggiorna un parametro specifico (usa ripetutamente)

## Feedback Loops

Il sistema implementa diversi feedback loops per migliorare continuamente i risultati:

### 1. Risk-KPI Feedback Loop
I risultati del risk assessment influenzano i parametri dei KPI e viceversa:
- Se il rischio medio è alto, alcuni KPI vengono adattati per riflettere questa condizione
- Se i KPI indicano bassa efficienza, vengono aumentate le attenzioni verso certi tipi di rischi

### 2. ML-Model Adaptation
I risultati dell'analisi ML influenzano l'adattamento dei modelli:
- Se vengono trovate forti correlazioni tra risk scores e altre metriche, i pesi nei moduli vengono aggiustati
- I modelli vengono aggiornati dinamicamente in base ai risultati delle analisi

### 3. Dynamic Thresholds
Le soglie di valutazione sono aggiornate dinamicamente:
- Le soglie del risk assessment sono adattate in base ai risultati KPI
- I parametri di classificazione sono aggiustati in base ai risultati ML

## Parallelizzazione e Performance

### Esecuzione Parallela
- I moduli indipendenti possono essere eseguiti in parallelo
- Il numero di worker è configurabile (default: 4)
- La parallelizzazione può essere disabilitata con `--sequential`

### Caching
- I risultati dei moduli sono memorizzati in cache per evitare calcoli ridondanti
- La cache può essere disabilitata con `--no-cache`
- La cache può essere svuotata con `--clear-cache`

## Sicurezza e Governance

Tutte le operazioni di coordinamento rispettano i principi di governance pubblica:
- Solo documenti ufficiali pubblici vengono analizzati
- Nessun trattamento di dati sensibili
- Tutte le operazioni sono tracciate e verificabili
- I risultati sono conservati in modo sicuro e conforme