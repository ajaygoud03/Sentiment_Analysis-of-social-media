# Dockerfile for Cloud Run (CPU)
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV PORT=8080

WORKDIR /app

# System deps needed for torch/transformers
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements early to leverage cache
COPY requirements.txt ./

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Expose (Cloud Run uses PORT)
EXPOSE 8080

# Use gunicorn pointing to backend.app:app, Cloud Run will set $PORT
CMD ["gunicorn", "backend.app:app", "--workers=2", "--bind=0.0.0.0:8080", "--timeout", "300"]
