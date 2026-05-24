FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Run as a non-root user. Owning /data is important so the SQLite
# database (mounted as a named volume) is writable.
RUN groupadd --system --gid 1001 lira \
 && useradd  --system --uid 1001 --gid 1001 --create-home --home-dir /home/lira lira

WORKDIR /app

COPY backend/bot/requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

COPY backend /app/backend
COPY web     /app/web
COPY main.py /app/main.py

ENV PYTHONPATH=/app/backend \
    API_HOST=0.0.0.0 \
    API_PORT=8000 \
    DATABASE_URL=sqlite+aiosqlite:////data/app.db

RUN mkdir -p /data && chown -R lira:lira /data /app

VOLUME ["/data"]
EXPOSE 8000

USER lira

# --forwarded-allow-ips=127.0.0.1 — the upstream proxy is Caddy on the
#   docker host, reached through the published 127.0.0.1:8000 port, so
#   the source IP uvicorn sees is always loopback. Using "*" here would
#   let any caller spoof X-Forwarded-For.
# --proxy-headers — trust the proxy's X-Forwarded-{Proto,For} so HTTPS
#   detection and client IP logging work behind Caddy.
CMD ["uvicorn", "main:app", \
     "--host", "0.0.0.0", "--port", "8000", \
     "--proxy-headers", "--forwarded-allow-ips=127.0.0.1"]
