# Use a slim Python base image for smaller footprint
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies for OpenCV and Tesseract
# Group apt-get commands in a single RUN instruction for optimization
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgl1-mesa-glx \
    tesseract-ocr \
    tesseract-ocr-ita \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
# Copy the lock file for reproducible builds, consistent with CI pipelines
COPY requirements.lock .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip pip-tools && \
    # Use pip-sync to ensure the environment exactly matches the lock file
    pip-sync requirements.lock

# Copy the rest of the application code
COPY . .

# Create a non-root user for security
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port for web applications (if needed)
EXPOSE 8501

# Default command for the container
CMD ["python", "-m", "src.delibere_comunali.cli.run_pipeline"]