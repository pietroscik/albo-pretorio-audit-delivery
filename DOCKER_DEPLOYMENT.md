# Deployment con Docker

## Panoramica

Questo documento descrive come containerizzare e distribuire il sistema di audit per albi pretori comunali utilizzando Docker. Il sistema include OCR completo per documenti scansionati e un'architettura enterprise-ready.

## Requisiti

- Docker versione 20.10 o superiore
- Docker Compose (opzionale ma raccomandato per deployment multi-container)

## Build del Container

### Build Standard
```bash
docker build -t albo-pretorio-audit .
```

### Build con Specificazione della Piattaforma (per sistemi ARM come Apple Silicon)
```bash
docker build --platform linux/amd64 -t albo-pretorio-audit .
```

## Esecuzione del Container

### Esecuzione Base
```bash
docker run -it --rm albo-pretorio-audit
```

### Esecuzione con Volume Montato per i Dati
```bash
docker run -it --rm \
  -v ./data:/app/data \
  albo-pretorio-audit
```

### Esecuzione con Variabili d'Ambiente
```bash
docker run -it --rm \
  -v ./data:/app/data \
  -v ./config:/app/config \
  -e PYTHON_ENV=production \
  -e LOG_LEVEL=INFO \
  albo-pretorio-audit
```

### Esecuzione del Dashboard Web
```bash
docker run -it --rm \
  -v ./data:/app/data \
  -p 8501:8501 \
  albo-pretorio-audit \
  streamlit run src/delibere_comunali/web/dashboard.py --server.port 8501 --server.address 0.0.0.0
```

## Docker Compose

Per deployment più complessi, è possibile utilizzare Docker Compose:

```yaml
version: '3.8'

services:
  audit-engine:
    build: .
    volumes:
      - ./data:/app/data
      - ./config:/app/config
    environment:
      - PYTHON_ENV=production
      - LOG_LEVEL=INFO
    command: ["python", "-m", "src.delibere_comunali.cli.run_pipeline"]
    
  web-dashboard:
    build: .
    volumes:
      - ./data:/app/data
    ports:
      - "8501:8501"
    command: ["streamlit", "run", "src/delibere_comunali/web/dashboard.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
    depends_on:
      - audit-engine
```

## Ottimizzazioni del Dockerfile

Il Dockerfile è stato ottimizzato per:

1. **Dimensioni Ridotte**: Uso di `python:3.10-slim` come base
2. **Installazione Minimale**: Solo le librerie di sistema necessarie per OpenCV e Tesseract
3. **Sicurezza**: Esecuzione come utente non-root
4. **Cache Docker**: Ordine ottimale dei layer per sfruttare la cache
5. **Isolamento**: Ambiente pulito senza dipendenze esterne

## Dipendenze di Sistema Installate

- `libglib2.0-0`: Libreria fondamentale per GTK
- `libsm6`, `libxext6`, `libxrender-dev`: Supporto per rendering grafico
- `libgomp1`: Supporto per OpenMP (richiesto da alcune librerie scientifiche)
- `libgl1-mesa-glx`: Supporto OpenGL
- `tesseract-ocr`: Engine OCR
- `tesseract-ocr-ita`: Pacchetto lingua italiana per Tesseract
- `poppler-utils`: Utilità per la manipolazione PDF

## Best Practices Implementate

1. **Multi-stage Builds**: Non implementato in questa versione per mantenere la semplicità, ma disponibile come ottimizzazione futura
2. **Layer Caching**: Il file `requirements.txt` è copiato separatamente per massimizzare la cache
3. **Security**: Esecuzione come utente non-root
4. **Environment Variables**: Gestione delle variabili d'ambiente
5. **Health Checks**: Disponibile come estensione futura

## Considerazioni per la Produzione

1. **Persistenza Dati**: Utilizzare volumi persistenti per la directory `data/`
2. **Logging**: Configurare un sistema di logging centralizzato
3. **Monitoring**: Aggiungere health checks e metriche
4. **Sicurezza**: Considerare l'uso di un registry privato e scanning delle immagini
5. **Networking**: Configurare correttamente le policy di rete

## Debugging del Container

Per entrare nel container in modalità debug:
```bash
docker run -it --entrypoint=/bin/bash albo-pretorio-audit
```

Per controllare le dipendenze installate:
```bash
docker run --rm albo-pretorio-audit pip list
```

## Dimensioni dell'Immagine

Grazie alle ottimizzazioni, l'immagine finale dovrebbe essere inferiore a 800MB, molto meno rispetto a una versione non ottimizzata (>1.5GB).