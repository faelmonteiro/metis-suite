FROM python:3.11-slim AS builder

WORKDIR /build

COPY requirements.txt .

RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

COPY --from=builder /install /usr/local

COPY app.py .
COPY config_models.json .
COPY assets ./assets
COPY agente ./agente

RUN mkdir -p /app/historico && useradd -m appuser && chown -R appuser:appuser /app
USER appuser

CMD ["python", "app.py"]
