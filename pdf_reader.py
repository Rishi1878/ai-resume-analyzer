"""
pdf_reader.py
-------------
Utility to extract text from PDF resumes.
Requires: pip install pdfplumber
"""

from pathlib import Path
from typing import Optional


def extract_text_from_pdf(pdf_path: str) -> Optional[str]:
    """
    Extracts all text from a PDF file using pdfplumber.
    Falls back page-by-page if full extraction fails.
    """
    try:
        import pdfplumber
    except ImportError:
        raise ImportError(
            "pdfplumber is required for PDF support.\n"
            "Install it with: pip install pdfplumber"
        )

    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    pages_text = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages_text.append(text.strip())

    if not pages_text:
        return None

    return "\n\n".join(pages_text)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python pdf_reader.py resume.pdf")
        sys.exit(1)
    text = extract_text_from_pdf(sys.argv[1])
    print(text or "[No text extracted]")
