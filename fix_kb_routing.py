"""
Fix: Knowledge Base routing (parent/child Outlet issue)
===========================================================
knowledge-base.tsx and knowledge-base.$documentId.tsx are being treated as
a parent/child route pair by the router. The parent needs an <Outlet />
to actually display the child page's content -- without it, the parent
always renders its own full content regardless of the URL.

This script:
  1. Backs up your current knowledge-base.tsx (just in case).
  2. Moves its current content into a new file, knowledge-base.index.tsx
     (this becomes the actual list page, shown at exactly /knowledge-base).
  3. Replaces knowledge-base.tsx with a minimal layout that renders
     whichever child route is active via <Outlet />.

USAGE (run from your frontend project root):
    python3 fix_kb_routing.py
"""

import re
import shutil
from pathlib import Path

ROUTES_DIR = Path(__file__).resolve().parent / "src" / "routes"
PARENT = ROUTES_DIR / "knowledge-base.tsx"
INDEX = ROUTES_DIR / "knowledge-base.index.tsx"
BACKUP = ROUTES_DIR / "knowledge-base.tsx.backup"

NEW_LAYOUT = '''import { createFileRoute, Outlet } from "@tanstack/react-router";

export const Route = createFileRoute("/knowledge-base")({
  component: KnowledgeBaseLayout,
});

function KnowledgeBaseLayout() {
  return <Outlet />;
}
'''


def fix():
    if not PARENT.exists():
        raise FileNotFoundError(f"Could not find {PARENT} -- run this from your frontend project root.")

    if INDEX.exists():
        print("Looks like this fix already ran -- knowledge-base.index.tsx already exists. "
              "Skipping to avoid overwriting it.")
        return

    original = PARENT.read_text()

    # Safety backup
    shutil.copy(PARENT, BACKUP)
    print(f"Backed up original to {BACKUP}")

    # Move the original list-page content into the new index file,
    # updating its route path to the index convention.
    index_content = original.replace(
        'createFileRoute("/knowledge-base")',
        'createFileRoute("/knowledge-base/")'
    )
    if index_content == original:
        # fallback in case of different quote style
        index_content = re.sub(
            r'createFileRoute\([\'"]\/knowledge-base[\'"]\)',
            'createFileRoute("/knowledge-base/")',
            original
        )

    INDEX.write_text(index_content)
    print(f"Created {INDEX} with your existing list page content.")

    # Replace the parent with a minimal layout
    PARENT.write_text(NEW_LAYOUT)
    print(f"Replaced {PARENT} with a minimal layout using <Outlet />.")

    print("\nDone. Your dev server should auto-detect these file changes and "
          "regenerate the route tree. If you see a build error, check the "
          "terminal running 'npm run dev' and paste it back.")


if __name__ == "__main__":
    fix()
