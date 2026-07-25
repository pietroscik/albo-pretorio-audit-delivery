# Usa l'immagine ufficiale Playwright con Python
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

# Aggiorna il sistema e installa dipendenze necessarie per l'esecuzione dei browser headless
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libnss3 \
        libatk-bridge2.0-0 \
        libdrm2 \
        libxkbcommon0 \
        libxcomposite1 \
        libxdamage1 \
        libxrandr2 \
        libgbm1 \
        libxss1 \
        libasound2 \
        fonts-liberation \
        libappindicator3-1 \
        libcurl4-openssl-dev \
        libdbus-glib-1-2 \
        libgtk-3-0 \
        libxtst6 \
        xdg-utils && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Imposta la directory di lavoro
WORKDIR /app

# Copia i file di dipendenza prima del codice sorgente per sfruttare la cache Docker
COPY requirements.txt .

# Installa le dipendenze Python
RUN pip install --no-cache-dir -r requirements.txt

# Installa Playwright browsers (necessario dopo aver installato le dipendenze di sistema)
RUN playwright install chromium

# Copia il codice sorgente
COPY . .

# Crea le directory necessarie per i dati
RUN mkdir -p data/sperone/albo_download/pdf \
    && mkdir -p data/albo_download/report \
    && mkdir -p logs

# Imposta l'utente non-root per motivi di sicurezza
RUN groupadd -r appgroup && useradd -r -g appgroup appuser && \
    chown -R appuser:appgroup /app
USER appuser

# Espone la porta per eventuali dashboard Streamlit
EXPOSE 8501 8502 8503 8504

# Comando di default
CMD ["python", "-m", "src.delibere_comunali.scraping.new_albo_scraper", "--ente", "sperone", "--max-pages", "1"]