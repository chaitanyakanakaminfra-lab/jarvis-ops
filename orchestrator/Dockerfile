FROM python:3.11-slim AS builder
WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ portaudio19-dev && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -e "." --target /build/packages

FROM python:3.11-slim AS runtime
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    portaudio19-dev mpg123 curl && rm -rf /var/lib/apt/lists/*
COPY --from=builder /build/packages /usr/local/lib/python3.11/site-packages/
COPY orchestrator/ /app/orchestrator/
COPY agents/ /app/agents/
COPY voice/ /app/voice/
COPY config/ /app/config/
COPY memory/ /app/memory/
COPY api/ /app/api/
RUN useradd --uid 1000 --no-create-home jarvis
USER jarvis
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1
CMD ["python", "-m", "orchestrator.main"]
