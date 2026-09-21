import warnings
warnings.filterwarnings("ignore")

import csv
import re
import sqlite3
import time
from datetime import datetime
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from starlette.concurrency import run_in_threadpool

import auth
import db
import ingest
import rag

ROOT = Path(__file__).parent.parent
LOG_FILE = ROOT / "data" / "logs.csv"

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

TAILLE_MAX_UPLOAD = 30 * 1024 * 1024  # 30 Mo

app = FastAPI(
    title="Assistant Roland",
    description="Chatbot RAG sur la documentation technique Roland",
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class Question(BaseModel):
    question: str


class InscriptionIn(BaseModel):
    email: str
    mot_de_passe: str

    @field_validator("email")
    @classmethod
    def email_valide(cls, v):
        v = v.strip().lower()
        if not EMAIL_RE.match(v):
            raise ValueError("Adresse e-mail invalide")
        return v

    @field_validator("mot_de_passe")
    @classmethod
    def mot_de_passe_valide(cls, v):
        if len(v) < 8:
            raise ValueError("Le mot de passe doit contenir au moins 8 caracteres")
        return v


class ConnexionIn(BaseModel):
    email: str
    mot_de_passe: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    email: str
    role: str


class UserOut(BaseModel):
    id: int
    email: str
    role: str
    created_at: str


class RoleIn(BaseModel):
    role: str

    @field_validator("role")
    @classmethod
    def role_valide(cls, v):
        if v not in db.ROLES_VALIDES:
            raise ValueError(f"Role invalide (attendu : {sorted(db.ROLES_VALIDES)})")
        return v


class DocumentOut(BaseModel):
    nom: str
    taille_octets: int


# ---------------------------------------------------------------------------
# Demarrage
# ---------------------------------------------------------------------------

@app.on_event("startup")
def startup():
    """Charge le modele et la base une seule fois au demarrage."""
    print("Initialisation de la base utilisateurs ...")
    db.init_db()

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


# ---------------------------------------------------------------------------
# Authentification
# ---------------------------------------------------------------------------

@app.post("/auth/register", response_model=TokenOut)
def inscription(donnees: InscriptionIn):
    if db.get_user_by_email(donnees.email) is not None:
        raise HTTPException(status_code=409, detail="Un compte existe deja avec cet e-mail")

    hash_mdp = auth.hasher_mot_de_passe(donnees.mot_de_passe)
    try:
        # Tous les comptes crees ici sont 'user'. Pour obtenir un compte
        # admin, voir backend/make_admin.py.
        user = db.create_user(donnees.email, hash_mdp, role="user")
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Un compte existe deja avec cet e-mail")

    token = auth.creer_token(user)
    return TokenOut(access_token=token, email=user["email"], role=user["role"])


@app.post("/auth/login", response_model=TokenOut)
def connexion(donnees: ConnexionIn):
    erreur = HTTPException(status_code=401, detail="E-mail ou mot de passe incorrect")

    user = db.get_user_by_email(donnees.email)
    if user is None:
        raise erreur
    if not auth.verifier_mot_de_passe(donnees.mot_de_passe, user["password_hash"]):
        raise erreur

    token = auth.creer_token(user)
    return TokenOut(access_token=token, email=user["email"], role=user["role"])


@app.get("/auth/me")
def moi(user: dict = Depends(auth.utilisateur_courant)):
    return {"id": user["id"], "email": user["email"], "role": user["role"]}


# ---------------------------------------------------------------------------
# Chatbot
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok", "provider": rag.PROVIDER}


@app.post("/ask")
def ask(q: Question, user: dict = Depends(auth.utilisateur_courant)):
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

    # Le role admin recoit en plus les donnees techniques. Le role vient du
    # token verifie cote serveur : un utilisateur ne peut pas se l'attribuer
    # lui-meme en modifiant la requete.
    if user["role"] == "admin":
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
def stats(user: dict = Depends(auth.admin_requis)):
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


# ---------------------------------------------------------------------------
# Gestion des utilisateurs (admin)
# ---------------------------------------------------------------------------

@app.get("/admin/users", response_model=list[UserOut])
def lister_utilisateurs(admin: dict = Depends(auth.admin_requis)):
    return db.list_users()


@app.patch("/admin/users/{user_id}/role", response_model=UserOut)
def changer_role(user_id: int, donnees: RoleIn, admin: dict = Depends(auth.admin_requis)):
    cible = db.get_user_by_id(user_id)
    if cible is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    if cible["id"] == admin["id"]:
        raise HTTPException(
            status_code=400,
            detail="Tu ne peux pas modifier ton propre role depuis cette interface",
        )

    if cible["role"] == "admin" and donnees.role == "user" and db.count_admins() <= 1:
        raise HTTPException(
            status_code=400,
            detail="Impossible de retirer le role admin au dernier administrateur",
        )

    db.set_role(cible["email"], donnees.role)
    return db.get_user_by_id(user_id)


@app.delete("/admin/users/{user_id}")
def supprimer_utilisateur(user_id: int, admin: dict = Depends(auth.admin_requis)):
    cible = db.get_user_by_id(user_id)
    if cible is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    if cible["id"] == admin["id"]:
        raise HTTPException(
            status_code=400, detail="Tu ne peux pas supprimer ton propre compte"
        )

    if cible["role"] == "admin" and db.count_admins() <= 1:
        raise HTTPException(
            status_code=400, detail="Impossible de supprimer le dernier administrateur"
        )

    db.delete_user(user_id)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Gestion des documents (admin) : upload d'un nouveau PDF + reindexation
# ---------------------------------------------------------------------------

@app.get("/admin/documents", response_model=list[DocumentOut])
def lister_documents(admin: dict = Depends(auth.admin_requis)):
    ingest.PDF_DIR.mkdir(parents=True, exist_ok=True)
    return [
        {"nom": f.name, "taille_octets": f.stat().st_size}
        for f in sorted(ingest.PDF_DIR.glob("*.pdf"))
    ]


@app.post("/admin/documents/upload", response_model=DocumentOut)
async def uploader_document(
    fichier: UploadFile = File(...), admin: dict = Depends(auth.admin_requis)
):
    nom = Path(fichier.filename or "").name  # retire tout chemin (securite)
    if not nom.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Seuls les fichiers PDF sont acceptes")

    contenu = await fichier.read()
    if not contenu:
        raise HTTPException(status_code=400, detail="Fichier vide")
    if len(contenu) > TAILLE_MAX_UPLOAD:
        raise HTTPException(
            status_code=400,
            detail=f"Fichier trop volumineux (max {TAILLE_MAX_UPLOAD // (1024*1024)} Mo)",
        )

    ingest.PDF_DIR.mkdir(parents=True, exist_ok=True)
    destination = ingest.PDF_DIR / nom
    destination.write_bytes(contenu)

    return {"nom": nom, "taille_octets": len(contenu)}


@app.delete("/admin/documents/{nom}")
def supprimer_document(nom: str, admin: dict = Depends(auth.admin_requis)):
    """Supprime le fichier PDF du disque. Ses chunks restent dans Chroma
    tant qu'une reindexation n'a pas ete relancee (reindexer() reconstruit
    la collection entiere a partir des PDF presents a ce moment-la) : c'est
    volontairement simple plutot que de gerer une suppression ciblee dans
    Chroma."""
    nom = Path(nom).name  # retire tout chemin (securite)
    cible = ingest.PDF_DIR / nom
    if not nom.lower().endswith(".pdf") or not cible.is_file():
        raise HTTPException(status_code=404, detail="Document introuvable")

    cible.unlink()
    return {"ok": True}


@app.get("/admin/documents/reindex/status")
def statut_reindexation(admin: dict = Depends(auth.admin_requis)):
    """Interroge l'avancement d'une reindexation en cours, pour la barre de
    progression du frontend (poll cote client, pas de websocket : plus
    simple, suffisant vu la frequence d'usage de cette fonctionnalite)."""
    return ingest.etat_reindexation()


@app.post("/admin/documents/reindex")
async def reindexer_documents(admin: dict = Depends(auth.admin_requis)):
    """Relance l'indexation complete (tous les PDF de data/pdf/) puis
    rafraichit la collection Chroma et la liste des modeles utilisee par
    l'API en cours d'execution, sans redemarrage. Execute dans un
    threadpool : reindexer() est bloquant (I/O + calcul CPU) et ne doit pas
    geler la boucle asyncio pendant potentiellement plusieurs dizaines de
    secondes."""
    modele_embeddings, _ = rag._init()
    try:
        resume = await run_in_threadpool(
            ingest.reindexer, model=modele_embeddings, verbose=False, client=rag.get_client()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Echec de l'indexation : {e}")

    rag.rafraichir_apres_reindex()
    return resume
