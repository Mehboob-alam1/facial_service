# Smart Campus Face API — Railway / Docker
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py start.sh ./
RUN chmod +x start.sh

ENV EMBEDDINGS_DIR=/data/embeddings
RUN mkdir -p /data/embeddings

EXPOSE 8080

CMD ["./start.sh"]
