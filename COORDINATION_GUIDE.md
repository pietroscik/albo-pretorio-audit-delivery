# Guida al Sistema di Coordinamento Centrale

## Introduzione

Il sistema di coordinamento centrale è una novità importante nell'architettura del sistema di audit dell'albo pretorio. Consente ai diversi moduli avanzati (Risk Assessment, KPI Manageriali, Analisi ML, Audit) di comunicare tra loro, scambiarsi informazioni e influenzarsi reciprocamente.

## Comandi Disponibili

### 1. orchestrate

Il comando `orchestrate` esegue l'intera pipeline di coordinamento tra tutti i moduli avanzati:

```bash
# Esecuzione completa di coordinamento
python run.py orchestrate --ente <nome_ente>

# Esecuzione con opzioni specifiche
python run.py orchestrate --ente avella --skip-risk  # Salta risk assessment
python run.py orchestrate --ente avella --skip-kpi   # Salta calcolo KPI
python run.py orchestrate --ente avella --dry-run    # Simulazione senza salvare
```

#### Funzionalità:
- Esegue il risk assessment e salva i risultati
- Calcola i KPI manageriali e li integra con i risultati del risk assessment
- Esegue l'analisi ML e adatta i modelli in base ai risultati precedenti
- Esegue l'audit utilizzando tutti i risultati precedenti
- Salva i risultati coordinati in formato strutturato

### 2. data-coord

Il comando `data-coord` permette di interagire con il coordinatore dati centralizzato:

```bash
# Ottenere un sommario dei dati
python run.py data-coord --ente avella --action summary

# Listare tutte le chiavi dei dati disponibili
python run.py data-coord --ente avella --action list

# Ottenere un dato specifico
python run.py data-coord --ente avella --action get --key "atti_parsed"

# Salvare un dato specifico
python run.py data-coord --ente avella --action save --key "test_data" --data '{"value": 42}' --module "test"

# Caricare dati da persistenza
python run.py data-coord --ente avella --action load

# Cancellare tutti i dati
python run.py data-coord --ente avella --action clear
```

#### Funzionalità:
- Gestisce la persistenza dei dati condivisi tra i moduli
- Permette di ispezionare i dati attualmente memorizzati
- Consente di salvare e recuperare dati specifici
- Supporta l'analisi e il debug del sistema di coordinamento

## Flusso di Esecuzione Coordinata

Quando si esegue `python run.py orchestrate --ente <nome>`, il sistema esegue il seguente flusso:

1. **Inizializzazione**: Caricamento dei dati condivisi da `atti_parsed.csv`
2. **Risk Assessment**: Esecuzione del modulo di valutazione del rischio
3. **Feedback KPI**: I risultati del risk assessment influenzano i parametri KPI
4. **Calcolo KPI**: Esecuzione del modulo di calcolo dei KPI manageriali
5. **Feedback Rischi**: I risultati KPI influenzano le soglie del risk assessment
6. **Analisi ML**: Esecuzione del modulo di analisi machine learning
7. **Adattamento Modelli**: I risultati ML influenzano i modelli e i pesi
8. **Audit**: Esecuzione del modulo di audit utilizzando tutti i risultati precedenti
9. **Salvataggio**: I risultati coordinati vengono salvati in `coordinated_analysis_results.json`

## File di Output

Il sistema di coordinamento genera i seguenti file di output:

- `data/{ente}/albo_download/report/coordinated_analysis_results.json`: Risultati coordinati di tutti i moduli
- `data/{ente}/albo_download/report/risk_assessment_coordinated.csv`: Versione coordinata dei risultati del risk assessment
- `data/{ente}/albo_download/report/kpi_manageriali_coordinated.csv`: Versione coordinata dei risultati KPI
- File di log dettagliati nel processo di coordinamento

## Benefici del Sistema di Coordinamento

1. **Integrazione**: I moduli avanzati ora comunicano tra loro anziché operare in isolamento
2. **Feedback Continuo**: I risultati di un modulo possono influenzare i parametri di un altro
3. **Coerenza**: Tutti i moduli accedono agli stessi dati attraverso il coordinatore
4. **Estensibilità**: Nuovi moduli possono essere facilmente integrati nel sistema
5. **Monitoraggio**: È possibile tracciare come i dati fluiscono tra i diversi moduli

## Esempi di Utilizzo

### Scenario Standard
```bash
# Esegui l'intero processo di coordinamento per l'ente Avella
python run.py orchestrate --ente avella
```

### Debug del Sistema di Coordinamento
```bash
# Controlla quali dati sono disponibili nel coordinatore
python run.py data-coord --ente avella --action summary

# Ottieni specifici risultati del risk assessment
python run.py data-coord --ente avella --action get --key "risk_scores"
```

### Esecuzione Parziale
```bash
# Esegui coordinamento senza risk assessment (se già eseguito)
python run.py orchestrate --ente avella --skip-risk

# Esegui coordinamento senza KPI (se già eseguito)
python run.py orchestrate --ente avella --skip-kpi
```

## Architettura del Sistema

Il sistema di coordinamento è implementato attraverso due componenti principali:

1. **[CentralOrchestrator](file:///c%3A/Users/39329/albo-pretorio-audit-delivery/src/delibere_comunali/core/orchestrator.py#L29-L436)**: Coordinatore principale che gestisce l'esecuzione sequenziale dei moduli con feedback reciproco
2. **[DataCoordinator](file:///c%3A/Users/39329/albo-pretorio-audit-delivery/src/delibere_comunali/core/data_coordinator.py#L51-L449)**: Sistema centralizzato per la gestione dei dati condivisi tra i moduli

Questa architettura permette di mantenere i moduli esistenti invariati mentre introduce la capacità di coordinamento tra di essi.