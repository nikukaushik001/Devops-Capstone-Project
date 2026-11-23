# Multi-Stage Production Hardened Dockerfile
# Stage 1: Build & Dependency Resolution
FROM python:3.11-slim AS builder

WORKDIR /build
COPY requirements.txt .

RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev \
    && pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Final Minimal & Distroless-like Runtime Image
FROM python:3.11-slim AS runner

WORKDIR /app

# Security: Dedicated non-root user (UID 10001)
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/false appuser

COPY --from=builder /root/.local /home/appuser/.local
COPY --chown=appuser:appgroup main.py .

ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/liveness')" || exit 1

ENTRYPOINT ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

