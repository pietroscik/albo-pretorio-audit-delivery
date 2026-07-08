# Mappa di Input/Output del Sistema di Audit dell'Albo Pretorio

## Panoramica

Documento che mappa tutti i flussi di input/output del sistema, inclusi i nuovi flussi introdotti dal modulo di coordinamento centrale.

## Input Principali

### Fonti Esterne
- **Web Albo Pretorio**: URL pubbliche degli albi pretori comunali
- **File PDF Locali**: Documenti scaricati precedentemente
- **Dataset Storici**: Dati di training e validazione precedenti
- **Chiavi API**: Google API Key per LLM

### Parametri di Configurazione
- **ENTE**: Nome dell'ente comunale da analizzare
- **Opzioni Pipeline**: --skip-scrape, --use-llm, --force, --strict-validation
- **Parametri ML**: Opzioni per l'addestramento e la predizione

## Output Principali

### File Strutturati
- **atti_parsed.csv**: Dati estratti dagli atti
- **documenti_features.csv**: Features per ML
- **documenti_corpus.jsonl**: Corpus per RAG
- **procedures.json**: Struttura del digital twin
- **anomalies.json**: Anomalie rilevate

### Report Specializzati
- **risk_assessment.csv**: Risultati della valutazione del rischio
- **kpi_dashboard.xlsx**: KPI manageriali
- **provisioning_attuariale.xlsx**: Analisi attuariale
- **atti_audited.csv**: Risultati dell'audit
- **albo_analisi.xlsx**: Report principale

### Output del Coordinamento
- **coordinated_analysis_results.json**: Risultati coordinati tra tutti i moduli
- **risk_assessment_coordinated.csv**: Versione coordinata del risk assessment
- **kpi_manageriali_coordinated.csv**: Versione coordinata dei KPI

## Flusso degli Input/Output

```mermaid
graph TD
    subgraph "INPUT ESTERNI"
        A1[Web Albo Pretorio]
        A2[PDF Locali]
        A3[Dataset Storici]
        A4[Chiavi API]
    end

    subgraph "MODULI CORE"
        B1[Scraper]
        B2[Parsing]
        B3[ML Models]
    end

    subgraph "MODULI AVANZATI"
        C1[Risk Assessment]
        C2[KPI Manageriali]
        C3[Analisi Attuariale]
        C4[Audit Engine]
    end

    subgraph "COORDINAMENTO CENTRALE"
        D1[CentralOrchestrator]
        D2[DataCoordinator]
    end

    subgraph "OUTPUT SPECIALIZZATI"
        E1[Risk Report]
        E2[KPI Report]
        E3[Actuarial Report]
        E4[Audit Report]
    end

    subgraph "OUTPUT COORDINATI"
        F1[Coordinated Results JSON]
        F2[Coordinated Reports]
    end

    subgraph "OUTPUT FINALI"
        G1[Excel Principale]
        G2[CSV Strutturati]
        G3[File RAG]
    end

    A1 --> B1
    A2 --> B2
    A3 --> B3
    A4 --> B3

    B1 --> B2
    B2 --> B3
    B3 --> C1
    B3 --> C2
    B3 --> C3
    B3 --> C4

    B2 --> D1
    C1 --> D1
    C2 --> D1
    C3 --> D1
    C4 --> D1

    D1 --> D2
    D2 --> C1
    D2 --> C2
    D2 --> C3
    D2 --> C4

    C1 --> E1
    C2 --> E2
    C3 --> E3
    C4 --> E4

    D1 --> F1
    D1 --> F2

    E1 --> G2
    E2 --> G1
    E3 --> G2
    E4 --> G2
    F1 --> G2
    F2 --> G1

    style D1 fill:#ffdd00
    style D2 fill:#ffdd00
    style F1 fill:#ffeeaa
    style F2 fill:#ffeeaa
```

## Schema dei Dati Condivisi

### Struttura dati coordinati
```
coordinated_analysis_results.json:
{
  "timestamp": "ISO datetime",
  "risk_results": {
    "risk_by_document": [...],
    "summary_statistics": {...}
  },
  "kpi_results": {
    "efficienza": {...},
    "efficacia": {...},
    "economicita": {...},
    "trasparenza": {...}
  },
  "ml_results": {...},
  "audit_results": {...}
}
```

## Consumatori dei Dati

### Moduli Interni
- **Control Room**: Utilizza tutti i report per la dashboard
- **RAG System**: Usa i dati coordinati per migliorare le risposte
- **ML Models**: Riceve feedback dai risultati coordinati

### Utenti Finali
- **Operatori Umani**: Utilizzano i report per la validazione
- **Analisti**: Studiano i risultati coordinati per insight
- **Autorità di Controllo**: Ricevono report integrati

## Frequenza di Aggiornamento

- **Input**: Giornaliero per scraping, mensile per dataset storici
- **Output Intermedi**: Ogni esecuzione della pipeline
- **Output Coordinati**: Ogni esecuzione dell'orchestrator
- **Report Finali**: Alla conclusione della pipeline completa