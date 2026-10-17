FROM python:3.11-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       libgl1 libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && rm /tmp/requirements.txt

# The container runs as the host user (see docker-compose.yml `user:`), so there is no
# home directory. Point HOME and the PaddleX model cache at the mounted /models volume so
# models download once and persist across restarts and rebuilds.
ENV HOME=/models \
    PADDLE_PDX_CACHE_HOME=/models/.paddlex \
    PYTHONUNBUFFERED=1 \
    APP_MODULE=server:app

RUN mkdir -p /input /output /models \
    && chmod 777 /output /models

COPY . /app

EXPOSE 8000

# The first start can take a while (model download + load), hence the long start-period.
HEALTHCHECK --interval=30s --timeout=5s --start-period=300s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)" || exit 1

CMD ["sh", "-c", "exec uvicorn \"$APP_MODULE\" --host 0.0.0.0 --port 8000"]
