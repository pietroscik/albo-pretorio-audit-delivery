# Albo Pretorio Audit Delivery

Sistema per l'analisi e l'audit degli albi pretori comunali italiani, con particolare focus sulla conformità AgID e sull'integrazione con sistemi Halleyweb.

## Compatibilità Ambiente

Il sistema è progettato per funzionare in diversi ambienti, ma alcune funzionalità richiedono considerazioni specifiche:

- **Windows con Python 3.13**: Funzionalità di scraping JavaScript (necessarie per Halleyweb) limitate a causa di un problema noto con Playwright su questa combinazione. Lo scraping dei metadati funziona regolarmente, ma il download degli allegati potrebbe non funzionare.
- **Linux/macOS o Docker**: Consigliato per il pieno funzionamento delle funzionalità, inclusi lo scraping JavaScript e il download degli allegati da siti Halleyweb.
- **Docker**: Disponibile un'immagine specifica `mcr.microsoft.com/playwright/python` per garantire compatibilità completa.

## Installazione e Setup

### Metodo 1: Installazione Locale

```bash
# Clona il repository
git clone <repository_url>
cd albo-pretorio-audit-delivery

# Crea un ambiente virtuale
python -m venv .venv
source .venv/bin/activate  # Su Windows: .venv\Scripts\activate

# Installa le dipendenze
pip install -r requirements.txt

# Installa Playwright e i browser necessari
pip install playwright
playwright install chromium
```

### Metodo 2: Docker Deployment (Consigliato)

Per garantire il pieno funzionamento su tutti i sistemi, inclusi Windows con Python 3.13:

```bash
# Avvia l'intero sistema con Docker Compose
docker-compose up -d

# I servizi saranno disponibili su:
# - Control Room: http://localhost:8501
# - RAG App: http://localhost:8504
# - Web Dashboard: http://localhost:8503
```

## Quick Start

### Modalità Completa (Scraping + Analisi)
```bash
# Esegui l'intero workflow per un comune (in ambiente locale)
python run.py enterprise --ente sperone --workflow full

# Esegui solo la fase di scraping
python run.py enterprise --ente sperone --workflow scrape-only

# Esegui solo la fase di analisi
python run.py enterprise --ente sperone --workflow analyze-only
```

### Comandi Docker (Se utilizzato il deployment Docker)
```bash
# Esegui un workflow completo per un comune
docker-compose exec app python run.py enterprise --ente sperone --workflow full

# Esegui solo lo scraping
docker-compose exec app python run.py enterprise --ente sperone --workflow scrape-only

# Esegui solo l'analisi
docker-compose exec app python run.py enterprise --ente sperone --workflow analyze-only

# Accedi alla shell del container
docker-compose exec app bash
```

### Comandi Specifici
```bash
# Esegui solo lo scraping
python -m src.delibere_comunali.scraping.new_albo_scraper --ente sperone --max-pages 5

# Esegui solo l'analisi
python -m src.delibere_comunali.parsing.analyze_albo --ente sperone

# Costruisci il knowledge graph
python run.py build-kg --ente sperone
```

## Struttura del Progetto

Per una panoramica dettagliata dell'architettura, vedere [ARCHITECTURE.md](./ARCHITECTURE.md).

## Output del Sistema

Dopo un'esecuzione completa, il sistema genera:

- **Metadati**: `data/{ente}/albo_download/albo_metadati.csv`
- **Documenti**: `data/{ente}/albo_download/pdf/`
- **Report di Analisi**: `data/{ente}/albo_download/report/`
- **CSV Strutturati**: `allegati_parsed.csv`, `atti_parsed.csv`
- **Knowledge Graph**: `knowledge_graph.gexf`, `knowledge_graph.html`
- **Report Testuali**: `procedural_analysis_report.md`, `alert_antifrode.md`

## Comandi Disponibili

Per una lista completa dei comandi disponibili, vedere [docs/CURRENT_COMMANDS.md](./docs/CURRENT_COMMANDS.md).

## Licenza

Questo software è fornito come è, senza alcuna garanzia. Vedi il file LICENSE per maggiori dettagli.