# Use the Python 3.11 template for Railway
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

ENV EMBEDDINGS_DIR=/data/embeddings
ENV PORT=8080
RUN mkdir -p /data/embeddings

EXPOSE 8080

# Expand $PORT at container start (Railway sets PORT at runtime)
CMD ["sh", "-c", "gunicorn app:app --bind 0.0.0.0:${PORT:-8080} --workers 1 --threads 4 --timeout 120"]
