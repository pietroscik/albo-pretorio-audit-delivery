# Esempi di Utilizzo

Questa guida mostra come utilizzare i vari comandi del sistema Albo Pretorio Audit Delivery con esempi pratici e completi.

## Due Sistemi di Comando

Il sistema dispone di due modalità di utilizzo:

1. **Interfaccia Click-based (Consigliata)** - Comandi disponibili direttamente con `python run.py <comando>`
2. **Sistema Legacy** - Comandi accessibili tramite il sistema di mapping per compatibilità

## Esecuzione della Pipeline Completa

### Pipeline Standard (Modalità Moderna)
```bash
# Esecuzione della pipeline completa per un ente specifico
python run.py pipeline --ente=baiano

# Con opzioni avanzate
python run.py pipeline --ente=baiano --limit 5
```

### Pipeline Enterprise
```bash
# Esecuzione workflow enterprise completo
python run.py enterprise --ente=comune_di_esempio --workflow=full

# Esecuzione workflow solo analisi
python run.py enterprise --ente=comune_di_esempio --workflow=analyze-only

# Esecuzione workflow solo scraping
python run.py enterprise --ente=comune_di_esempio --workflow=scrape-only

# Con file di configurazione personalizzato
python run.py enterprise --ente=comune_di_esempio --config=config/personalizzato.yaml
```

## Esecuzione di Singoli Moduli (Modalità Moderna)

### Estrazione Dati (Scraping)
```bash
# Estrazione dati per un ente specifico (se disponibile)
python run.py scrape --ente=baiano

# Estrazione con date specifiche (solo se il modulo è disponibile)
python run.py scrape --ente=baiano --date-from 2023-01-01 --date-to 2023-01-31
```

### Analisi e Parsing
```bash
# Analisi dei documenti scaricati
python run.py analyze --ente=baiano

# Analisi con utilizzo di LLM
python run.py analyze --ente=baiano --use-llm

# Analisi con provider LLM specifico
python run.py analyze --ente=baiano --use-llm --llm-provider=openai --llm-model=gpt-4
```

### Audit Antifrode
```bash
# Esecuzione audit standard
python run.py audit --ente=baiano

# Esecuzione audit con LLM
python run.py audit --ente=baiano --use-llm

# Esecuzione audit con provider e modello specifici
python run.py audit --ente=baiano --use-llm --llm-provider=gemini --llm-model=gemini-pro
```

### Knowledge Graph
```bash
# Costruzione del knowledge graph
python run.py build-kg --ente=baiano

# Analisi della topologia del knowledge graph
python run.py analyze-topology --ente=baiano
```

### Post-Elaborazione Classificazioni
```bash
# Post-process delle classificazioni OCR
python run.py post-process-classification --input=data/input.csv --output=data/output.csv
```

## Dashboard e Interfacce (Modalità Moderna)

### Control Room
```bash
# Avvio della dashboard di controllo
python run.py control-room

# Alternativamente
python run.py ui
python run.py dashboard
```

## Machine Learning e Analisi Avanzate (Modalità Moderna)

### Training Modelli
```bash
# Training del modello ML
python run.py train --ente=baiano

# Training supervisionato
python run.py supervised-training --ente=baiano
```

### Analisi del Rischio
```bash
# Esecuzione risk assessment
python run.py risk-assessment --ente=baiano

# Con opzioni specifiche
python run.py risk-assessment --ente=baiano --base=data/baiano/albo_download
```

### KPI di Gestione
```bash
# Calcolo KPI di gestione
python run.py management-kpi --ente=baiano
```

### Analisi Attuariale
```bash
# Esecuzione analisi attuariale
python run.py actuarial-analysis --ente=baiano
```

## Operazioni di Manutenzione (Modalità Moderna)

### Validazione Dati
```bash
# Validazione output
python run.py validate-output --ente=baiano

# Validazione CSV
python run.py validate-csv --ente=baiano
```

### Pulizia Dati
```bash
# Pulizia testi
python run.py clean-texts --ente=baiano

# Sincronizzazione testi
python run.py sync-texts --ente=baiano
```

## Privacy e GDPR (Modalità Moderna)

### Report di Conformità GDPR
```bash
# Generazione report di conformità GDPR
python run.py privacy-report --ente=baiano
```

### Diritto all'Oblio
```bash
# Cancellazione dati utente (diritto all'oblio)
python run.py gdpr-delete --user-identifier=CF12345678901

# Con percorso dati specifico
python run.py gdpr-delete --user-identifier=CF12345678901 --data-path=data/custom_path/
```

## Sistema Legacy (Per Compatibilità)

Il sistema supporta anche il sistema legacy di comandi per compatibilità con versioni precedenti:

### Comandi Base
```bash
# Esecuzione della pipeline completa (modalità legacy)
python run.py pipeline --ente=baiano

# Estrazione dati (modalità legacy)
python run.py scrape --ente=baiano

# Analisi dati (modalità legacy)
python run.py analyze --ente=baiano
```

### Dashboard e UI (Modalità Legacy)
```bash
# Avvio della dashboard (modalità legacy)
python run.py control-room
python run.py ui
python run.py dashboard
```

## Opzioni Comuni

Molti comandi accettano le seguenti opzioni comuni:

- `--ente`: Nome dell'ente locale (obbligatorio per la maggior parte dei comandi)
- `--base`: Directory base per i dati (default: data/{ente}/albo_download)
- `--use-llm`: Abilita l'arricchimento con LLM
- `--llm-provider`: Provider LLM da utilizzare (openai, gemini, mistral, ecc.)
- `--llm-model`: Modello LLM specifico da utilizzare
- `--force`: Forza l'esecuzione anche se i risultati sono già presenti

## Risoluzione Problemi Comuni

### Comando non trovato
Se ricevi un messaggio "comando non trovato", assicurati di:
1. Essere nella directory principale del progetto
2. Avere installato tutte le dipendenze
3. Usare il nome corretto del comando (controlla con `python run.py --help`)

### Errori di permessi
Se ricevi errori di permessi durante l'esecuzione:
1. Controlla di avere i permessi di lettura/scrittura sulla directory `data/`
2. Verifica che il processo abbia accesso ai file di configurazione

### Porta già in uso
Se ricevi errori relativi a porte già in uso (es. 8501 per la dashboard):
1. Chiudi eventuali istanze precedenti dell'applicazione
2. Usa un'altra porta se disponibile