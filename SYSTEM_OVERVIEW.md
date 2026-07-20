# Panoramica del Sistema - Albo Pretorio Audit Delivery

## Introduzione

Il sistema Albo Pretorio Audit Delivery implementa un'architettura ibrida per la gestione dei comandi CLI, combinando un'interfaccia moderna basata su Click con un sistema legacy per garantire retrocompatibilità.

## Architettura del Sistema di Comandi

### 1. Interfaccia Click-based (Moderna - Consigliata)

L'interfaccia moderna è basata sulla libreria Click di Python ed offre:

- **Sintassi uniforme**: Tutti i comandi seguono lo stesso pattern `python run.py <comando>`
- **Validazione parametri**: Controllo automatico dei parametri richiesti e opzionali
- **Documentazione integrata**: Aiuto contestuale disponibile con `--help`
- **Gestione errori**: Segnalazione chiara degli errori di input
- **Integrazione IDE**: Supporto per completamento automatico

**Comandi principali:**
- `enterprise` - Workflow enterprise completo
- `audit` - Audit antifrode
- `build-kg` - Costruzione knowledge graph
- `control-room` - Dashboard di controllo
- `metrics-exporter` - Esportazione metriche
- `privacy-report` - Report conformità GDPR

### 2. Sistema Legacy (Per Retrocompatibilità)

Il sistema legacy permette di mantenere la compatibilità con versioni precedenti e script esistenti:

- **Mapping comandi**: I comandi legacy vengono mappati a script o moduli specifici
- **Compatibilità script**: Gli script esistenti continuano a funzionare senza modifiche
- **Supporto funzionalità**: Tutte le funzionalità del sistema sono accessibili



## Esempi di Utilizzo

### Esecuzione Completa (Approccio Raccomandato)
```bash
# 1. Configura ambiente
python -m venv .venv
source .venv/bin/activate  # Su Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Esegui workflow enterprise
python run.py enterprise --ente=baiano --workflow=full

# 3. Oppure esegui singoli moduli
python run.py audit --ente=baiano --use-llm
python run.py build-kg --ente=baiano
```

### Utilizzo Specifico (Approccio Legacy)
```bash
# Esecuzione pipeline completa
python run.py pipeline --ente=baiano

# Avvio dashboard
python run.py control-room

# Training modelli ML
python run.py train --ente=baiano
```

## Struttura dei Dati

### Organizzazione Directory
```
data/
├── {ente}/
│   ├── albo_download/     # Dati grezzi scaricati
│   ├── parsed_data/       # Dati parsati e strutturati
│   ├── kg/               # Knowledge graph generato
│   ├── ml_models/        # Modelli ML addestrati
│   └── reports/          # Report generati
```

### Formati Supportati
- Documenti PDF
- File HTML
- File CSV per dati strutturati
- File JSON per metadati
- File P7M per documenti firmati digitalmente

## Configurazione

### File di Configurazione
La configurazione principale si trova in `config/config.yaml` e può essere sovrascritta con variabili d'ambiente.

### Variabili d'Ambiente Principali
- `ALBO_DATA_DIR` - Directory dati
- `OPENAI_API_KEY` - Chiave API OpenAI (se utilizzata)
- `GOOGLE_API_KEY` - Chiave API Google (se utilizzata)
- `LOG_LEVEL` - Livello di logging

## Sicurezza e Privacy

### Conformità GDPR
- Implementazione del diritto all'oblio
- Tracciamento dei dati personali
- Report di conformità
- Crittografia dei dati sensibili

### Controllo Accessi
- Autenticazione richiesta per accesso a dati sensibili
- Logging delle operazioni critiche
- Separazione tra dati pubblici e privati

## Monitoraggio e Logging

### Metriche Disponibili
- Numero di documenti processati
- Tempo di elaborazione per tipo di documento
- Accuratezza delle classificazioni
- Risorse utilizzate

### Endpoint Monitoraggio
- Metrics exporter: `http://localhost:8001/metrics`
- Dashboard: `http://localhost:8501` (dopo avvio)

## Sviluppo e Contributi

### Ambiente di Sviluppo
1. Clona il repository
2. Crea ambiente virtuale
3. Installa dipendenze con `pip install -r requirements.txt`
4. Configura variabili d'ambiente necessarie

### Test
Eseguire i test con:
```bash
python -m pytest tests/
```

## Risoluzione Problemi Comuni

### Comando Non Trovato
Verifica di:
1. Essere nella directory corretta
2. Avere installato tutte le dipendenze
3. Usare il comando corretto (usa `python run.py --help` per lista)

### Errori di Permessi
Controlla i permessi di lettura/scrittura sulla directory `data/` e sui file di configurazione.

### Connessione Internet
Alcune funzionalità richiedono connessione internet (es. per servizi LLM esterni).

## Note di Versione

Questa documentazione riflette lo stato del sistema alla versione corrente. La struttura ibrida dei comandi rappresenta una fase di transizione verso un sistema completamente Click-based, mantenendo comunque la retrocompatibilità con il sistema legacy per garantire continuità operativa.