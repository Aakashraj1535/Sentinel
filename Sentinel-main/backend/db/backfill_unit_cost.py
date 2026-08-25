"""
Demo data enrichment: assigns a plausible unit_cost to every existing
order that doesn't have one yet.

Why this exists: migration 006 adds `orders.unit_cost`, but every order
already in the database (loaded before this migration existed) will have
it as NULL. The Financial Impact agent can't estimate exposure for an
order with no cost basis, so this backfills a realistic per-unit cost
based on the item type -- same spirit as backfill_demo_timestamps.py,
this only exists to make DEMO data usable, it doesn't change any agent
logic.

Run:  python -m db.backfill_unit_cost
Safe to run multiple times -- only fills rows where unit_cost IS NULL,
so it won't overwrite anything you set manually afterward.
"""

import random

from app.db import get_connection, get_dict_cursor

# Rough per-unit cost bands (USD) by item, loosely matched to the ITEMS
# list in backend/data/generate_synthetic_data.py. Deliberately a wide
# random range per item rather than a single fixed price -- real per-unit
# cost varies by batch/supplier even for the "same" item.
ITEM_UNIT_COST_RANGES = {
    "Packaging Material - Corrugated": (0.50, 2.50),
    "Steel Fasteners (M6)": (0.05, 0.40),
    "Injection-Molded Housings": (2.00, 9.00),
    "Circuit Board Assemblies": (15.00, 60.00),
    "Industrial Adhesive - 20L Drum": (80.00, 220.00),
    "Polymer Resin Pellets": (1.20, 3.50),
    "Aluminum Extrusions": (4.00, 14.00),
    "Rubber Gaskets - Bulk": (0.30, 1.80),
}
DEFAULT_RANGE = (1.00, 10.00)  # fallback for any item not in the table above


def backfill():
    conn = get_connection()
    cur = get_dict_cursor(conn)

    cur.execute("SELECT id, item FROM orders WHERE unit_cost IS NULL")
    orders = cur.fetchall()

    for o in orders:
        low, high = ITEM_UNIT_COST_RANGES.get(o["item"], DEFAULT_RANGE)
        unit_cost = round(random.uniform(low, high), 2)
        cur.execute(
            "UPDATE orders SET unit_cost = %s WHERE id = %s",
            (unit_cost, o["id"]),
        )

    conn.commit()
    cur.close()
    conn.close()
    print(f"Backfilled unit_cost on {len(orders)} order(s).")


if __name__ == "__main__":
    backfill()
