# 1. Usa un'immagine ufficiale di Python leggera come base (sistema operativo)
FROM python:3.11-slim

# 2. Imposta la directory di lavoro all'interno del container
WORKDIR /app

# Variabili d'ambiente per ottimizzare Python nel container
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. Installa le dipendenze di sistema necessarie (Tesseract OCR per l'italiano e librerie grafiche per OpenCV)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-ita \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 4. Copia il file dei requisiti e installa le dipendenze Python
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 5. Copia tutto il resto del codice dell'applicazione nel container
COPY . .

# 6. Esponi la porta 8501 per rendere visibile l'interfaccia Streamlit all'esterno
EXPOSE 8501

# 7. Comando da eseguire quando il container si avvia
CMD ["streamlit", "run", "app_control_room.py", "--server.port=8501", "--server.address=0.0.0.0"]