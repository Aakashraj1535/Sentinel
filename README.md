# Supply Chain Sentinel

<!--
  Once pushed to GitHub, replace OWNER/REPO below with your actual
  GitHub username/repository name to make this badge live, e.g.
  https://github.com/aakashraj/Sentinel/actions/workflows/tests.yml
-->
![Tests](https://github.com/OWNER/REPO/actions/workflows/tests.yml/badge.svg)

An autonomous, multi-agent, RAG-driven supply chain exception detection and resolution system. Built as a final-year Information Technology project at Easwari Engineering College.

## Overview

Supply Chain Sentinel monitors supply chain operations, detects exceptions and anomalies across suppliers, and uses a coordinated team of AI agents to investigate, explain, and recommend resolutions — with human-in-the-loop approval for critical decisions. The system runs fully locally, with no dependency on external cloud LLM APIs.

## Key Features

- **6 coordinated agents** (via LangGraph) handling detection, retrieval, reasoning, risk scoring, pattern analysis, and resolution recommendation
- **Retrieval-Augmented Generation (RAG)** over supply chain documents using pgvector for semantic search
- **Predictive risk scoring** to flag likely disruptions before they escalate
- **Cross-supplier pattern detection** to surface recurring issues across multiple vendors
- **Human-in-the-loop controls** so critical actions require explicit approval rather than full autonomy
- **Multi-language document chat** for querying supply chain documents in different languages
- **Fully local stack** — no external API calls, all inference runs on-device

## Tech Stack

| Layer | Technology |
|---|---|
| LLM | Ollama (llama3.2) |
| Agent orchestration | LangGraph |
| Backend | FastAPI |
| Database | PostgreSQL 17 + pgvector |
| Frontend | React + Tailwind CSS |
| Dev environment | Mac M3 (local) |

## Getting Started

### Prerequisites
- Node.js & npm
- Python 3.10+
- PostgreSQL 17 running locally on port `5433` with `pgvector` enabled
- Ollama installed with the `llama3.2` model pulled

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Copy the example env file and fill in your DATABASE_URL (and, if you
# want real escalation emails, your SMTP settings) — see .env.example
cp .env.example .env

uvicorn app.main:app --reload --port 8080
```

### Frontend Setup
Run from the **project root** (not `backend/`) — there's no separate `frontend/` folder, the React app lives at the repo root alongside `backend/`.
```bash
npm install
npm run dev
```

### Database
Make sure PostgreSQL is running on port `5433` with `pgvector` enabled, then run the provided migration/setup scripts in `backend/db/` before starting the backend. Your `.env`'s `DATABASE_URL` must point at the same host/port/database you set those up on.

### Running Tests
```bash
cd backend
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest tests/ -v
```
36 tests covering the deterministic logic (severity scoring, RBAC role enforcement, confidence blending, upload validation, risk tiers) — no database or Ollama required. These also run automatically on every push via GitHub Actions (see badge above).

## License

This project is developed for academic purposes as part of the final-year curriculum at Easwari Engineering College.
