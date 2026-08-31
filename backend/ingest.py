import warnings
warnings.filterwarnings("ignore")

from pathlib import Path
import re
import chromadb
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).parent.parent
PDF_DIR = ROOT / "data" / "pdf"
CHROMA_DIR = ROOT / "data" / "chroma"

MODEL_NAME = "intfloat/multilingual-e5-small"
COLLECTION = "roland"
CHUNK_SIZE = 1400
OVERLAP = 300


def clean(text):
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def read_pdf(path):
    """Retourne le texte complet + une table offset -> numero de page."""
    reader = PdfReader(path)
    parts, offsets = [], []
    cursor = 0
    for i, page in enumerate(reader.pages, start=1):
        txt = clean(page.extract_text() or "")
        if not txt:
            continue
        offsets.append((cursor, i))
        parts.append(txt)
        cursor += len(txt) + 1
    return "\n".join(parts), offsets


def page_of(offset, offsets):
    page = offsets[0][1] if offsets else 1
    for start, num in offsets:
        if start <= offset:
            page = num
        else:
            break
    return page


def chunk_text(text, offsets):
    """Decoupe en respectant les sauts de ligne pour ne pas couper les mots."""
    lignes = text.split("\n")
    chunks = []
    buf, buf_len, buf_start = [], 0, 0
    cursor = 0

    for ligne in lignes:
        if buf_len + len(ligne) > CHUNK_SIZE and buf:
            piece = "\n".join(buf).strip()
            if len(piece) >= 100:
                chunks.append({"text": piece, "page": page_of(buf_start, offsets)})
            garde, taille = [], 0
            for l in reversed(buf):
                if taille + len(l) > OVERLAP:
                    break
                garde.insert(0, l)
                taille += len(l) + 1
            buf = garde
            buf_len = taille
            buf_start = cursor - taille

        if not buf:
            buf_start = cursor
        buf.append(ligne)
        buf_len += len(ligne) + 1
        cursor += len(ligne) + 1

    piece = "\n".join(buf).strip()
    if len(piece) >= 100:
        chunks.append({"text": piece, "page": page_of(buf_start, offsets)})
    return chunks


def main():
    files = sorted(PDF_DIR.glob("*.pdf"))
    if not files:
        print("Aucun PDF dans", PDF_DIR)
        return

    print(f"Chargement du modele {MODEL_NAME} ...")
    model = SentenceTransformer(MODEL_NAME)

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    if COLLECTION in [c.name for c in client.list_collections()]:
        client.delete_collection(COLLECTION)
    col = client.create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})

    total = 0
    for f in files:
        text, offsets = read_pdf(f)
        chunks = chunk_text(text, offsets)
        if not chunks:
            print(f"  {f.name} : aucun chunk, ignore")
            continue

        modele = f.stem.split("_")[0]

        vectors = model.encode(
            [f"passage: {c['text']}" for c in chunks],
            batch_size=32,
            show_progress_bar=False,
            normalize_embeddings=True,
        ).tolist()

        col.add(
            ids=[f"{f.stem}_{i}" for i in range(len(chunks))],
            documents=[c["text"] for c in chunks],
            embeddings=vectors,
            metadatas=[
                {"source": f.name, "page": c["page"], "modele": modele}
                for c in chunks
            ],
        )
        total += len(chunks)
        print(f"  {f.name:45} {len(chunks):5} chunks  (modele: {modele})")

    print(f"\nIndexation terminee : {total} chunks dans {CHROMA_DIR}")


if __name__ == "__main__":
    main()