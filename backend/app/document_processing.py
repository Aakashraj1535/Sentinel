"""
Document text extraction and chunking.
Supports PDF, DOCX, TXT, CSV, and XLSX — spreadsheet formats are converted
to readable row-by-row text so they can be embedded and retrieved like any
other document.
"""

import re
import pandas as pd
from pypdf import PdfReader
from docx import Document as DocxDocument


def extract_text(file_path: str, file_name: str) -> str:
    ext = file_name.lower().rsplit(".", 1)[-1]

    if ext == "pdf":
        reader = PdfReader(file_path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    elif ext == "docx":
        doc = DocxDocument(file_path)
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())

    elif ext == "txt":
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    elif ext == "csv":
        df = pd.read_csv(file_path)
        return _dataframe_to_text(df)

    elif ext in ("xlsx", "xls"):
        # Read all sheets; label each one so multi-sheet workbooks stay readable
        sheets = pd.read_excel(file_path, sheet_name=None)
        parts = []
        for sheet_name, df in sheets.items():
            parts.append(f"Sheet: {sheet_name}")
            parts.append(_dataframe_to_text(df))
        return "\n\n".join(parts)

    else:
        raise ValueError(f"Unsupported file type: .{ext}")


def _dataframe_to_text(df: pd.DataFrame) -> str:
    """
    Converts a spreadsheet into readable sentences — one per row, naming
    each column — rather than a raw table dump, so embeddings capture
    meaning the same way they would for prose text.
    """
    df = df.fillna("")
    lines = []
    for _, row in df.iterrows():
        parts = [f"{col}: {row[col]}" for col in df.columns if str(row[col]).strip()]
        if parts:
            lines.append(", ".join(parts) + ".")
    return "\n".join(lines)


def chunk_text(text: str, target_words: int = 150) -> list:
    """
    Splits text into paragraph-sized chunks (~target_words each).
    Keeps whole sentences together rather than cutting mid-sentence.
    """
    # Normalize whitespace first
    text = re.sub(r"\s+", " ", text).strip()
    sentences = re.split(r"(?<=[.!?])\s+", text)

    chunks = []
    current = []
    word_count = 0

    for sentence in sentences:
        words_in_sentence = len(sentence.split())
        if word_count + words_in_sentence > target_words and current:
            chunks.append(" ".join(current))
            current = []
            word_count = 0
        current.append(sentence)
        word_count += words_in_sentence

    if current:
        chunks.append(" ".join(current))

    return [c for c in chunks if c.strip()]
