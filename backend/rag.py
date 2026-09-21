import warnings
warnings.filterwarnings("ignore")

import os
import re
import unicodedata
from pathlib import Path
import requests
import chromadb
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env")

PROVIDER = os.getenv("LLM_PROVIDER", "mistral")
API_KEY = os.getenv("LLM_API_KEY", "")

SEUIL_HORS_PERIMETRE = 0.19
# Releve a 15 (depuis 8) : sur les manuels courts (TB-03, JU-06A, SH-01A), les
# distances vectorielles sont tres resserrees (~0.11-0.13) et des paragraphes
# proches sur des sujets voisins (ex: "tempo" mentionne dans le reglage MIDI
# Clock Source) peuvent devancer le bon extrait de peu. Constate en pratique :
# "Comment regler le tempo sur le TB-03 ?" renvoyait 8 chunks pertinents mais
# aucun ne contenait la procedure, alors qu'elle existe bien dans le corpus.
N_RESULTS = 15

# Reclassement lexical : diagnostique via backend/diag_chunk.py sur "Comment
# regler le tempo sur le TR-1000 ?" - le chunk contenant la vraie procedure
# existe bien dans le corpus mais ressortait tres loin (38e, puis 55e apres
# une tentative de re-decoupage) dans les 100 premiers resultats purement
# vectoriels, alors qu'une question tres proche sur le TB-03 marchait. Plutot
# que de retoucher encore le decoupage (deja tente sans succes, voir le
# commentaire sur CHUNK_SIZE dans ingest.py), on elargit le pool de
# candidats quand la question cible un seul modele (recherche peu couteuse,
# filtree sur un document) et on penalise legerement la distance des chunks
# qui contiennent litteralement les mots de la question. Le score sert
# uniquement au tri : la distance brute (non modifiee) reste utilisee pour
# le seuil hors-perimetre et pour l'affichage.
N_ELARGI = 50
BONUS_PAR_MOT_CLE = 0.03
BONUS_MAX = 0.09
MOTS_VIDES = {
    "le", "la", "les", "l", "un", "une", "des", "de", "du", "sur", "en", "et",
    "a", "au", "aux", "pour", "avec", "dans", "comment", "quel", "quelle",
    "quels", "quelles", "est", "ce", "cette", "ces", "que", "qui", "son",
    "sa", "ses", "je", "tu", "il", "elle", "on", "vous", "nous", "ils",
    "elles", "d", "s", "ou", "est-ce", "peut", "peux",
}

PDF_DIR = ROOT / "data" / "pdf"


def _normaliser(mot):
    """Minuscule + suppression des accents, pour comparer independamment de
    la casse et des accents (ex: "regler" == "régler")."""
    return "".join(
        c for c in unicodedata.normalize("NFD", mot.lower())
        if unicodedata.category(c) != "Mn"
    )


def _mots_cles_requete(question):
    mots = re.findall(r"[a-zA-Z0-9]+", question)
    return {
        _normaliser(m) for m in mots
        if len(m) > 2 and _normaliser(m) not in MOTS_VIDES
    }


def _detecter_modeles_disponibles():
    """Deduit la liste des modeles a partir des noms de fichiers PDF presents
    (meme convention que ingest.py : prefixe avant le premier "_", ex.
    'TB-03_manuel.pdf' -> 'TB-03'). Remplace l'ancienne liste codee en dur :
    un nouveau document uploade est ainsi reconnu sans modifier le code."""
    if not PDF_DIR.exists():
        return []
    modeles = {f.stem.split("_")[0] for f in PDF_DIR.glob("*.pdf")}
    return sorted(modeles)


MODELES = _detecter_modeles_disponibles()

MESSAGE_REFUS = (
    "Je ne dispose pas de cette information dans la documentation Roland "
    "que je couvre. Pour toute autre question, contactez le support Roland : "
    "https://www.roland.com/fr/support/"
)

SYSTEM_PROMPT = """Tu es un assistant technique specialise dans les instruments Roland.

Regles imperatives :
1. Reponds UNIQUEMENT a partir des extraits de documentation fournis.
2. Si les extraits ne contiennent pas la reponse, ecris exactement : INFORMATION_ABSENTE
3. N'invente jamais de procedure, de nom de bouton ou de valeur.
4. Cite tes sources avec les marqueurs [Source N] places dans ton texte.
5. Reponds en francais, de maniere claire, avec des etapes numerotees si c'est une procedure.
6. Reste concis."""

SYNONYMES = {
    "sauvegarder": "sauvegarder enregistrer write memoriser",
    "enregistrer": "enregistrer write sauvegarder",
    "supprimer": "supprimer effacer clear delete",
    "connecter": "connecter brancher synchroniser midi",
    "regler": "regler parametrer configurer setting",
    "régler": "regler parametrer configurer setting",
}

_model = None
_client = None
_col = None


def _init():
    global _model, _client, _col
    if _model is None:
        # e5-base (768 dim) au lieu de e5-small (384 dim) : embeddings plus
        # discriminants, pour mieux distinguer des paragraphes voisins sur un
        # sujet proche (ex: "tempo" mentionne a la fois dans le reglage manuel
        # et dans la synchro MIDI Clock Source). Necessite un re-index complet
        # (python backend/ingest.py) : la dimension des vecteurs change.
        _model = SentenceTransformer("intfloat/multilingual-e5-base")
        # Un seul PersistentClient garde en memoire pour tout le process : en
        # creer un second en parallele (comme le faisait ingest.reindexer()
        # avec son propre client, ou comme le faisait rafraichir_apres_reindex
        # avant) peut laisser cette seconde instance avec une vue perimee de
        # la collection apres un delete_collection()/create_collection() fait
        # par la premiere, meme une fois la collection "re-fetchee" - constate
        # en pratique : une recherche via un process independant retrouvait un
        # excellent resultat (distance 0.098) juste apres une reindexation a
        # chaud, alors que la meme recherche via le serveur en cours
        # d'execution refusait la question. Utiliser TOUJOURS le meme client
        # pour lire et pour ecrire evite ce genre d'incoherence.
        _client = chromadb.PersistentClient(path=str(ROOT / "data" / "chroma"))
        _col = _client.get_collection("roland")
    return _model, _col


def get_client():
    """Le PersistentClient partage par tout le process, pour que
    ingest.reindexer() ecrive avec le meme client que celui utilise ici pour
    lire (voir le commentaire dans _init())."""
    _init()
    return _client


def rafraichir_apres_reindex():
    """A appeler juste apres un reindexer() (ingest.py) declenche a chaud par
    l'API : la collection Chroma a ete supprimee puis recreee, il faut donc
    en reprendre une reference fraiche (get_collection) sans quoi les
    requetes suivantes echoueraient (ancien handle invalide). Rafraichit
    aussi MODELES pour reconnaitre un nouveau document sans redemarrer le
    process. Le modele d'embeddings, lui, ne change pas et n'a pas besoin
    d'etre recharge."""
    global _col, MODELES
    _init()
    _col = _client.get_collection("roland")
    MODELES = _detecter_modeles_disponibles()
    return {"modeles": MODELES}


def enrichir(question):
    q = question.lower()
    ajouts = [v for k, v in SYNONYMES.items() if k in q]
    return question + (" " + " ".join(ajouts) if ajouts else "")


def detecter_modele(question):
    q = question.upper().replace(" ", "").replace("-", "")
    for m in MODELES:
        if m.replace("-", "") in q:
            return m
    return None


def rechercher(question, n=N_RESULTS):
    model, col = _init()
    vec = model.encode(f"query: {enrichir(question)}", normalize_embeddings=True).tolist()

    modele = detecter_modele(question)
    kwargs = {"query_embeddings": [vec], "n_results": n}
    if modele:
        # Recherche bornee a un seul document : peu couteux d'elargir le pool
        # de candidats pour donner une chance au reclassement lexical
        # ci-dessous (voir le commentaire sur N_ELARGI plus haut).
        kwargs["where"] = {"modele": modele}
        kwargs["n_results"] = max(n, N_ELARGI)

    res = col.query(**kwargs)
    if not res["documents"] or not res["documents"][0]:
        return []

    resultats = [
        {"texte": d, "source": m["source"], "page": m["page"], "distance": dist}
        for d, m, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0])
    ]

    if modele:
        mots = _mots_cles_requete(question)
        if mots:
            for r in resultats:
                texte_norm = _normaliser(r["texte"])
                hits = sum(1 for mot in mots if mot in texte_norm)
                r["_score"] = r["distance"] - min(hits * BONUS_PAR_MOT_CLE, BONUS_MAX)
            resultats.sort(key=lambda r: r["_score"])
            for r in resultats:
                del r["_score"]

    return resultats[:n]


def appeler_llm(system, user):
    valides = {"anthropic", "openai", "groq", "mistral", "grok"}
    if PROVIDER not in valides:
        raise ValueError(
            f"LLM_PROVIDER='{PROVIDER}' inconnu. Valeurs acceptees : {sorted(valides)}"
        )
    if not API_KEY:
        raise ValueError("LLM_API_KEY est vide. Verifie ton fichier .env")

    if PROVIDER == "anthropic":
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": "claude-sonnet-4-5",
            "max_tokens": 800,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        r = requests.post(url, headers=headers, json=payload, timeout=60)
        r.raise_for_status()
        return r.json()["content"][0]["text"]

    # Les autres fournisseurs exposent tous une API compatible OpenAI
    # (meme forme de requete/reponse), y compris xAI (Grok).
    endpoints = {
        "openai": ("https://api.openai.com/v1/chat/completions", "gpt-4o-mini"),
        "groq": ("https://api.groq.com/openai/v1/chat/completions", "llama-3.3-70b-versatile"),
        "mistral": ("https://api.mistral.ai/v1/chat/completions", "mistral-small-latest"),
        "grok": ("https://api.x.ai/v1/chat/completions", "grok-4.6"),
    }
    url, modele = endpoints[PROVIDER]
    r = requests.post(
        url,
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
        json={
            "model": modele,
            "max_tokens": 800,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        },
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def repondre(question, debug=False):
    chunks = rechercher(question)

    if debug:
        print("\n--- CHUNKS RECUPERES ---")
        for i, c in enumerate(chunks, 1):
            print(f"[{i}] dist={c['distance']:.3f} {c['source']} p.{c['page']}")
            print(f"    {c['texte'][:200]}...\n")

    # min() et non chunks[0] : depuis le reclassement lexical (voir
    # rechercher()), le premier chunk de la liste n'est plus forcement celui
    # avec la meilleure distance vectorielle brute (un chunk contenant les
    # mots de la question peut passer devant). Le seuil hors-perimetre doit
    # rester base sur la meilleure correspondance vectorielle reelle, pas sur
    # l'ordre d'affichage.
    if not chunks or min(c["distance"] for c in chunks) > SEUIL_HORS_PERIMETRE:
        return {"reponse": MESSAGE_REFUS, "sources": [], "hors_perimetre": True,
                "cause": "distance", "chunks": chunks}

    contexte = "\n\n".join(
        f"[Source {i+1}] ({c['source']}, page {c['page']})\n{c['texte']}"
        for i, c in enumerate(chunks)
    )
    user = f"Extraits de documentation :\n\n{contexte}\n\nQuestion de l'utilisateur : {question}"

    texte = appeler_llm(SYSTEM_PROMPT, user)

    if debug:
        print("--- REPONSE BRUTE DU LLM ---")
        print(texte)
        print("---\n")

    if "INFORMATION_ABSENTE" in texte:
        return {"reponse": MESSAGE_REFUS, "sources": [], "hors_perimetre": True,
                "cause": "llm", "chunks": chunks}

    citees = set(int(n) for n in re.findall(r"\[Source (\d+)\]", texte))
    sources = [
        {"n": i + 1, "source": c["source"], "page": c["page"],
         "distance": round(c["distance"], 3)}
        for i, c in enumerate(chunks)
        if not citees or (i + 1) in citees
    ]

    return {"reponse": texte, "sources": sources, "hors_perimetre": False,
            "cause": None, "chunks": chunks}


if __name__ == "__main__":
    import sys, time
    args = sys.argv[1:]
    debug = "--debug" in args
    args = [a for a in args if a != "--debug"]
    q = " ".join(args) or "Comment sauvegarder un pattern sur le TR-1000 ?"
    t0 = time.time()
    r = repondre(q, debug=debug)
    print(f"\nQ: {q}\n")
    print(r["reponse"])
    if r["cause"]:
        print(f"\n[refus declenche par : {r['cause']}]")
    if r["sources"]:
        print("\nSources :")
        for s in r["sources"]:
            print(f"  [{s['n']}] {s['source']} p.{s['page']} (dist {s['distance']})")
    print(f"\nTemps : {time.time() - t0:.2f}s")
