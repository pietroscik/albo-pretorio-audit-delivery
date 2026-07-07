# Diagrammi dell'Architettura del Sistema

## Diagramma Mermaid: Flusso Completo del Sistema con Moduli Avanzati

```mermaid
graph TB
    subgraph "Ingresso Dati"
        A1[Fonte Web Albo Pretorio] 
        A2[File PDF Locali]
        A3[Dataset Storici]
    end
    
    subgraph "Scraping e Parsing"
        B1[new_albo_scraper.py]
        B2[analyze_albo.py]
        B3[enhanced_extractor.py]
        B4[analyzer.py]
    end
    
    subgraph "Machine Learning"
        C1[randomForest.py]
        C2[train_model.py]
        C3[enhance_ml_model.py]
        C4[model_diagnostics.py]
    end
    
    subgraph "Moduli Avanzati Integrati"
        D1[Risk Assessment<br/>risk_calculator.py]
        D2[Analisi Attuariale<br/>provisioning.py]
        D3[KPI Manageriali<br/>kpi_calculator.py]
        D4[Controllo Anomalie<br/>audit_engine.py]
    end
    
    subgraph "Elaborazione e Post-elaborazione"
        E1[post_process_classification.py]
        E2[resolve_ambiguities.py]
        E3[enhance_metadata.py]
        E4[enhance_doc_type.py]
    end
    
    subgraph "Interfaccia Utente"
        F1[app_control_room.py]
        F2[Streamlit UI]
        F3[RAG Chat Interface]
    end
    
    subgraph "Output e Reporting"
        G1[risk_assessment.csv]
        G2[provisioning_attuariale.xlsx]
        G3[kpi_dashboard.xlsx]
        G4[allegati_parsed.csv]
        G5[atti_audited.csv]
    end
    
    subgraph "Feedback Loop"
        H1[feedback_operatore.csv]
        H2[apply_feedback_corrections.py]
        H3[Ground Truth Update]
    end

    A1 --> B1
    A2 --> B2
    A3 --> C2
    
    B1 --> B2
    B2 --> B3
    B3 --> B4
    
    B4 --> C1
    B4 --> C2
    C2 --> C3
    C3 --> C4
    
    B4 --> E1
    E1 --> E2
    E2 --> E3
    E3 --> E4
    
    E4 --> D1
    E4 --> D2
    E4 --> D3
    E4 --> D4
    
    D1 --> G1
    D2 --> G2
    D3 --> G3
    E4 --> G4
    D4 --> G5
    
    G4 --> F1
    G5 --> F1
    F1 --> F2
    F2 --> F3
    
    F2 --> H1
    H1 --> H2
    H2 --> C2
    H2 --> E1
    
    style A1 fill:#e1f5fe
    style G1 fill:#f3e5f5
    style G2 fill:#f3e5f5
    style G3 fill:#f3e5f5
    style D1 fill:#fff3e0
    style D2 fill:#fff3e0
    style D3 fill:#fff3e0
    style D4 fill:#fff3e0
```

## Dendrogramma Concettuale: Gerarchia dei Moduli del Sistema

Il seguente diagramma rappresenta la struttura gerarchica dei moduli del sistema, mostrando come i diversi componenti sono organizzati in una struttura ad albero gerarchico:

```
Sistema di Audit dell'Albo Pretorio
├── Core System
│   ├── Parsing Layer
│   │   ├── Basic Parser
│   │   ├── Enhanced Extractor
│   │   └── Analyzer
│   ├── ML Engine
│   │   ├── RandomForest Classifier
│   │   ├── Model Trainer
│   │   ├── Model Enhancer
│   │   └── Model Diagnostics
│   └── Data Processor
│       ├── Post-processor
│       ├── Ambiguity Resolver
│       ├── Metadata Enhancer
│       └── Doc Type Enhancer
├── Advanced Modules
│   ├── Risk Assessment
│   │   ├── Risk Calculator
│   │   └── Risk Scoring
│   ├── Actuarial Analysis
│   │   ├── Provisioning Calculator
│   │   └── Survival Analysis
│   ├── Management KPIs
│   │   ├── Efficiency Metrics
│   │   ├── Effectiveness Metrics
│   │   ├── Economy Metrics
│   │   └── Transparency Metrics
│   └── Audit Engine
│       ├── Anomaly Detection
│       └── Compliance Checking
├── User Interface
│   ├── Streamlit Control Room
│   ├── RAG Interface
│   └── Visualization Tools
├── Data Flow
│   ├── Input Sources
│   ├── Processing Pipeline
│   ├── Output Generation
│   └── Feedback Loop
└── Quality Assurance
    ├── Validation Tools
    ├── Statistics Analysis
    └── Continuous Improvement
```

## Descrizione dei Livelli

### 1. Core System
Livello fondamentale del sistema che gestisce l'estrazione e l'elaborazione iniziale dei dati.

### 2. Advanced Modules
Moduli specializzati che implementano competenze professionali avanzate:
- **Risk Assessment**: Valutazione del rischio basata su importo, urgenza, ricorrenza fornitori
- **Analisi Attuariale**: Calcoli attuariari per la stima degli impegni finanziari
- **Management KPIs**: Indicatori di governance ed efficienza amministrativa

### 3. User Interface
Interfaccia utente che consente l'interazione con il sistema e la supervisione umana.

### 4. Data Flow
Gestione del flusso dei dati attraverso il sistema, inclusi i feedback loop.

### 5. Quality Assurance
Componenti per garantire la qualità e l'affidabilità del sistema.

## Interazioni tra Moduli

I moduli comunicano attraverso:
- File CSV intermedi
- Comandi CLI standardizzati
- Feedback loop per l'apprendimento continuo
- API interne per l'integrazione

Questa architettura modulare permette l'espansione e la manutenzione del sistema mantenendo la scalabilità e la qualità.