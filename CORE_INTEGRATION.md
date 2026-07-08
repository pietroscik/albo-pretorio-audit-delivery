# Sistema di Coordinamento Centrale

## Introduzione

Il sistema di coordinamento centrale è stato introdotto per risolvere uno dei principali problemi architetturali del sistema: la mancanza di integrazione tra i diversi moduli avanzati (Risk Assessment, Management KPI, ML Models, Audit Engine).

Prima di questa implementazione, questi moduli operavano in modo completamente indipendente, senza scambiarsi informazioni né influenzarsi reciprocamente, limitando notevolmente l'efficacia complessiva del sistema.

## Componenti del Sistema di Coordinamento

### 1. CentralOrchestrator

Il modulo CentralOrchestrator si occupa di:

- Coordinare l'esecuzione dei diversi moduli avanzati
- Consentire lo scambio di informazioni tra i moduli
- Implementare meccanismi di feedback tra i risultati ottenuti
- Salvare i risultati coordinati in formato strutturato

#### Funzionalità principali:

- **Caricamento dati condivisi**: Carica i dati parsati da fonti comuni
- **Esecuzione coordinata**: Esegue i moduli in sequenza ma con feedback reciproco
- **Aggiornamento parametri**: Usa i risultati di un modulo per influenzare i parametri di un altro
- **Gestione output**: Salva i risultati in formato strutturato per l'utilizzo successivo

### 2. DataCoordinator

Il modulo DataCoordinator implementa:

- Un sistema centralizzato per la gestione dei dati condivisi tra i moduli
- Un meccanismo di registrazione delle dipendenze tra moduli
- Una persistenza dei dati su disco
- Uno storico delle modifiche ai dati

#### Funzionalità principali:

- **Memorizzazione dati**: Memorizza dati con chiavi specifiche e metadati
- **Recupero dati**: Recupera dati in base a chiave, tipo o modulo sorgente
- **Persistenza**: Salva e carica i dati su disco per la persistenza
- **Tracciamento**: Mantiene uno storico delle operazioni sui dati

## Flusso di Esecuzione Coordinata

Il nuovo sistema implementa il seguente flusso di esecuzione:

1. **Caricamento dati condivisi**: I dati vengono caricati da fonti comuni
2. **Esecuzione Risk Assessment**: Calcolo dei punteggi di rischio
3. **Aggiornamento KPI**: I risultati del risk assessment influenzano i parametri KPI
4. **Calcolo KPI**: Esecuzione del calcolo dei KPI manageriali
5. **Aggiornamento soglie**: I risultati KPI influenzano le soglie del risk assessment
6. **Analisi ML**: Esecuzione dell'analisi machine learning
7. **Adattamento modelli**: I risultati ML influenzano i modelli e i pesi
8. **Analisi di Audit**: Esecuzione dell'analisi di audit usando tutti i risultati precedenti
9. **Salvataggio coordinato**: I risultati vengono salvati in formato strutturato

## Comandi Disponibili

### Orchestrator

```bash
# Esegui l'orchestrator completo
python run.py orchestrate --ente <nome_ente>

# Esegui con opzioni specifiche
python run.py orchestrate --ente <nome_ente> --base-path <percorso_base> --skip-risk
```

### Data Coordinator

```bash
# Interagisci con il coordinatore dati
python run.py data-coord --ente <nome_ente>
```

### Pipeline Completa con Coordinamento

```bash
# Esegui la pipeline completa con coordinamento
python run.py pipeline --ente <nome_ente> --use-llm

# Esegui con coordinamento saltato
python run.py pipeline --ente <nome_ente> --skip-orchestration
```

## File di Output

Il sistema di coordinamento genera i seguenti file di output:

- `coordinated_analysis_results.json`: Risultati coordinati di tutti i moduli
- `risk_assessment_coordinated.csv`: Risultati del risk assessment
- `kpi_manageriali_coordinated.csv`: Risultati dei KPI manageriali
- File di log e storico delle operazioni

## Architettura del Sistema

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Raw Data      │───▶│  Parsed Data     │───▶│ Shared Data     │
│   Sources       │    │  (analyze_albo)  │    │  Coordinator    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
    ┌────────────────────────────────────────────────────┼─────────────────────────────────────────────────────┐
    ▼                                                    ▼                                                     ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Risk Assessor   │    │  KPI Calculator  │    │  ML Model Diagnostics   │    │ Audit Engine    │    │ Human Feedback  │
│                 │    │                  │    │                         │    │                 │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                              │                          │                      │
         └───────────────────────┼──────────────────────────────┼──────────────────────────┼──────────────────────┘
                                 ▼                              ▼                          ▼
                    ┌─────────────────────────┐    ┌─────────────────────────┐    ┌─────────────────────────┐
                    │  Central Orchestrator   │───▶│ Coordinated Analysis    │───▶│ Actionable Insights     │
                    │                         │    │  Results (JSON/CSV)     │    │  & Recommendations     │
                    └─────────────────────────┘    └─────────────────────────┘    └─────────────────────────┘
```

## Conformità alle Norme di Progetto

Questa implementazione soddisfa le seguenti norme di progetto:

- **跨模块协同架构规范 (Cross-module Coordination Architecture Specification)**: Implementa un coordinatore centrale come richiesto
- **项目输入输出映射规范 (Project I/O Mapping Specification)**: Documenta chiaramente input/output del sistema
- **指标消费端一致性与数据流完整性规范 (Indicator Consumer Consistency and Data Flow Integrity Specification)**: Garantisce la consistenza dei dati tra i moduli
- **Pipeline扩展与集成规范 (Pipeline Extension and Integration Specification)**: Estende la pipeline senza modificare i componenti esistenti
- **多租户路径解析与函数集中化规范 (Multi-tenant Path Resolution and Function Centralization Specification)**: Tutte le funzioni di gestione del percorso risiedono ora nel modulo centralizzato `delibere_comunali.utils.config`

## Note di Implementazione

Come richiesto dalla norma "多租户路径解析与函数集中化规范", la funzione `get_tenant_dir()` è stata centralizzata nel modulo `delibere_comunali.utils.config` e tutti i moduli che ne avevano bisogno (incluso il nuovo `orchestrator.py`) ora la importano da questa unica fonte autorevole.

## Benefici del Sistema di Coordinamento

1. **Migliore efficacia**: I moduli ora possono influenzarsi reciprocamente, migliorando l'accuratezza complessiva
2. **Feedback continuo**: I risultati di un modulo possono essere utilizzati per migliorare i successivi
3. **Consistenza dei dati**: Tutti i moduli accedono agli stessi dati attraverso il coordinatore
4. **Facilità di estensione**: Nuovi moduli possono essere facilmente integrati nel sistema
5. **Monitoraggio**: È possibile tracciare come i dati fluiscono tra i diversi moduli