# Supply Chain Sentinel

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
- PostgreSQL 17 running locally (default port used in this project: `5433`)
- Ollama installed with the `llama3.2` model pulled

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### Database
Make sure PostgreSQL is running on port `5433` with pgvector enabled, then run the provided migration/setup scripts before starting the backend.

## License

This project is developed for academic purposes as part of the final-year curriculum at Easwari Engineering College.
