"""
One-time migration: adds two nullable columns to `recommendations` so we
can capture the RAW LLM confidence and the grounding score separately,
not just the final blended confidence_pct. This enables offline ablation
studies (sweeping the blend ratio) without re-running the LLM each time.

Safe to run multiple times (IF NOT EXISTS guards).

Run from inside scs-backend with venv active:
    python3 migrate_add_calibration_columns.py
"""
from app.db import get_connection

conn = get_connection()
cur = conn.cursor()

cur.execute("""
    ALTER TABLE recommendations
    ADD COLUMN IF NOT EXISTS raw_llm_confidence_pct NUMERIC;
""")
cur.execute("""
    ALTER TABLE recommendations
    ADD COLUMN IF NOT EXISTS grounding_score NUMERIC;
""")

conn.commit()
cur.close()
conn.close()
print("Migration complete: raw_llm_confidence_pct and grounding_score columns added.")
