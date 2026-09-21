"""Diagnostic ponctuel : ou se classe le bon extrait dans la recherche
vectorielle, au dela des 15 retenus habituellement. Sert a savoir si un
simple N_RESULTS plus grand suffirait, ou si le probleme est plus profond
(l'extrait n'apparait meme pas dans les 40 premiers)."""
import warnings
warnings.filterwarnings("ignore")

import sys
import rag

question = " ".join(sys.argv[1:]) or "Comment regler le tempo sur le TR-1000 ?"
chunks = rag.rechercher(question, n=40)

print(f"Question : {question}\n")
for i, c in enumerate(chunks, 1):
    texte_maj = c["texte"].upper()
    interessant = "TEMPO" in texte_maj and ("C2" in texte_maj or "SETTING" in texte_maj or "SHUFFLE" in texte_maj)
    marque = "  <=== candidat 'Modification du tempo'" if interessant else ""
    print(f"[{i:2}] dist={c['distance']:.3f} {c['source']} p.{c['page']}{marque}")
    print(f"     {c['texte'][:150].replace(chr(10), ' ')}...")
