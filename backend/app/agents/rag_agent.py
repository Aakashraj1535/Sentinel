"""
RAG Knowledge Agent
--------------------
For a given exception, retrieves the most relevant SOPs, contracts, and past
incidents — NOT via plain similarity search alone. Retrieval is routed by the
knowledge graph first (same supplier, same exception type), then ranked by
vector similarity within that relevant subset. This is the key differentiator
from plain RAG: structurally-relevant documents are prioritized over ones
that just sound similar.

Run standalone for testing:  python -m app.agents.rag_agent
"""

from app.db import get_connection, get_dict_cursor
from app.embeddings import embed_text


def build_query_text(exception_type: str, supplier_id: str, item: str = None) -> str:
    """Constructs a natural-language query to embed for retrieval."""
    parts = [exception_type, "involving supplier", supplier_id]
    if item:
        parts.append(f"for item {item}")
    return " ".join(parts)


def retrieve_context(exception_id: str, top_k: int = 5):
    """
    Retrieves relevant knowledge documents for a given exception.
    Returns a list of dicts: {doc_label, doc_kind, chunk_text, relevance}
    'relevance' is 'graph-linked' (structurally relevant via knowledge graph)
    or 'similarity' (matched by vector search only).
    """
    conn = get_connection()
    cur = get_dict_cursor(conn)

    cur.execute("""
        SELECT e.id, e.exception_type, e.supplier_id, o.item
        FROM exceptions e
        LEFT JOIN orders o ON o.id = e.order_id
        WHERE e.id = %s
    """, (exception_id,))
    exc = cur.fetchone()
    if not exc:
        cur.close()
        conn.close()
        raise ValueError(f"Exception {exception_id} not found")

    query_text = build_query_text(exc["exception_type"], exc["supplier_id"], exc["item"])
    query_embedding = embed_text(query_text)

    # --- Step 1: Graph-guided candidates ---
    # Documents structurally linked to this supplier or this exception type
    # via knowledge_edges, OR directly tagged with matching supplier_id/exception_type.
    # relevance_rank: 0 = directly tied to THIS supplier (strongest signal),
    # 1 = only tied to the exception type generally (e.g. a generic SOP or
    # another supplier's incident of the same type). Supplier-specific
    # matches are ranked first, then by vector distance within each tier.
    cur.execute("""
        SELECT DISTINCT kd.id, kd.doc_label, kd.doc_kind, kd.chunk_text,
               (kd.embedding <=> %s::vector) AS distance,
               CASE WHEN kd.supplier_id = %s
                      OR kd.doc_label IN (
                          SELECT from_label FROM knowledge_edges WHERE to_label = %s
                      )
                    THEN 0 ELSE 1 END AS relevance_rank
        FROM knowledge_documents kd
        WHERE kd.supplier_id = %s
           OR kd.exception_type = %s
           OR kd.doc_label IN (
               SELECT from_label FROM knowledge_edges
               WHERE to_label = %s OR to_label = %s
           )
        ORDER BY relevance_rank ASC, distance ASC
        LIMIT %s
    """, (query_embedding, exc["supplier_id"], exc["supplier_id"],
          exc["supplier_id"], exc["exception_type"],
          exc["supplier_id"], exc["exception_type"], top_k))
    graph_results = cur.fetchall()

    retrieved = [{
        "doc_label": r["doc_label"],
        "doc_kind": r["doc_kind"],
        "chunk_text": r["chunk_text"],
        "relevance": "supplier-linked" if r["relevance_rank"] == 0 else "type-linked",
        "distance": round(float(r["distance"]), 4),
    } for r in graph_results]

    # --- Step 2: Fallback pure similarity search if graph-guided results are thin ---
    if len(retrieved) < top_k:
        remaining = top_k - len(retrieved)
        already_have = [r["doc_label"] for r in retrieved]
        cur.execute("""
            SELECT doc_label, doc_kind, chunk_text,
                   (embedding <=> %s::vector) AS distance
            FROM knowledge_documents
            WHERE doc_label != ALL(%s)
            ORDER BY distance ASC
            LIMIT %s
        """, (query_embedding, already_have, remaining))
        fallback_results = cur.fetchall()
        retrieved.extend([{
            "doc_label": r["doc_label"],
            "doc_kind": r["doc_kind"],
            "chunk_text": r["chunk_text"],
            "relevance": "similarity",
            "distance": round(float(r["distance"]), 4),
        } for r in fallback_results])

    # Log to audit trail
    labels = ", ".join(r["doc_label"] for r in retrieved) if retrieved else "none"
    cur.execute("""
        INSERT INTO audit_log (exception_id, step, summary)
        VALUES (%s, 'Retrieved', %s)
    """, (exception_id, f"Retrieved {len(retrieved)} relevant document(s): {labels}"))

    # Persist structured knowledge records (for the frontend's knowledge panel)
    cur.execute("DELETE FROM exception_knowledge WHERE exception_id = %s", (exception_id,))
    for r in retrieved:
        cur.execute("""
            INSERT INTO exception_knowledge (exception_id, doc_label, doc_kind, excerpt, relevance)
            VALUES (%s, %s, %s, %s, %s)
        """, (exception_id, r["doc_label"], r["doc_kind"], r["chunk_text"], r["relevance"]))

    conn.commit()
    cur.close()
    conn.close()
    return retrieved


if __name__ == "__main__":
    conn = get_connection()
    cur = get_dict_cursor(conn)
    cur.execute("SELECT id FROM exceptions ORDER BY id LIMIT 1")
    sample = cur.fetchone()
    cur.close()
    conn.close()

    if not sample:
        print("No exceptions found — run the monitoring agent first.")
    else:
        exc_id = sample["id"]
        print(f"Retrieving context for {exc_id}...\n")
        results = retrieve_context(exc_id)
        for r in results:
            print(f"[{r['relevance']}] {r['doc_label']} ({r['doc_kind']}) "
                  f"- distance: {r['distance']}")
            print(f"  {r['chunk_text'][:120]}...")
            print()
