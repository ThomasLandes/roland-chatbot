from pathlib import Path
from pypdf import PdfReader

PDF_DIR = Path(__file__).parent.parent / "data" / "pdf"

def check():
    files = sorted(PDF_DIR.glob("*.pdf"))
    if not files:
        print("Aucun PDF trouve dans", PDF_DIR)
        return

    total_chars = 0
    for f in files:
        reader = PdfReader(f)
        pages = len(reader.pages)
        chars = sum(len(p.extract_text() or "") for p in reader.pages)
        total_chars += chars
        ratio = chars / pages if pages else 0
        statut = "OK" if ratio > 200 else "SUSPECT (scan image ?)"
        print(f"{f.name:45} {pages:4} pages {chars:8} chars  {ratio:6.0f} c/page  {statut}")

    print(f"\n{len(files)} documents, {total_chars} caracteres au total")

if __name__ == "__main__":
    check()