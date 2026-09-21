"""Diagnostic ponctuel : verifie EXACTEMENT comment le chunking reel (celui
de ingest.py, tel que deploye) decoupe le passage "Modification du tempo"
du TR-1000, et a quel rang ce chunk ressort vraiment dans la recherche
vectorielle (jusqu'a 100, au lieu de 40 dans diag_rang.py)."""
import warnings
warnings.filterwarnings("ignore")

from ingest import read_pdf, chunk_text, PDF_DIR
import rag

CIBLE = "Modification du tempo"

f = PDF_DIR / "TR-1000_fra02_W.pdf"
text, offsets = read_pdf(f)
chunks = chunk_text(text, offsets)
cibles = [c for c in chunks if CIBLE in c["text"]]

print(f"{len(chunks)} chunks generes pour TR-1000 (chunking actuel).")
print(f"{len(cibles)} chunk(s) contiennent '{CIBLE}' :\n")
for c in cibles:
    print(f"--- page {c['page']}, {len(c['text'])} caracteres ---")
    print(c["text"])
    print()

question = "Comment regler le tempo sur le TR-1000 ?"
resultats = rag.rechercher(question, n=100)
print(f"\n{len(resultats)} resultats renvoyes par la recherche vectorielle reelle (max 100 demandes).")

trouve = False
for i, r in enumerate(resultats, 1):
    if CIBLE in r["texte"]:
        print(f"  -> trouve au rang {i}, distance {r['distance']:.3f}")
        trouve = True
if not trouve:
    print(f"  -> absent des {len(resultats)} premiers resultats")
