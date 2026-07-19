"""
Demo data enrichment: spreads existing exceptions' detected_at timestamps
realistically over the past ~35 days, instead of all clustering on
whichever day the Monitoring Agent happened to run.

Why this exists: the Predictive Risk Agent compares a "recent window" vs
a "prior window" of incidents per supplier. On a freshly-generated demo
database, every exception was detected on the same day, so there's no
real prior period to compare against — every supplier looks like it's
"Rising" by default, which isn't a bug, just an artifact of a fresh
dataset. In a real deployment running for weeks/months, this issue
wouldn't exist naturally. This script only exists to make the DEMO data
realistic; it does not change any agent logic.

Run:  python -m db.backfill_demo_timestamps
Safe to run multiple times (re-randomizes each time).
"""

import random
from datetime import timedelta

from app.db import get_connection, get_dict_cursor


def backfill():
    conn = get_connection()
    cur = get_dict_cursor(conn)

    cur.execute("SELECT id, detected_at FROM exceptions")
    exceptions = cur.fetchall()

    for exc in exceptions:
        # Spread across the last 35 days, weighted slightly toward recent
        # days so some suppliers plausibly show a "Rising" recent trend
        # while others show "Stable" or "Improving".
        days_ago = random.choices(
            population=range(0, 35),
            weights=[3 if d < 14 else 1 for d in range(35)],  # more density in recent window
            k=1,
        )[0]
        new_timestamp = exc["detected_at"] - timedelta(
            days=days_ago, hours=random.randint(0, 23)
        )
        cur.execute(
            "UPDATE exceptions SET detected_at = %s WHERE id = %s",
            (new_timestamp, exc["id"]),
        )

    conn.commit()
    cur.close()
    conn.close()
    print(f"Spread detected_at timestamps across {len(exceptions)} exceptions over the last 35 days.")


if __name__ == "__main__":
    backfill()
