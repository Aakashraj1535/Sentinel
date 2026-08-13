"""
LangGraph Pipeline
-------------------
Chains the 4 agents into one automatic flow:

    detect (batch, finds ALL new exceptions)
        -> for each new exception:
             retrieve -> resolve -> report   (LangGraph-orchestrated)

Detection is a batch step (it can find several new exceptions at once from
the operational data), so it runs once up front in plain Python. Each
individual exception then flows through the 3-step LangGraph graph:
retrieve context -> resolve with the LLM -> generate report.

Run standalone:  python -m app.graph
"""

from typing import TypedDict, Optional, List
from langgraph.graph import StateGraph, END

from app.agents.monitoring_agent import detect_exceptions
from app.agents.rag_agent import retrieve_context
from app.agents.resolution_agent import resolve_exception
from app.agents.report_agent import generate_report


class PipelineState(TypedDict):
    exception_id: str
    context_docs: Optional[List[dict]]
    resolution: Optional[dict]
    report: Optional[dict]


def node_retrieve(state: PipelineState) -> dict:
    docs = retrieve_context(state["exception_id"], top_k=5)
    return {"context_docs": docs}


def node_resolve(state: PipelineState) -> dict:
    result = resolve_exception(state["exception_id"], context_docs=state["context_docs"])
    return {"resolution": result}


def node_report(state: PipelineState) -> dict:
    report = generate_report(state["exception_id"])
    return {"report": report}


def build_graph():
    graph = StateGraph(PipelineState)
    graph.add_node("retrieve", node_retrieve)
    graph.add_node("resolve", node_resolve)
    graph.add_node("generate_report", node_report)
    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "resolve")
    graph.add_edge("resolve", "generate_report")
    graph.add_edge("generate_report", END)
    return graph.compile()


_compiled_graph = build_graph()


def run_pipeline_for_exception(exception_id: str) -> dict:
    """Runs the retrieve -> resolve -> report graph for one exception."""
    return _compiled_graph.invoke({"exception_id": exception_id})


def run_full_pipeline() -> list:
    """
    Full end-to-end run: detect all new exceptions from operational data,
    then push each one through the LangGraph pipeline.
    Returns a list of {exception_id, resolution, report} dicts.

    Each newly-detected exception is processed independently — if one fails
    (e.g. Ollama times out or returns malformed JSON on that one exception),
    it's logged and skipped rather than aborting the rest of the batch. The
    skipped exception stays at 'Active' and gets picked up by the next
    process_all_active_exceptions catch-up pass, so nothing is lost.
    """
    new_exceptions = detect_exceptions()
    results = []
    for exc in new_exceptions:
        try:
            result = run_pipeline_for_exception(exc["id"])
            results.append(result)
        except Exception as e:
            print(f"[run_full_pipeline] Skipped {exc['id']} due to error: {e}")
            continue
    return results


def process_all_active_exceptions(limit: int = None) -> list:
    """
    Catches up any exceptions still sitting at 'Active' status (detected
    by the Monitoring Agent but never pushed through retrieve -> resolve
    -> report) — pushes them through the pipeline.

    `limit` processes only that many at once — useful on memory-constrained
    machines to avoid processing a large batch in one go. Call this
    repeatedly (e.g. with limit=5) until no Active exceptions remain.

    Each exception is processed independently — if one fails, it's
    skipped and logged, and the rest continue rather than the whole
    batch failing.
    """
    from app.db import get_connection, get_dict_cursor
    conn = get_connection()
    cur = get_dict_cursor(conn)
    query = "SELECT id FROM exceptions WHERE status = 'Active'"
    if limit:
        query += f" LIMIT {int(limit)}"
    cur.execute(query)
    active_ids = [row["id"] for row in cur.fetchall()]
    cur.close()
    conn.close()

    results = []
    for exception_id in active_ids:
        try:
            result = run_pipeline_for_exception(exception_id)
            results.append(result)
        except Exception as e:
            print(f"[process_all_active_exceptions] Skipped {exception_id} due to error: {e}")
            continue
    return results


if __name__ == "__main__":
    print("Running full pipeline: detect -> retrieve -> resolve -> report...\n")
    results = run_full_pipeline()

    if not results:
        print("No new exceptions detected. (All operational data already processed.)")
    else:
        print(f"Processed {len(results)} new exception(s):\n")
        for r in results:
            report = r["report"]
            print(f"  {report['exception_id']} | {report['exception_type']} | "
                  f"{report['severity']} | Status: {report['status']}")
