from pathlib import Path

TARGET = Path(__file__).resolve().parent / "src" / "routes" / "knowledge-base.tsx"

OLD_BLOCK = '''  const handleDownload = (doc: DocumentRecord) => {
    toast.message("Download not yet connected to file storage", {
      description: doc.fileName,
    });
    // Best-effort: hit the metadata endpoint
    window.location.href = `${KB_API_BASE}/api/documents/${doc.id}/file`;
  };'''

NEW_BLOCK = '''  const handleDownload = (doc: DocumentRecord) => {
    window.location.href = `${KB_API_BASE}/api/documents/${doc.id}/file`;
  };'''


def patch():
    text = TARGET.read_text()
    if NEW_BLOCK in text and OLD_BLOCK not in text:
        print("Already cleaned up -- nothing to change.")
        return
    if OLD_BLOCK not in text:
        raise RuntimeError("Could not find the expected block -- file may differ from what we expect.")
    text = text.replace(OLD_BLOCK, NEW_BLOCK)
    TARGET.write_text(text)
    print("Cleaned up the misleading toast message in handleDownload.")


if __name__ == "__main__":
    patch()
