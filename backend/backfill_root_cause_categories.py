"""
One-time backfill: re-classify existing exceptions whose root cause
category is still NULL, using the current (broadened) keyword matcher in
app/root_cause.py.

Why this exists: exceptions resolved BEFORE the root cause tagging
feature (or before a keyword-list improvement) will never retroactively
get a category just by restarting the backend -- resolution_agent.py
only classifies at the moment an exception is resolved, and deliberately
never overwrites an existing category. This script is the one-time catch-
up pass for data that already existed before/during that feature's
rollout.

Safe to run multiple times -- only touches rows where
root_cause_category IS NULL, so it will never overwrite a human
correction or a category already set (whether 'auto' or 'human').

USAGE:
    python backfill_root_cause_categories.py           # apply changes
    python backfill_root_cause_categories.py --dry-run # preview only, no writes
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.db import get_connection, get_dict_cursor  # noqa: E402
from app.root_cause import classify_root_cause  # noqa: E402


def main():
    dry_run = "--dry-run" in sys.argv

    conn = get_connection()
    cur = get_dict_cursor(conn)

    cur.execute("""
        SELECT id, root_cause
        FROM exceptions
        WHERE root_cause_category IS NULL AND root_cause IS NOT NULL
    """)
    candidates = cur.fetchall()

    if not candidates:
        print("Nothing to backfill -- every exception with a root_cause already "
              "has a category (or has no root_cause yet).")
        cur.close()
        conn.close()
        return

    print(f"Found {len(candidates)} exception(s) with an uncategorized root cause.\n")

    updated = 0
    still_uncategorized = 0
    for row in candidates:
        category = classify_root_cause(row["root_cause"])
        if category:
            print(f"  {row['id']}: -> {category}")
            if not dry_run:
                cur.execute("""
                    UPDATE exceptions
                    SET root_cause_category = %s, root_cause_category_source = 'auto'
                    WHERE id = %s
                """, (category, row["id"]))
            updated += 1
        else:
            still_uncategorized += 1

    if not dry_run:
        conn.commit()

    cur.close()
    conn.close()

    print(f"\n{'Would update' if dry_run else 'Updated'}: {updated}")
    print(f"Still uncategorized (no keyword match -- needs a human 'Correct' tag): "
          f"{still_uncategorized}")
    if dry_run:
        print("\nThis was a dry run -- nothing was written. Re-run without --dry-run to apply.")


if __name__ == "__main__":
    main()
