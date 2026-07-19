# Supply Chain Sentinel — Backend Setup (Phase 1)

This phase gets your database and synthetic data working. No Ollama needed yet.

## 1. Install pgvector extension for PostgreSQL

macOS (Homebrew):
```
brew install pgvector
```

## 2. Create the database

```
createdb scs_db
psql scs_db -f db/schema.sql
```

If `createdb`/`psql` aren't found, they come with PostgreSQL — make sure
Postgres's `bin` folder is on your PATH, or use the full path shown when
you installed Postgres.

## 3. Set up Python environment

```
cd scs-backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 4. Configure your database connection

Create a file named `.env` in this folder:
```
DATABASE_URL=postgresql://localhost:5433/scs_db
```
(Adjust username/password/port if your local Postgres setup needs them —
e.g. `postgresql://username:password@localhost:5432/scs_db`)

## 5. Generate synthetic data

```
cd data
python3 generate_synthetic_data.py
cd ..
```

This creates `suppliers.json`, `orders.json`, `knowledge_documents.json`,
and `knowledge_edges.json` inside the `data/` folder.

## 6. Load data into PostgreSQL (with embeddings)

```
cd db
python3 load_data.py
cd ..
```

First run downloads a small (~80MB) embedding model — this is normal and
only happens once.

## 7. Verify it worked

```
psql scs_db -c "SELECT count(*) FROM knowledge_documents;"
psql scs_db -c "SELECT count(*) FROM orders WHERE status = 'delayed';"
```

You should see 35 knowledge documents and roughly 20+ delayed orders.

---

**Once this works, come back to Claude and say so — Phase 2 builds the
actual agents (Monitoring, RAG retrieval, Resolution, Report) on top of
this data.**
