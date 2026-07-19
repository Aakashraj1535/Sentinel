"""
Loads the synthetic JSON data (suppliers, orders, knowledge documents, edges)
into PostgreSQL, computing embeddings locally with sentence-transformers
(no Ollama needed for this step — embeddings are a separate, lightweight model).

Prerequisites:
  1. PostgreSQL running locally with the pgvector extension installed.
  2. Database created (see README for the exact commands).
  3. schema.sql already applied to that database.
  4. ../data/generate_synthetic_data.py already run once.

Run:  python load_data.py
"""

import json
import os
import psycopg2
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DATABASE_URL", "postgresql://localhost:5432/scs_db")
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

print("Loading embedding model (all-MiniLM-L6-v2, first run downloads ~80MB)...")
model = SentenceTransformer("all-MiniLM-L6-v2")


def load_json(name):
    with open(os.path.join(DATA_DIR, name)) as f:
        return json.load(f)


def main():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    suppliers = load_json("suppliers.json")
    orders = load_json("orders.json")
    docs = load_json("knowledge_documents.json")
    edges = load_json("knowledge_edges.json")

    print(f"Inserting {len(suppliers)} suppliers...")
    for s in suppliers:
        cur.execute(
            """INSERT INTO suppliers (id, name, region, on_time_rate, total_incidents)
               VALUES (%s, %s, %s, %s, %s)
               ON CONFLICT (id) DO UPDATE SET
                 name=EXCLUDED.name, region=EXCLUDED.region,
                 on_time_rate=EXCLUDED.on_time_rate, total_incidents=EXCLUDED.total_incidents""",
            (s["id"], s["name"], s["region"], s["on_time_rate"], s["total_incidents"]),
        )

    print(f"Inserting {len(orders)} orders...")
    for o in orders:
        cur.execute(
            """INSERT INTO orders (id, supplier_id, item, quantity, warehouse_id,
                                    expected_delivery, actual_delivery, status)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (id) DO NOTHING""",
            (o["id"], o["supplier_id"], o["item"], o["quantity"], o["warehouse_id"],
             o["expected_delivery"], o["actual_delivery"], o["status"]),
        )

    print(f"Computing embeddings and inserting {len(docs)} knowledge document chunks...")
    texts = [d["chunk_text"] for d in docs]
    embeddings = model.encode(texts, show_progress_bar=True)

    for d, emb in zip(docs, embeddings):
        cur.execute(
            """INSERT INTO knowledge_documents
                 (doc_label, doc_kind, supplier_id, exception_type, chunk_text, embedding)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (d["doc_label"], d["doc_kind"], d["supplier_id"], d["exception_type"],
             d["chunk_text"], emb.tolist()),
        )

    print(f"Inserting {len(edges)} knowledge graph edges...")
    for e in edges:
        cur.execute(
            """INSERT INTO knowledge_edges (from_label, relation, to_label)
               VALUES (%s, %s, %s)""",
            (e["from_label"], e["relation"], e["to_label"]),
        )

    conn.commit()
    cur.close()
    conn.close()
    print("Done. All synthetic data loaded into PostgreSQL.")


if __name__ == "__main__":
    main()
