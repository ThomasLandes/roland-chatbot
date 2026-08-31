import warnings
warnings.filterwarnings("ignore")

import os
import re
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
N_RESULTS = 8

MODELES = ["TR-1000", "TB-03", "JU-06A", "SH-01A"]

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
_col = None


def _init():
    global _model, _col
    if _model is None:
        _model = SentenceTransformer("intfloat/multilingual-e5-small")
        client = chromadb.PersistentClient(path=str(ROOT / "data" / "chroma"))
        _col = client.get_collection("roland")
    return _model, _col


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
        kwargs["where"] = {"modele": modele}

    res = col.query(**kwargs)
    if not res["documents"] or not res["documents"][0]:
        return []
    return [
        {"texte": d, "source": m["source"], "page": m["page"], "distance": dist}
        for d, m, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0])
    ]


def appeler_llm(system, user):
    valides = {"anthropic", "openai", "groq", "mistral"}
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

    endpoints = {
        "openai": ("https://api.openai.com/v1/chat/completions", "gpt-4o-mini"),
        "groq": ("https://api.groq.com/openai/v1/chat/completions", "llama-3.3-70b-versatile"),
        "mistral": ("https://api.mistral.ai/v1/chat/completions", "mistral-small-latest"),
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

    if not chunks or chunks[0]["distance"] > SEUIL_HORS_PERIMETRE:
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