# 🤖 Jarvis AI Ops Platform

> Voice-controlled AI DevOps & Infrastructure platform — 15 specialized agents,
> powered by LangChain + GPT-4o, deployed on AWS EKS.

## Quick Start
```bash
cp .env.example .env   # fill in your API keys
make run               # start local stack
make listen            # start voice session — say "Hey Jarvis"
```

## Architecture
- **Jarvis Brain** — LangChain AgentExecutor routes voice commands to agents
- **15 Agents** — CI/CD, Infra, Cost, Security, Observability, Reporting
- **Voice layer** — Porcupine wake word + Whisper STT + ElevenLabs TTS
- **Runtime** — Argo Workflows on AWS EKS
- **Triggers** — Argo Events (GitHub webhooks + cron schedules)
- **Secrets** — AWS Secrets Manager + External Secrets Operator
- **Memory** — ChromaDB (vector) + Postgres (run history)

## 15 Agents

| # | Agent | Category |
|---|-------|----------|
| 01 | CI/CD Pipeline | CI/CD |
| 02 | Lint & Code Quality | CI/CD |
| 03 | Docker & Image | CI/CD |
| 04 | Release & Versioning | CI/CD |
| 05 | Infra Provisioning | Infrastructure |
| 06 | Kubernetes Ops | Infrastructure |
| 07 | Cloud Config | Infrastructure |
| 08 | DR & Backup | Infrastructure |
| 09 | Cost Optimization | Cost |
| 10 | Auto-Scaling | Cost |
| 11 | Security Scanning | Security |
| 12 | Compliance | Security |
| 13 | Observability | Observability |
| 14 | Incident Response | Observability |
| 15 | Reporting & Insights | Intelligence |

## Build Phases

| Phase | Days | What gets built |
|-------|------|-----------------|
| 1 — Foundation | 1–7 | AWS EKS + Argo + Voice layer + Brain |
| 2 — CI/CD Agents | 8–14 | Agents 01–04 |
| 3 — Infra Agents | 15–21 | Agents 05–08 |
| 4 — Cost + Security | 22–28 | Agents 09–12 + UI |
| 5 — Observability | 29–32 | Agents 13–15 |
| 6 — Deploy + Polish | 33–37 | GitOps + domain + demo video |

## Voice Commands
- *"Hey Jarvis, run the pipeline"* → CI/CD agent
- *"Hey Jarvis, how are cloud costs?"* → Cost agent
- *"Hey Jarvis, check the cluster"* → Kubernetes Ops agent
- *"Hey Jarvis, we have an incident"* → Incident Response agent
- *"Hey Jarvis, weekly summary"* → Reporting agent

## Tech Stack
Python 3.11 · FastAPI · LangChain · GPT-4o · Porcupine · Whisper · ElevenLabs ·
AWS EKS · Argo Workflows · Argo Events · ChromaDB · Postgres · Terraform · Docker
