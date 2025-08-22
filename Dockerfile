FROM python:3.11-slim

# Install FFmpeg and system dependencies
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY api.py .

# Create directories
RUN mkdir -p temp_downloads

# Expose port
EXPOSE 5000

# Simple start command
CMD ["python", "-m", "waitress", "--host=0.0.0.0", "--port=5000", "--threads=4", "api:app"]
