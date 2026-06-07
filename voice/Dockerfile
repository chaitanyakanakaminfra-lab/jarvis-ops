FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml .
RUN pip install --upgrade pip && pip install --no-cache-dir websockets deepgram-sdk requests structlog boto3 python-dotenv aiohttp
COPY voice/ /app/voice/
COPY agents/ /app/agents/
COPY config/ /app/config/
COPY orchestrator/ /app/orchestrator/
COPY memory/ /app/memory/
EXPOSE 8765
CMD ["python", "voice/browser_voice_server.py"]
