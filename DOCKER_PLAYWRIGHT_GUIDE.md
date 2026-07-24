# Docker e Playwright: Guida all'Utilizzo

Questa guida spiega come il sistema utilizza Docker per risolvere i problemi di compatibilità tra Playwright e alcuni ambienti locali.

## Il Problema di Compatibilità

Come evidenziato nel sistema, esiste un problema noto tra:
- Python 3.13 su Windows
- Playwright e la sua gestione dei subprocess
- Il nuovo event loop di asyncio su Windows

Questo problema causa un `NotImplementedError` quando Playwright tenta di creare subprocess per comunicare con Chromium.

## La Soluzione Docker

Docker risolve questo problema in quanto:
- Fornisce un ambiente Linux standardizzato
- Usa l'event loop `epoll` (su Linux) invece del problematico `ProactorEventLoop` di Windows
- Include tutte le dipendenze di sistema necessarie per far girare i browser headless
- Isola l'applicazione dall'ambiente host

## Architettura Docker

### Immagine Base
L'immagine usa `mcr.microsoft.com/playwright/python:v1.44.0-jammy` che include:
- Python 3.11 (compatibile con Playwright)
- Chromium e tutte le dipendenze di sistema
- Librerie necessarie per l'esecuzione di browser headless

### Sicurezza
- L'applicazione gira con un utente non-root (`appuser`)
- Accesso limitato al filesystem host tramite volumi
- Nessuna esposizione diretta di porte se non necessario

## Utilizzo Consigliato

### Sviluppo Locale
```bash
# Per testare le funzionalità complete di Playwright
docker-compose up scraper
```

### Produzione
```bash
# Per un deployment completo
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Debugging

Se si verificano problemi con Playwright all'interno del container:

```bash
# Accedi al container
docker exec -it albo-scraper bash

# Controlla la versione di Chromium
google-chrome --version

# Testa Playwright
python -c "from playwright.sync_api import sync_playwright; pw = sync_playwright().start(); browser = pw.chromium.launch(); print('Success')"
```

## Performance Tuning

Per ottimizzare le prestazioni in container:

1. **Limiti di Risorsa**: Usa `deploy.resources` in docker-compose per limitare CPU/RAM
2. **Concordanza Browser Context**: Riutilizza i contesti browser invece di crearne di nuovi per ogni richiesta
3. **Cache**: Sfrutta la cache Docker durante il build per velocizzare i rebuild

## Best Practice

- Non esporre porte se non necessario in ambiente di scraping puro
- Usa volumi per persistere i dati scaricati
- Monitora l'utilizzo di memoria del container durante operazioni intensive
- Usa restart policies appropriate per garantire uptime in produzione