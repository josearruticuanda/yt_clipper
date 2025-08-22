FROM python:3.11-slim

# Install FFmpeg and system dependencies
RUN apt-get update && \
    apt-get install -y \
    ffmpeg \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first (for better Docker layer caching)
COPY requirements.txt .

# Install Python packages with explicit waitress
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir waitress==3.0.0

# Copy application code
COPY api.py .

# Create temp downloads directory
RUN mkdir -p temp_downloads

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port (Railway will auto-detect)
EXPOSE 5000

# Start command with environment variable fallback
CMD python -c "import os; os.system(f'python -m waitress --host=0.0.0.0 --port={os.environ.get(\"PORT\", \"5000\")} --threads=4 api:app')"
