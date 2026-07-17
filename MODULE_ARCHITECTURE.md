# Architettura Modulare del Sistema di Audit per Albi Pretori

## Panoramica

Il sistema è stato trasformato da un singolo script monolitico in un'architettura modulare altamente scalabile e manutenibile, composta da 72 componenti interconnessi.

## Struttura del Sistema

### 1. Layer di Orchestratore
- `analyze_albo.py`: Punto di ingresso principale per l'analisi degli atti
- `orchestrator.py`: Gestisce il coordinamento tra i diversi moduli
- `event_factory.py`: Crea eventi per il Digital Twin amministrativo

### 2. Layer di Estrazione e Parsing
- `entity_extractor.py`: Estrazione avanzata di entità da documenti
- `extractor.py`: Funzionalità basilari di estrazione
- `enhanced_extractor.py`: Estrazione avanzata con capacità forensi
- `text_extractor.py`: Estrazione testo da diversi formati di documento
- `feature_extractor.py`: Calcolo di caratteristiche statistiche
- `document_classifier.py`: Classificazione automatica dei documenti
- `parsed_document.py`: Modello dati per documenti estratti

### 3. Layer di Validazione e Controllo
- `validation_utils.py`: Utilità per la validazione con gestione intelligente delle dipendenze opzionali
- `output_validator.py`: Validazione degli output prodotti
- `cache.py`: Sistema di caching per operazioni costose

### 4. Layer di Intelligenza Artificiale
- `llm_factory.py`: Factory per la creazione di modelli linguistici
- `trainer.py`: Addestramento dei modelli predittivi
- `ground_truth.py`: Gestione dei ground truth per il machine learning

### 5. Layer di Conoscenza e Relazioni
- `builder.py`: Costruzione del knowledge graph
- `models.py`: Modelli per rappresentare entità e relazioni
- `exporters.py`: Esportazione del grafo della conoscenza

### 6. Layer di Sicurezza e Audit
- `audit_engine.py`: Motore principale per l'audit antifrode
- `risk_calculator.py`: Calcolo dei rischi associati agli atti
- `anomalies.py`: Rilevamento di anomalie nei processi amministrativi

## Pattern di Gestione delle Dipendenze Opzionali

I moduli che richiedono dipendenze opzionali seguono il pattern di lazy loading implementato in `optional_deps.py`:

```python
# Esempio di lazy loading
try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    bcrypt = None
    BCRYPT_AVAILABLE = False
```

Questo approccio permette al sistema di funzionare anche quando alcune librerie non sono installate, fornendo messaggi di errore chiari quando queste funzionalità sono effettivamente richieste.

## Integrazione con Digital Twin

La factory `DigitalTwinEventFactory` converte i documenti parsati in eventi del Digital Twin attraverso il modello standardizzato `ParsedDocument`, consentendo una rappresentazione virtuale fedele dei processi amministrativi reali.

## Vantaggi dell'Architettura Modulare

1. **Isolamento dei Guasti**: Problemi in un modulo non compromettono l'intero sistema
2. **Testabilità**: Ogni modulo può essere testato in modo indipendente
3. **Manutenibilità**: Modifiche localizzate non hanno impatti collaterali
4. **Estensibilità**: Nuove funzionalità possono essere aggiunte senza modificare l'esistente
5. **Scalabilità**: I moduli possono essere ottimizzati individualmente

## Standard di Codifica

Tutti i moduli seguono gli standard definiti nelle specifiche di progetto:
- Interfacce contrattuali stabili
- Retrocompatibilità mantenuta
- Documentazione inline coerente
- Gestione appropriata degli errori