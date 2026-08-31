import warnings
warnings.filterwarnings("ignore")

import csv
import time
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import rag

ROOT = Path(__file__).parent.parent
LOG_FILE = ROOT / "data" / "logs.csv"

app = FastAPI(
    title="Assistant Roland",
    description="Chatbot RAG sur la documentation technique Roland",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class Question(BaseModel):
    question: str
    profil: str = "user"


@app.on_event("startup")
def startup():
    """Charge le modele et la base une seule fois au demarrage."""
    print("Chargement du modele d'embeddings et de ChromaDB ...")
    rag._init()
    if not LOG_FILE.exists():
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(
                ["date", "question", "hors_perimetre", "cause", "duree_s", "nb_sources"]
            )
    print("API prete.")


def journaliser(question, res, duree):
    with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            datetime.now().isoformat(timespec="seconds"),
            question,
            res["hors_perimetre"],
            res["cause"] or "",
            round(duree, 2),
            len(res["sources"]),
        ])


@app.get("/health")
def health():
    return {"status": "ok", "provider": rag.PROVIDER}


@app.post("/ask")
def ask(q: Question):
    if not q.question.strip():
        raise HTTPException(status_code=400, detail="Question vide")

    t0 = time.time()
    try:
        res = rag.repondre(q.question)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erreur LLM : {e}")
    duree = time.time() - t0

    journaliser(q.question, res, duree)

    reponse = {
        "reponse": res["reponse"],
        "sources": res["sources"],
        "hors_perimetre": res["hors_perimetre"],
        "duree": round(duree, 2),
    }

    # Le profil admin recoit en plus les donnees techniques
    if q.profil == "admin":
        reponse["debug"] = {
            "cause_refus": res["cause"],
            "modele_detecte": rag.detecter_modele(q.question),
            "requete_enrichie": rag.enrichir(q.question),
            "chunks": [
                {
                    "n": i + 1,
                    "source": c["source"],
                    "page": c["page"],
                    "distance": round(c["distance"], 3),
                    "extrait": c["texte"][:300],
                }
                for i, c in enumerate(res["chunks"])
            ],
        }

    return reponse


@app.get("/admin/stats")
def stats():
    _, col = rag._init()
    metas = col.get(include=["metadatas"])["metadatas"]

    par_doc = {}
    for m in metas:
        par_doc[m["source"]] = par_doc.get(m["source"], 0) + 1

    nb_questions, nb_refus, total_duree = 0, 0, 0.0
    if LOG_FILE.exists():
        with open(LOG_FILE, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                nb_questions += 1
                if row["hors_perimetre"] == "True":
                    nb_refus += 1
                total_duree += float(row["duree_s"])

    return {
        "documents": len(par_doc),
        "chunks_total": len(metas),
        "chunks_par_document": par_doc,
        "config": {
            "provider": rag.PROVIDER,
            "seuil_hors_perimetre": rag.SEUIL_HORS_PERIMETRE,
            "n_results": rag.N_RESULTS,
        },
        "usage": {
            "questions_posees": nb_questions,
            "refus": nb_refus,
            "duree_moyenne_s": round(total_duree / nb_questions, 2) if nb_questions else 0,
        },
    }