.PHONY: help run stop listen test lint format deploy scale-down scale-up clean

help:
	@echo "make run         Start local dev stack"
	@echo "make stop        Stop local dev stack"
	@echo "make listen      Start voice session"
	@echo "make test        Run tests"
	@echo "make lint        Run ruff linter"
	@echo "make format      Format with black + ruff"
	@echo "make deploy      Deploy to EKS"
	@echo "make scale-down  Zero EKS nodes (save cost)"
	@echo "make scale-up    Restore EKS nodes"
	@echo "make clean       Remove cache files"

run:
	cp -n .env.example .env 2>/dev/null || true
	docker-compose up -d
	@echo "API:   http://localhost:8000"
	@echo "Docs:  http://localhost:8000/docs"
	@echo "Voice: ws://localhost:8080/voice/stream"

stop:
	docker-compose down

logs:
	docker-compose logs -f orchestrator

shell:
	docker-compose exec orchestrator /bin/bash

listen:
	python -c "\
import asyncio; \
from voice.voice_session import VoiceSession; \
from orchestrator.brain import JarvisBrain; \
brain = JarvisBrain(); \
brain.initialise(); \
session = VoiceSession(brain_handler=brain.process); \
asyncio.run(session.run())"

install:
	pip install -e ".[dev]"

test:
	pytest tests/ -v --cov=. --cov-report=term-missing

lint:
	ruff check .

format:
	black .
	ruff check . --fix

typecheck:
	mypy orchestrator/ agents/ voice/ --ignore-missing-imports

deploy:
	kubectl apply -f deploy/namespace.yaml
	kubectl apply -f deploy/external-secrets.yaml
	kubectl apply -f deploy/orchestrator-deployment.yaml
	kubectl apply -f deploy/orchestrator-service.yaml
	kubectl apply -f deploy/voice-server-deployment.yaml
	kubectl apply -f triggers/
	kubectl get pods -n jarvis

scale-down:
	eksctl scale nodegroup --cluster=jarvis-cluster --name=jarvis-nodes --nodes=0 --nodes-min=0 -r us-east-1
	@echo "Nodes scaled to 0 — costs stopped"

scale-up:
	eksctl scale nodegroup --cluster=jarvis-cluster --name=jarvis-nodes --nodes=2 --nodes-min=1 -r us-east-1
	@echo "Nodes scaled to 2 — ready"

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .mypy_cache .ruff_cache dist build *.egg-info
