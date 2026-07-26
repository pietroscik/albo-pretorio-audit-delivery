# Usa l'immagine ufficiale Playwright con Python
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

# Imposta la directory di lavoro
WORKDIR /app

# Copia i file di dipendenza prima del codice sorgente per sfruttare la cache Docker
COPY requirements.txt .

# Installa le dipendenze Python
# L'immagine base di Playwright include già i browser e le loro dipendenze, quindi non è necessario installarli.
RUN pip install --no-cache-dir -r requirements.txt

# Copia il codice sorgente
COPY . .

# Installa il pacchetto in modalità sviluppo per rendere disponibili i moduli
RUN pip install -e .

# Aggiungi la directory principale al PYTHONPATH
ENV PYTHONPATH=/app:$PYTHONPATH

# Crea le directory necessarie per i dati
RUN mkdir -p data/sperone/albo_download/pdf \
    && mkdir -p data/albo_download/report \
    && mkdir -p logs

# Imposta l'utente non-root per motivi di sicurezza
RUN groupadd -r appgroup && useradd -r -g appgroup appuser && \
    chown -R appuser:appgroup /app
USER appuser

# Espose la porta per eventuali dashboard Streamlit
EXPOSE 8501 8502 8503 8504

# Comando di default
CMD ["python", "-m", "src.delibere_comunali.scraping.new_albo_scraper", "--ente", "sperone", "--max-pages", "1"]