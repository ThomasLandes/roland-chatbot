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

# e5-base (768 dim) au lieu de e5-small (384 dim) : embeddings plus
# discriminants. Doit rester identique au modele charge dans rag.py._init(),
# sinon les distances calculees a la recherche n'ont plus de sens.
MODEL_NAME = "intfloat/multilingual-e5-base"
COLLECTION = "roland"
# Retour a 1400/300 : la coupure nette a chaque "titre de section" (testee
# via backend/diag_chunk.py) isolait bien le chunk vise ("Modification du
# tempo" sur le TR-1000, plus de residu de la section precedente) mais son
# rang dans la recherche vectorielle a EMPIRE (38e -> 55e sur 100) et une
# question auparavant fiable (TB-03, meme sujet) s'est mise a echouer. Le
# probleme n'est donc pas la proprete du chunk mais le classement de la
# recherche elle-meme : traite maintenant cote recherche (voir le reclassement
# lexical dans rag.py.rechercher), pas cote decoupage.
CHUNK_SIZE = 1400
OVERLAP = 300

# Etat partage, lu par l'API (GET /admin/documents/reindex/status) pendant
# qu'un reindexer() tourne dans un thread separe, pour afficher une barre de
# progression cote frontend. Pas de verrou : une simple lecture/ecriture de
# dict suffit pour un indicateur d'avancement, pas besoin de plus ici.
_progression = {"en_cours": False, "phase": None, "fichier": None, "traites": 0, "total": 0}


def etat_reindexation():
    return dict(_progression)


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
    """Decoupe en respectant les sauts de ligne pour ne pas couper les mots,
    avec un recouvrement (OVERLAP) entre chunks successifs pour ne pas
    perdre le contexte a la frontiere."""
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


def reindexer(model=None, verbose=True, client=None):
    """Reconstruit entierement la collection Chroma a partir des PDF presents
    dans data/pdf/. Reutilisable depuis l'API (apres un upload admin) ou en
    ligne de commande (main()).

    model : instance SentenceTransformer deja chargee, pour eviter de la
            recharger si l'appelant l'a deja en memoire (ex: rag.py, qui
            garde le meme modele que l'API en cours d'execution). Si None,
            le modele est charge ici.
    client : chromadb.PersistentClient deja ouvert, a reutiliser plutot que
             d'en creer un nouveau (important quand reindexer() est appele
             a chaud par l'API : reutiliser rag.get_client() evite qu'une
             deuxieme instance de client, pointant sur le meme dossier,
             garde une vue perimee de la collection apres qu'on l'ait
             supprimee/recreee ici). Si None (usage CLI autonome), un
             client independant est cree.

    Retourne un resume : {"documents": int, "chunks_total": int,
    "modeles": [str], "details": [{"fichier", "chunks", "modele"}]}.
    """
    files = sorted(PDF_DIR.glob("*.pdf"))
    if not files:
        if verbose:
            print("Aucun PDF dans", PDF_DIR)
        return {"documents": 0, "chunks_total": 0, "modeles": [], "details": []}

    _progression.update(en_cours=True, phase="chargement", fichier=None, traites=0, total=len(files))
    try:
        if model is None:
            if verbose:
                print(f"Chargement du modele {MODEL_NAME} ...")
            model = SentenceTransformer(MODEL_NAME)

        if client is None:
            client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        if COLLECTION in [c.name for c in client.list_collections()]:
            client.delete_collection(COLLECTION)
        col = client.create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})

        total = 0
        modeles = set()
        details = []
        _progression["phase"] = "indexation"
        for f in files:
            _progression["fichier"] = f.name

            text, offsets = read_pdf(f)
            chunks = chunk_text(text, offsets)
            if not chunks:
                if verbose:
                    print(f"  {f.name} : aucun chunk, ignore")
                details.append({"fichier": f.name, "chunks": 0, "modele": None})
                _progression["traites"] += 1
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
            modeles.add(modele)
            details.append({"fichier": f.name, "chunks": len(chunks), "modele": modele})
            _progression["traites"] += 1
            if verbose:
                print(f"  {f.name:45} {len(chunks):5} chunks  (modele: {modele})")

        if verbose:
            print(f"\nIndexation terminee : {total} chunks dans {CHROMA_DIR}")

        return {
            "documents": len(files),
            "chunks_total": total,
            "modeles": sorted(modeles),
            "details": details,
        }
    finally:
        # Toujours remis a jour, meme en cas d'erreur : le frontend ne doit
        # jamais rester bloque sur une barre de progression figee.
        _progression.update(en_cours=False, phase=None, fichier=None)


def main():
    reindexer()


if __name__ == "__main__":
    main()
