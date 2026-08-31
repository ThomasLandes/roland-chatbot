from pathlib import Path
import chromadb
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).parent.parent
model = SentenceTransformer("intfloat/multilingual-e5-small")
client = chromadb.PersistentClient(path=str(ROOT / "data" / "chroma"))
col = client.get_collection("roland")

QUESTIONS = [
    "Comment sauvegarder un pattern ?",
    "Comment regler le tempo ?",
    "Comment connecter l'instrument en MIDI ?",
    "Quelle est la recette de la tarte aux pommes ?",
]

for q in QUESTIONS:
    vec = model.encode(f"query: {q}", normalize_embeddings=True).tolist()
    res = col.query(query_embeddings=[vec], n_results=3)
    print(f"\n=== {q}")
    for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
        extrait = doc[:110].replace("\n", " ")
        print(f"  [{dist:.3f}] {meta['source']} p.{meta['page']} | {extrait}...")