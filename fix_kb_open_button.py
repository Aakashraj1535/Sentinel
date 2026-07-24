"""
One-time patch: fixes the "open document" button in knowledge-base.tsx
so it points at the real file-serving endpoint instead of the metadata
endpoint, and uses window.location.href instead of window.open (which
gets silently blocked as a popup after an async action).

USAGE (run from inside your frontend project folder):
    python fix_kb_open_button.py
"""

from pathlib import Path

TARGET = Path(__file__).resolve().parent / "src" / "routes" / "knowledge-base.tsx"

OLD_LINE = 'window.open(`${KB_API_BASE}/api/documents/${doc.id}`, "_blank");'
NEW_LINE = 'window.location.href = `${KB_API_BASE}/api/documents/${doc.id}/file`;'


def patch():
    if not TARGET.exists():
        raise FileNotFoundError(f"Could not find {TARGET} -- run this from your frontend project root.")

    text = TARGET.read_text()

    if NEW_LINE in text:
        print("Already fixed -- nothing to change.")
        return

    if OLD_LINE not in text:
        raise RuntimeError(
            "Could not find the expected old line in the file. "
            "It may have already been edited differently. Stopping without changes."
        )

    text = text.replace(OLD_LINE, NEW_LINE)
    TARGET.write_text(text)
    print(f"Fixed! Updated {TARGET}")
    print(f"  Old: {OLD_LINE}")
    print(f"  New: {NEW_LINE}")


if __name__ == "__main__":
    patch()
