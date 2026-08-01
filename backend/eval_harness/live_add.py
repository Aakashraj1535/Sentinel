cat > /Users/aakashraj/Downloads/scs-backend/eval_harness/live_add.py << 'EOF'
"""
Live Demo Add-On
=================
Run this DURING your actual demo, in front of the panel, to show a brand
new problem being detected and resolved in real time.

Does NOT wipe any existing demo data -- just adds ONE new order and
processes it, on top of whatever demo_seed.py already set up.

USAGE:
    python eval_harness/live_add.py
"""

import sys
import time
import random
import requests
from pathlib import Path
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.db import get_connection, get_dict_cursor  # noqa: E402

API_BASE = "http://localhost:8000"

SUPPLIER_POOL = ["SUP-001", "SUP-002", "SUP-004", "SUP-006"]


def main():
    random.seed()
    conn = get_connection()
    cur = get_dict_cursor(conn)

    order_id = f"LIVE-{random.randint(1000, 9999)}"
    supplier_id = random.choice(SUPPLIER_POOL)
    now = datetime.now(timezone.utc)
    expected_delivery = now - timedelta(days=1)
    actual_delivery = now  # 1 day late, happening "right now"

    print(f"Creating new order {order_id} (supplier {supplier_id}, 1 day delayed)...")
    cur.execute("""
        INSERT INTO orders (id, supplier_id, item, quantity, warehouse_id,
                             expected_delivery, actual_delivery, status)
        VALUES (%s, %s, 'Live Demo Shipment', 250, 'WH-A (Chennai)', %s, %s, 'delayed')
    """, (order_id, supplier_id, expected_delivery, actual_delivery))
    conn.commit()
    print("Order created. Now triggering the pipeline (watch the terminal + dashboard)...")

    resp = requests.post(f"{API_BASE}/api/run-pipeline", timeout=120)
    resp.raise_for_status()
    data = resp.json()
    print(f"\nDone! Pipeline processed {data.get('processed')} new exception(s).")
    print(">>> Now refresh your dashboard in the browser to show the panel the new exception. <<<")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
EOF