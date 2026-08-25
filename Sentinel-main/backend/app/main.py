"""
FastAPI Backend
-----------------
Exposes the agent pipeline and database to the React dashboard.
Endpoint shapes match src/lib/mock-api.ts exactly, so the frontend
only needs to swap its mock functions for fetch() calls — no
component changes required.

Run:  uvicorn app.main:app --reload --port 8080
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import csv
import io
import os

from app.db import get_connection, get_dict_cursor
from app.serializers import (
    serialize_exception, list_exceptions,
    list_suppliers, serialize_supplier, dashboard_summary,
)
from app.graph import run_full_pipeline, process_all_active_exceptions
from app import document_service
from app import analytics as analytics_module
from app.agents import predictive_risk_agent
from app.agents import pattern_detection_agent
from app.agents import sla_monitor
from app.agents import report_scheduler
from app.auth import require_role

app = FastAPI(title="Supply Chain Sentinel API")

# Allow the local Vite/TanStack dev server to call this API.
# Loosened for local development — tighten before any real deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# AUTOMATIC BACKGROUND PROCESSING
# ------------------------------------------------------------
# Instead of relying on someone manually calling /api/run-pipeline or
# /api/process-active-exceptions, this scheduler quietly runs in the
# background and does it automatically:
#   1. detect_exceptions() picks up any newly delayed/pending orders
#   2. any exception still sitting at 'Active' (not yet resolved) gets
#      pushed through retrieve -> resolve -> report automatically
#
# SCHEDULER_INTERVAL_MINUTES and SCHEDULER_BATCH_LIMIT are kept small on
# purpose -- this is tuned for a memory-constrained local dev machine
# (8GB RAM). In a real deployment this job would instead be triggered
# event-driven (immediately after a new order/exception is detected)
# and run on proper worker infrastructure (e.g. Celery + Redis), rather
# than polling on a timer.
SCHEDULER_INTERVAL_MINUTES = 3
SCHEDULER_BATCH_LIMIT = 5

scheduler = BackgroundScheduler()


def _auto_process_job():
    try:
        # SLA checking runs FIRST and is deliberately independent of
        # everything below it -- it's pure DB queries + a webhook/SMTP
        # call, no LLM involved. If it ran last (as it originally did),
        # a slow or unresponsive Ollama call in the steps below could
        # delay time-critical breach notifications by the same amount,
        # which defeats the point of having an SLA monitor at all.
        sla_monitor.check_sla_breaches()
    except Exception as e:
        print(f"[scheduler] check_sla_breaches error: {e}")
    try:
        # Pick up any brand-new exceptions from operational data.
        run_full_pipeline()
    except Exception as e:
        print(f"[scheduler] run_full_pipeline error: {e}")
    try:
        # Then chip away at anything still stuck at 'Active'.
        process_all_active_exceptions(limit=SCHEDULER_BATCH_LIMIT)
    except Exception as e:
        print(f"[scheduler] process_all_active_exceptions error: {e}")


@app.on_event("startup")
def start_scheduler():
    scheduler.add_job(
        _auto_process_job,
        "interval",
        minutes=SCHEDULER_INTERVAL_MINUTES,
        id="auto_process_exceptions",
        replace_existing=True,
    )
    scheduler.start()
    print(f"[scheduler] Auto-processing started: every {SCHEDULER_INTERVAL_MINUTES} min, "
          f"batch size {SCHEDULER_BATCH_LIMIT}.")

    # Executive digest: weekly by default (Monday 8am), configurable via
    # SCS_REPORT_CRON as a standard 5-field crontab string, e.g.
    # "0 8 * * MON" or "0 8 * * *" for daily. Kept as a separate job from
    # _auto_process_job since it runs far less often and has nothing to
    # do with exception processing.
    report_cron = os.environ.get("SCS_REPORT_CRON", "0 8 * * MON")
    try:
        scheduler.add_job(
            report_scheduler.generate_and_send_report,
            CronTrigger.from_crontab(report_cron),
            id="executive_report",
            replace_existing=True,
        )
        print(f"[scheduler] Executive digest scheduled: '{report_cron}' (cron syntax).")
    except Exception as e:
        print(f"[scheduler] Failed to schedule executive digest (check SCS_REPORT_CRON "
              f"format): {e}")


@app.on_event("shutdown")
def stop_scheduler():
    scheduler.shutdown(wait=False)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/exceptions")
def get_exceptions():
    conn = get_connection()
    cur = get_dict_cursor(conn)
    result = list_exceptions(cur)
    cur.close()
    conn.close()
    return result


@app.get("/api/exceptions/resolved")
def get_resolved_exceptions():
    conn = get_connection()
    cur = get_dict_cursor(conn)
    result = list_exceptions(cur, status="Resolved")
    cur.close()
    conn.close()
    return result


@app.get("/api/audit-log/export")
def export_audit_log():
    """
    Supports the 'auditability' requirement of a real deployment: every
    AI decision (detection, retrieval, recommendation, escalation,
    notification) is already logged in `audit_log`. This just exposes
    that data as a downloadable CSV -- e.g. for compliance review, or to
    hand to a company's audit/risk team.
    """
    conn = get_connection()
    cur = get_dict_cursor(conn)
    cur.execute("""
        SELECT exception_id, step, summary, timestamp
        FROM audit_log
        ORDER BY timestamp ASC
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Exception ID", "Step", "Summary", "Timestamp"])
    for r in rows:
        writer.writerow([
            r["exception_id"], r["step"], r["summary"],
            r["timestamp"].isoformat() if r["timestamp"] else "",
        ])
    buffer.seek(0)

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_log_export.csv"},
    )


@app.get("/api/exceptions/{exception_id}")
def get_exception(exception_id: str):
    conn = get_connection()
    cur = get_dict_cursor(conn)
    result = serialize_exception(cur, exception_id)
    cur.close()
    conn.close()
    if result is None:
        raise HTTPException(status_code=404, detail="Exception not found")
    return result


@app.get("/api/suppliers")
def get_suppliers():
    conn = get_connection()
    cur = get_dict_cursor(conn)
    result = list_suppliers(cur)
    cur.close()
    conn.close()
    return result


@app.post("/api/suppliers")
def create_supplier(
    name: str = Form(...),
    region: str = Form(...),
    on_time_rate: float = Form(100.0),
    _role: str = Depends(require_role("Admin")),
):
    """
    Adds a new supplier from the dashboard. New suppliers start with
    zero incident history — their risk level and predictive forecast
    will populate naturally as exceptions occur for them over time.
    """
    import uuid
    supplier_id = f"SUP-{uuid.uuid4().hex[:6].upper()}"

    conn = get_connection()
    cur = get_dict_cursor(conn)
    cur.execute("""
        INSERT INTO suppliers (id, name, region, on_time_rate, total_incidents)
        VALUES (%s, %s, %s, %s, 0)
    """, (supplier_id, name, region, on_time_rate))
    conn.commit()

    result = serialize_supplier(cur, supplier_id)
    cur.close()
    conn.close()
    return result


# ============================================================
# HUMAN-IN-THE-LOOP: notes and decisions on exceptions
# ============================================================

@app.post("/api/exceptions/{exception_id}/note")
def add_exception_note(
    exception_id: str,
    note: str = Form(...),
    author: str = Form("Demo User"),
    _role: str = Depends(require_role("Procurement Manager")),
):
    """Adds a manual human note to an exception's audit trail."""
    conn = get_connection()
    cur = get_dict_cursor(conn)
    cur.execute("SELECT id FROM exceptions WHERE id = %s", (exception_id,))
    if not cur.fetchone():
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Exception not found")

    cur.execute("""
        INSERT INTO audit_log (exception_id, step, summary)
        VALUES (%s, 'Note', %s)
    """, (exception_id, f"{author}: {note}"))
    conn.commit()
    cur.close()
    conn.close()
    return {"added": True}


@app.post("/api/exceptions/{exception_id}/decision")
def record_human_decision(
    exception_id: str,
    decision: str = Form(...),   # "Approved" | "Rejected"
    note: str = Form(""),
    decided_by: str = Form("Demo User"),
    _role: str = Depends(require_role("Procurement Manager")),
):
    """
    Records a human's final decision on an escalated (or any) exception —
    completes the human-in-the-loop story: detect -> recommend -> escalate
    -> HUMAN DECIDES -> logged. Approving marks the exception Resolved;
    rejecting keeps it open for further action but records why.
    """
    if decision not in ("Approved", "Rejected"):
        raise HTTPException(status_code=400, detail="decision must be 'Approved' or 'Rejected'")

    conn = get_connection()
    cur = get_dict_cursor(conn)
    cur.execute("SELECT id, status FROM exceptions WHERE id = %s", (exception_id,))
    exc = cur.fetchone()
    if not exc:
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Exception not found")

    new_status = "Resolved" if decision == "Approved" else exc["status"]

    cur.execute("""
        UPDATE exceptions
        SET human_decision = %s, human_decision_note = %s,
            human_decided_at = now(), human_decided_by = %s, status = %s
        WHERE id = %s
    """, (decision, note, decided_by, new_status, exception_id))

    cur.execute("""
        INSERT INTO audit_log (exception_id, step, summary)
        VALUES (%s, 'Decided', %s)
    """, (exception_id, f"Human decision by {decided_by}: {decision}"
          + (f" — {note}" if note else "")))

    conn.commit()
    result = serialize_exception(cur, exception_id)
    cur.close()
    conn.close()
    return result


# ============================================================
# SYSTEM HEALTH
# ============================================================

@app.get("/api/system-health")
def system_health():
    """
    Quick status check for a dashboard health strip: is the local LLM
    reachable, is the database reachable, and when did the pipeline
    last run.
    """
    import requests as req_lib

    ollama_ok = False
    try:
        r = req_lib.get("http://localhost:11434/api/tags", timeout=2)
        ollama_ok = r.status_code == 200
    except Exception:
        ollama_ok = False

    db_ok = True
    last_run = None
    try:
        conn = get_connection()
        cur = get_dict_cursor(conn)
        cur.execute("SELECT max(detected_at) as last FROM exceptions")
        row = cur.fetchone()
        last_run = row["last"].isoformat() if row and row["last"] else None
        cur.close()
        conn.close()
    except Exception:
        db_ok = False

    return {
        "ollamaReachable": ollama_ok,
        "databaseReachable": db_ok,
        "lastExceptionDetectedAt": last_run,
    }


@app.get("/api/dashboard-summary")
def get_dashboard_summary():
    conn = get_connection()
    cur = get_dict_cursor(conn)
    result = dashboard_summary(cur)
    cur.close()
    conn.close()
    return result


@app.post("/api/run-pipeline")
def trigger_pipeline(_role: str = Depends(require_role("Procurement Manager"))):
    """
    Runs the full detect -> retrieve -> resolve -> report pipeline.
    Useful for a "Check for new exceptions" button on the dashboard,
    or to call after inserting fresh synthetic/test data.
    """
    results = run_full_pipeline()
    return {
        "processed": len(results),
        "exception_ids": [r["report"]["exception_id"] for r in results],
    }


@app.post("/api/reports/send-now")
def trigger_executive_report(_role: str = Depends(require_role("Admin"))):
    """
    Manually sends the executive digest immediately, on whatever channels
    are configured (email via SCS_REPORT_RECIPIENT/SCS_NOTIFY_TO, Slack
    via SCS_SLACK_WEBHOOK_URL). Exists so nobody has to wait for the
    weekly schedule to see what the report looks like -- Admin-gated
    since it's an outbound communication action, same tier as document
    management.
    """
    return report_scheduler.generate_and_send_report()


@app.post("/api/process-active-exceptions")
def trigger_process_active(
    background_tasks: BackgroundTasks,
    limit: int = None,
    _role: str = Depends(require_role("Procurement Manager")),
):
    """
    Catches up exceptions still stuck at 'Active' status. Runs as a
    background task. Optionally pass ?limit=5 to process only a small
    batch at a time — safer on memory-constrained machines. Call this
    endpoint repeatedly to work through a large backlog gradually.
    """
    from app.graph import process_all_active_exceptions
    from app.db import get_connection, get_dict_cursor

    conn = get_connection()
    cur = get_dict_cursor(conn)
    cur.execute("SELECT count(*) as c FROM exceptions WHERE status = 'Active'")
    pending_count = cur.fetchone()["c"]
    cur.close()
    conn.close()

    batch_size = min(limit, pending_count) if limit else pending_count
    background_tasks.add_task(process_all_active_exceptions, limit)
    return {
        "status": "processing_started",
        "pending_count": pending_count,
        "processing_this_batch": batch_size,
        "note": "Running in the background. Check /api/exceptions or the dashboard "
                "after a while to see results.",
    }


# ============================================================
# KNOWLEDGE BASE — document management endpoints
# ============================================================

def _serialize_document(row: dict) -> dict:
    return {
        "id": row["id"],
        "fileName": row["file_name"],
        "docType": row["doc_type"],
        "supplierId": row["supplier_id"],
        "uploadedBy": row["uploaded_by"],
        "uploadedAt": row["uploaded_at"].isoformat() if row["uploaded_at"] else None,
        "fileSizeBytes": row["file_size_bytes"],
        "status": row["status"],
        "chunkCount": row["chunk_count"],
        "summary": row["summary"],
        "lastIndexedAt": row["last_indexed_at"].isoformat() if row["last_indexed_at"] else None,
        "errorMessage": row["error_message"],
    }


@app.get("/api/documents")
def list_documents(doc_type: str = None):
    conn = get_connection()
    cur = get_dict_cursor(conn)
    if doc_type:
        cur.execute("SELECT * FROM documents WHERE doc_type = %s ORDER BY uploaded_at DESC", (doc_type,))
    else:
        cur.execute("SELECT * FROM documents ORDER BY uploaded_at DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [_serialize_document(r) for r in rows]


@app.get("/api/documents/summary")
def documents_summary():
    from datetime import datetime, timedelta, timezone
    conn = get_connection()
    cur = get_dict_cursor(conn)
    cur.execute("SELECT doc_type, status, uploaded_at FROM documents")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    recently_uploaded = sum(
        1 for r in rows
        if r["uploaded_at"] and r["uploaded_at"] >= week_ago
    )

    return {
        "totalDocuments": len(rows),
        "contracts": sum(1 for r in rows if r["doc_type"] == "Contract"),
        "sops": sum(1 for r in rows if r["doc_type"] == "SOP"),
        "indexedDocuments": sum(1 for r in rows if r["status"] == "Indexed"),
        "recentlyUploaded": recently_uploaded,
    }


@app.post("/api/documents/upload")
def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    doc_type: str = Form(...),
    supplier_id: str = Form(None),
    uploaded_by: str = Form("Demo User"),
    _role: str = Depends(require_role("Admin")),
):
    file_bytes = file.file.read()
    try:
        doc_id, storage_path, safe_file_name = document_service.save_uploaded_file(
            file_bytes, file.filename
        )
    except document_service.UploadValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    document_service.create_document_record(
        doc_id, safe_file_name, doc_type, supplier_id or None,
        uploaded_by, len(file_bytes), storage_path,
    )
    # Index in the background so the upload request returns immediately
    # with status "Processing" — the frontend can poll for "Indexed".
    background_tasks.add_task(document_service.index_document, doc_id)

    conn = get_connection()
    cur = get_dict_cursor(conn)
    cur.execute("SELECT * FROM documents WHERE id = %s", (doc_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return _serialize_document(row)


@app.get("/api/documents/{document_id}")
def get_document(document_id: str):
    conn = get_connection()
    cur = get_dict_cursor(conn)
    cur.execute("SELECT * FROM documents WHERE id = %s", (document_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Document not found")
    return _serialize_document(row)


@app.delete("/api/documents/{document_id}")
def delete_document(document_id: str, _role: str = Depends(require_role("Admin"))):
    conn = get_connection()
    cur = get_dict_cursor(conn)
    cur.execute("SELECT id FROM documents WHERE id = %s", (document_id,))
    if not cur.fetchone():
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Document not found")
    cur.close()
    conn.close()
    document_service.delete_document(document_id)
    return {"deleted": document_id}


@app.post("/api/documents/{document_id}/reindex")
def reindex_document(
    document_id: str,
    background_tasks: BackgroundTasks,
    _role: str = Depends(require_role("Admin")),
):
    conn = get_connection()
    cur = get_dict_cursor(conn)
    cur.execute("SELECT id FROM documents WHERE id = %s", (document_id,))
    if not cur.fetchone():
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Document not found")
    cur.close()
    conn.close()
    background_tasks.add_task(document_service.reindex_document, document_id)
    return {"status": "reindexing", "document_id": document_id}


@app.post("/api/documents/{document_id}/chat")
def chat_with_document(document_id: str, question: str = Form(...), language: str = Form("English")):
    try:
        result = document_service.ask_document(document_id, question, language=language)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return result


# ============================================================
# ANALYTICS & NOTIFICATIONS
# ============================================================

@app.get("/api/analytics/summary")
def get_analytics_summary():
    conn = get_connection()
    cur = get_dict_cursor(conn)
    result = analytics_module.analytics_summary(cur)
    cur.close()
    conn.close()
    return result


@app.get("/api/notifications")
def get_notifications(limit: int = 20):
    conn = get_connection()
    cur = get_dict_cursor(conn)
    result = analytics_module.notifications_feed(cur, limit=limit)
    cur.close()
    conn.close()
    return result


# ============================================================
# PREDICTIVE RISK AGENT
# ============================================================

@app.get("/api/predictive-risk")
def get_predictive_risk():
    """Fast read of the last computed forecast (does not recompute)."""
    return predictive_risk_agent.get_cached_risk_forecast()


@app.post("/api/predictive-risk/refresh")
def refresh_predictive_risk():
    """
    Recomputes trend + predicted risk for every supplier. Calls the local
    LLM once per supplier for a narrative explanation, so this can take
    a short while (a few seconds per supplier) — call from a button with
    a loading state, similar to /api/run-pipeline.
    """
    results = predictive_risk_agent.run_predictive_risk_analysis()
    return {"suppliers_analyzed": len(results), "results": results}


# ============================================================
# AGENT ACTIVITY LOG
# ============================================================

@app.get("/api/activity-log")
def get_activity_log(limit: int = 50):
    """
    Recent agent activity across all exceptions, most recent first.
    Pulled directly from the same audit_log table each agent already
    writes to — this is a read-only view proving the agents are
    genuinely running, not a separate logging system.
    """
    conn = get_connection()
    cur = get_dict_cursor(conn)
    cur.execute("""
        SELECT a.step, a.timestamp, a.summary, a.exception_id,
               e.exception_type, e.severity, s.name as supplier_name
        FROM audit_log a
        JOIN exceptions e ON e.id = a.exception_id
        JOIN suppliers s ON s.id = e.supplier_id
        ORDER BY a.timestamp DESC
        LIMIT %s
    """, (limit,))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [{
        "step": r["step"],
        "timestamp": r["timestamp"].isoformat() if r["timestamp"] else None,
        "summary": r["summary"],
        "exceptionId": r["exception_id"],
        "exceptionType": r["exception_type"],
        "severity": r["severity"],
        "supplierName": r["supplier_name"],
    } for r in rows]


# ============================================================
# CROSS-SUPPLIER PATTERN DETECTION
# ============================================================

@app.get("/api/systemic-patterns")
def get_systemic_patterns():
    """
    Detects potential systemic issues affecting multiple DISTINCT
    suppliers within the same recent window — different from the
    Predictive Risk Agent, which looks at one supplier's trend over
    time. This looks across all suppliers at once. Computed live
    (cheap query + LLM narrative per pattern found, not cached).
    """
    return pattern_detection_agent.detect_systemic_patterns()


# ============================================================
# CALIBRATION / ACCURACY METRIC
# ============================================================

@app.get("/api/analytics/calibration")
def get_calibration_metrics():
    """
    Tracks agreement between human Approve/Reject decisions and the
    AI's own confidence — a real, growing accuracy signal built from
    actual usage, not a one-time offline benchmark.
    """
    conn = get_connection()
    cur = get_dict_cursor(conn)
    result = analytics_module.calibration_metrics(cur)
    cur.close()
    conn.close()
    return result


@app.get("/api/analytics/root-causes")
def get_root_cause_breakdown():
    """
    Structured root-cause counts (overall + weekly trend) for the Root
    Cause Analysis panel. Open to any signed-in role (Viewer included) —
    same tier as the other analytics endpoints, which are read-only by
    nature.
    """
    conn = get_connection()
    cur = get_dict_cursor(conn)
    result = analytics_module.root_cause_breakdown(cur)
    cur.close()
    conn.close()
    return result


@app.get("/api/analytics/financial-impact")
def get_financial_impact_summary():
    """
    Aggregated dollar exposure for the Financial Impact panel: total
    currently at risk, breakdown by severity, top suppliers by
    exposure, and a weekly trend. Open to any signed-in role, same
    tier as the other analytics endpoints (read-only by nature).
    """
    conn = get_connection()
    cur = get_dict_cursor(conn)
    result = analytics_module.financial_impact_summary(cur)
    cur.close()
    conn.close()
    return result


@app.post("/api/exceptions/{exception_id}/estimate-financial-impact")
def trigger_financial_impact_estimate(
    exception_id: str,
    _role: str = Depends(require_role("Procurement Manager")),
):
    """
    Manually (re)computes the financial impact estimate for one
    exception -- useful right after backfilling unit_cost on an order
    that previously had none, or after an SLA breach changes the
    estimate, without waiting for the exception to flow through the
    full pipeline again.
    """
    from app.agents.financial_impact_agent import estimate_financial_impact

    conn = get_connection()
    cur = get_dict_cursor(conn)
    cur.execute("SELECT id FROM exceptions WHERE id = %s", (exception_id,))
    if not cur.fetchone():
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Exception not found")
    cur.close()
    conn.close()

    result = estimate_financial_impact(exception_id)
    return result


@app.get("/api/suppliers/{supplier_id}/trend")
def get_supplier_trend(supplier_id: str):
    """
    Real historical on-time-rate trend for one supplier, computed from
    actual order delivery data -- see analytics.supplier_weekly_trend
    for why this exists instead of relying on the static
    suppliers.on_time_rate column.
    """
    conn = get_connection()
    cur = get_dict_cursor(conn)
    cur.execute("SELECT id FROM suppliers WHERE id = %s", (supplier_id,))
    if not cur.fetchone():
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Supplier not found")
    result = analytics_module.supplier_weekly_trend(cur, supplier_id)
    cur.close()
    conn.close()
    return result


@app.post("/api/exceptions/{exception_id}/root-cause-category")
def set_root_cause_category(
    exception_id: str,
    category: str = Form(...),
    _role: str = Depends(require_role("Procurement Manager")),
):
    """
    Lets a human correct or fill in the auto-classified root cause
    category — the actual "tagging" half of this feature, since keyword
    matching (see app/root_cause.py) deliberately won't catch everything
    and shouldn't be treated as the final word.
    """
    from app.root_cause import ROOT_CAUSE_CATEGORIES

    if category not in ROOT_CAUSE_CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail=f"category must be one of {ROOT_CAUSE_CATEGORIES}",
        )

    conn = get_connection()
    cur = get_dict_cursor(conn)
    cur.execute("SELECT id FROM exceptions WHERE id = %s", (exception_id,))
    if not cur.fetchone():
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="Exception not found")

    cur.execute("""
        UPDATE exceptions
        SET root_cause_category = %s, root_cause_category_source = 'human'
        WHERE id = %s
    """, (category, exception_id))
    cur.execute("""
        INSERT INTO audit_log (exception_id, step, summary)
        VALUES (%s, 'Root Cause Tagged', %s)
    """, (exception_id, f"Root cause category set to '{category}' by a human reviewer."))
    conn.commit()
    cur.close()
    conn.close()
    return {"exceptionId": exception_id, "rootCauseCategory": category}
