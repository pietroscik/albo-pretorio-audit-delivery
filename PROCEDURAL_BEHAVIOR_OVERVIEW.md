# Panoramica del Comportamento Procedurale

## Introduzione

Questo documento descrive il comportamento procedurale del sistema "Albo Pretorio Audit Delivery", inclusi i flussi di lavoro, le interazioni tra componenti e i processi decisionali implementati.

## Flussi di Lavoro Principali

### 1. Flusso Standard (Legacy)
```
Scraping → Parsing → ML Training → Knowledge Graph → Risk Assessment → Output
```

### 2. Flusso Enterprise (Nuovo)
```
Configurazione Enterprise → Scraping (opzionale) → Parsing → Coordinamento Moduli → Enterprise Workflow → Output Enterprise
```

## Componenti Procedurali

### Core Components
- **ConfigManager**: Gestisce la configurazione centralizzata del sistema enterprise
- **EnterpriseOrchestrator**: Coordinatore avanzato per l'esecuzione di workflow complessi
- **DataCoordinator**: Gestisce i dati condivisi tra i diversi moduli
- **CentralOrchestrator**: Coordinatore centrale per il sistema di analisi avanzata

### Processi Decisionali

#### Selezione del Workflow
Il sistema seleziona il workflow appropriato basandosi sui seguenti criteri:
- Se vengono forniti parametri enterprise (`--enterprise-workflow`), viene attivato il flusso enterprise
- Altrimenti, viene utilizzato il flusso standard
- La configurazione viene validata prima dell'esecuzione

#### Gestione degli Errori
- Ogni componente implementa meccanismi di logging dettagliato
- I dati problematici vengono isolati e segnalati
- I processi continuano anche in presenza di errori parziali
- I risultati intermedi vengono salvati per analisi successive

#### Coordinamento tra Moduli
Come specificato nel "[模块协同与Pipeline协调规范](file:///c:/Users\39329\albo-pretorio-audit-delivery/ENTERPRISE_PARAMETERIZATION_GUIDE.md#L4-L12)", il coordinamento segue questi principi:
1. I moduli comunicano attraverso rappresentazioni standardizzate (es. quality_metrics.json)
2. Il coordinatore centrale gestisce l'ordine di esecuzione e i flussi di dati
3. I feedback loops permettono aggiornamenti dinamici (es. ground truth aggiorna risk_assessment)
4. I risultati sono salvati in formato JSON standardizzato

## Nuovi Workflow Enterprise

### 1. Workflow Completo (`full`)
Esegue tutti i componenti disponibili:
- Risk Assessment
- Management KPI
- ML Analysis
- Audit

### 2. Workflow Specializzato (`risk_only`, `kpi_only`, `ml_only`, `audit_only`)
Esegue solo il componente specificato per analisi mirate.

### 3. Workflow Minimale (`minimal`)
Esegue una verifica rapida per test e validazione.

## Interazioni tra Componenti

### Sequenza di Esecuzione
1. **Inizializzazione**: [ConfigManager](file:///c:/Users\39329\albo-pretorio-audit-delivery/src/delibere_comunali/core/config_manager.py) carica la configurazione
2. **Preparazione**: [DataCoordinator](file:///c:/Users\39329\albo-pretorio-audit-delivery/src/delibere_comunali/core/data_coordinator.py) prepara i dati condivisi
3. **Coordinamento**: [CentralOrchestrator](file:///c:/Users\39329\albo-pretorio-audit-delivery/src/delibere_comunali/core/orchestrator.py) orchestra i moduli
4. **Esecuzione**: [EnterpriseOrchestrator](file:///c:/Users\39329\albo-pretorio-audit-delivery/src/delibere_comunali/core/enterprise_orchestration.py) esegue il workflow specificato
5. **Output**: Risultati salvati in formato strutturato

### Feedback Loops
- I risultati del Risk Assessment influenzano i parametri dei KPI
- I risultati dei KPI influenzano le soglie del Risk Assessment
- I risultati ML influenzano l'adattamento dei modelli
- I risultati dell'Audit influenzano tutti gli altri componenti

## Sicurezza e Governance

Tutti i processi rispettano i principi di governance pubblica:
- Solo documenti ufficiali pubblici vengono analizzati
- Nessun trattamento di dati sensibili
- Tutte le decisioni sono tracciabili
- I risultati sono verificabili e riproducibili

## Performance e Ottimizzazione

### Elaborazione Parallela
- I moduli indipendenti possono essere eseguiti in parallelo
- Il numero di worker è configurabile tramite parametri enterprise
- La cache è utilizzata per evitare calcoli ridondanti

### Gestione delle Risorse
- I parametri sono ottimizzati automaticamente in base alle risorse disponibili
- I processi lunghi mostrano progressi intermedi
- I dati temporanei sono gestiti efficientemente

## Monitoraggio e Logging

Ogni componente del sistema:
- Registra dettagliatamente le proprie operazioni
- Misura le performance e i tempi di esecuzione
- Segnala eventuali anomalie o errori
- Produce metriche di qualità e accuratezza