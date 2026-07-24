# Comandi del Sistema - Reference Attuale

## Comandi Raccomandati (Modalità Enterprise)

I seguenti comandi rappresentano l'interfaccia ufficiale del sistema:

### Modalità Enterprise Completa
```bash
# Esecuzione completa (scraping + analisi)
python run.py enterprise --ente {nome_ente} --workflow full

# Solo scraping
python run.py enterprise --ente {nome_ente} --workflow scrape-only

# Solo analisi (richiede dati già scaricati)
python run.py enterprise --ente {nome_ente} --workflow analyze-only
```

### Singoli Componenti
```bash
# Solo scraping diretto
python -m src.delibere_comunali.scraping.new_albo_scraper --ente {nome_ente} --max-pages {numero}

# Solo analisi diretta
python -m src.delibere_comunali.parsing.analyze_albo --ente {nome_ente}

# Generazione knowledge graph
python run.py build-kg --ente {nome_ente}

# Audit specifico
python run.py audit --ente {nome_ente}
```

### Parametri Supportati
- `--ente`: Nome dell'ente comunale (es. sperone, avella)
- `--workflow`: Modalità di esecuzione (full, scrape-only, analyze-only)
- `--max-pages`: Numero massimo di pagine da elaborare (solo per scraping)
- `--delay`: Ritardo tra le richieste (secondi)
- `--no-download`: Solo estrazione metadati, nessun download

## Comandi Legacy (Da Non Utilizzare)

I seguenti comandi sono mantenuti per retrocompatibilità ma non sono raccomandati:

```bash
# DEPRECATO: Utilizzare invece python run.py enterprise
python main.py --ente {nome_ente}

# DEPRECATO: Utilizzare invece il modulo diretto
python src/delibere_comunali/scraping/scraper.py --ente {nome_ente}
```

## Workflows Disponibili

### `--workflow full`
- Esegue sia scraping che analisi
- Produce tutti i file di output
- Richiede connessione Internet per lo scraping

### `--workflow scrape-only`
- Esegue solo la fase di scraping
- Scarica documenti e genera metadati
- Richiede connessione Internet

### `--workflow analyze-only`
- Esegue solo la fase di analisi
- Richiede dati già scaricati in `data/{ente}/albo_download/`
- Non richiede connessione Internet

## Comandi di Diagnostica

```bash
# Controllo stato ente
python run.py status --ente {nome_ente}

# Validazione output
python run.py validate --ente {nome_ente}

# Esplorazione dati
python run.py explore --ente {nome_ente}
```

## Note Importanti

- I comandi con parametro `--workflow` sono i soli ufficialmente supportati
- Non esistono flag come `risk_only` o `kpi_only` implementati in `run.py`
- La modalità enterprise è l'unica interfaccia ufficiale verso l'utente finale
- I moduli diretti sono destinati principalmente al debugging e testing