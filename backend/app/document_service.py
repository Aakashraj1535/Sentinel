"""
Document Service — Knowledge Base module
------------------------------------------
Handles the lifecycle of uploaded documents:
  1. Save the raw file to disk
  2. Extract text (PDF/DOCX/TXT)
  3. Chunk it and generate embeddings
  4. Insert chunks into the SAME knowledge_documents table the agents
     already retrieve from — so uploaded documents are automatically
     available to the Resolution Agent with zero changes to that agent.
  5. Track status (Processing / Indexed / Failed) on the documents table

Also provides "Ask this Document" — a RAG query scoped to a single
document's chunks only, answered by the local LLM.
"""

import os
import uuid
import requests

from app.db import get_connection, get_dict_cursor
from app.embeddings import embed_text
from app.document_processing import extract_text, chunk_text

STORAGE_DIR = os.path.join(os.path.dirname(__file__), "..", "storage", "documents")
os.makedirs(STORAGE_DIR, exist_ok=True)

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2"

# Maps a Knowledge Base doc_type to the doc_kind used in knowledge_documents,
# so uploaded docs slot into the same categories the RAG agent already knows.
DOC_TYPE_TO_KIND = {
    "Contract": "Contract",
    "SOP": "SOP",
    "Purchase Order": "Policy",
    "Invoice": "Policy",
    "Policy": "Policy",
}


def save_uploaded_file(file_bytes: bytes, file_name: str) -> tuple:
    """Saves the raw uploaded file to disk. Returns (document_id, storage_path)."""
    doc_id = f"DOC-{uuid.uuid4().hex[:8]}"
    safe_name = f"{doc_id}_{file_name}"
    path = os.path.join(STORAGE_DIR, safe_name)
    with open(path, "wb") as f:
        f.write(file_bytes)
    return doc_id, path


def create_document_record(doc_id, file_name, doc_type, supplier_id,
                            uploaded_by, file_size, storage_path):
    conn = get_connection()
    cur = get_dict_cursor(conn)
    cur.execute("""
        INSERT INTO documents (id, file_name, doc_type, supplier_id, uploaded_by,
                                file_size_bytes, storage_path, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'Processing')
    """, (doc_id, file_name, doc_type, supplier_id, uploaded_by, file_size, storage_path))
    conn.commit()
    cur.close()
    conn.close()


def index_document(doc_id: str):
    """
    Extracts, chunks, embeds, and stores a document's content.
    Marks the document as Indexed on success or Failed on error —
    never leaves it stuck in 'Processing'.
    """
    conn = get_connection()
    cur = get_dict_cursor(conn)

    cur.execute("SELECT * FROM documents WHERE id = %s", (doc_id,))
    doc = cur.fetchone()
    if not doc:
        cur.close()
        conn.close()
        raise ValueError(f"Document {doc_id} not found")

    try:
        text = extract_text(doc["storage_path"], doc["file_name"])
        if not text.strip():
            raise ValueError("No extractable text found in document")

        chunks = chunk_text(text)
        doc_kind = DOC_TYPE_TO_KIND.get(doc["doc_type"], "Policy")

        for i, chunk in enumerate(chunks):
            embedding = embed_text(chunk)
            label = f"{doc['file_name']} (chunk {i+1})"
            cur.execute("""
                INSERT INTO knowledge_documents
                    (doc_label, doc_kind, supplier_id, exception_type,
                     chunk_text, embedding, document_id)
                VALUES (%s, %s, %s, NULL, %s, %s, %s)
            """, (label, doc_kind, doc["supplier_id"], chunk, embedding, doc_id))

        summary = _generate_summary(text[:3000])

        cur.execute("""
            UPDATE documents
            SET status = 'Indexed', chunk_count = %s, summary = %s,
                last_indexed_at = now(), error_message = NULL
            WHERE id = %s
        """, (len(chunks), summary, doc_id))
        conn.commit()

    except Exception as e:
        cur.execute("""
            UPDATE documents SET status = 'Failed', error_message = %s WHERE id = %s
        """, (str(e), doc_id))
        conn.commit()
        raise
    finally:
        cur.close()
        conn.close()


def _generate_summary(text_sample: str) -> str:
    prompt = (
        "Summarize this document in 2 sentences for a business document library. "
        "Be factual, no headers.\n\n" + text_sample
    )
    try:
        response = requests.post(OLLAMA_URL, json={
            "model": OLLAMA_MODEL, "prompt": prompt, "stream": False,
        }, timeout=60)
        response.raise_for_status()
        return response.json()["response"].strip()
    except Exception:
        return "Summary unavailable (LLM not reachable)."


def reindex_document(doc_id: str):
    """Deletes existing chunks for a document and re-runs indexing from scratch."""
    conn = get_connection()
    cur = get_dict_cursor(conn)
    cur.execute("DELETE FROM knowledge_documents WHERE document_id = %s", (doc_id,))
    cur.execute("UPDATE documents SET status = 'Processing', chunk_count = 0 WHERE id = %s", (doc_id,))
    conn.commit()
    cur.close()
    conn.close()
    index_document(doc_id)


def delete_document(doc_id: str):
    conn = get_connection()
    cur = get_dict_cursor(conn)
    cur.execute("SELECT storage_path FROM documents WHERE id = %s", (doc_id,))
    doc = cur.fetchone()
    if doc and os.path.exists(doc["storage_path"]):
        os.remove(doc["storage_path"])
    cur.execute("DELETE FROM knowledge_documents WHERE document_id = %s", (doc_id,))
    cur.execute("DELETE FROM documents WHERE id = %s", (doc_id,))
    conn.commit()
    cur.close()
    conn.close()


def ask_document(doc_id: str, question: str, language: str = "English") -> dict:
    """
    'Ask this Document' — RAG scoped to ONLY this document's chunks.
    Answers must come only from the uploaded document's content.

    `language` lets the answer be returned in a language other than
    English (e.g. "Tamil", "Hindi") — useful given the MSME target
    audience may include non-English-speaking staff. Answer QUALITY in
    non-English languages depends on the local model's own multilingual
    capability (llama3.2 has some, but it's not as strong as English) —
    this is an honest limitation worth stating, not a guarantee.
    """
    conn = get_connection()
    cur = get_dict_cursor(conn)

    cur.execute("SELECT file_name FROM documents WHERE id = %s", (doc_id,))
    doc = cur.fetchone()
    if not doc:
        cur.close()
        conn.close()
        raise ValueError(f"Document {doc_id} not found")

    query_embedding = embed_text(question)
    cur.execute("""
        SELECT chunk_text, (embedding <=> %s::vector) AS distance
        FROM knowledge_documents
        WHERE document_id = %s
        ORDER BY distance ASC
        LIMIT 4
    """, (query_embedding, doc_id))
    relevant_chunks = cur.fetchall()
    cur.close()
    conn.close()

    if not relevant_chunks:
        return {"answer": "This document hasn't been indexed yet, or has no content.",
                "sources_used": 0}

    context = "\n\n".join(r["chunk_text"] for r in relevant_chunks)
    language_instruction = (
        "" if language.lower() == "english"
        else f"\nIMPORTANT: Write your answer in {language}, not English."
    )
    prompt = f"""Answer the question using ONLY the document excerpts below. \
If the answer isn't in the excerpts, say so — do not guess or use outside knowledge.
{language_instruction}

DOCUMENT: {doc['file_name']}

EXCERPTS:
{context}

QUESTION: {question}

ANSWER:"""

    try:
        response = requests.post(OLLAMA_URL, json={
            "model": OLLAMA_MODEL, "prompt": prompt, "stream": False,
        }, timeout=60)
        response.raise_for_status()
        answer = response.json()["response"].strip()
    except Exception as e:
        answer = f"Could not reach local LLM ({e}). Is Ollama running?"

    return {"answer": answer, "sources_used": len(relevant_chunks)}
