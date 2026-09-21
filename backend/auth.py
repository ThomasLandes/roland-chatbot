"""Authentification : hash des mots de passe, tokens JWT, dependances FastAPI.

- Mots de passe : bcrypt (deja present dans requirements.txt).
- Sessions : JWT signes (PyJWT), envoyes par le client dans l'en-tete
  "Authorization: Bearer <token>". Pas de session cote serveur : le
  token porte l'identite (sub = id utilisateur) et le role au moment
  de la connexion.
"""

import os
import warnings
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pathlib import Path
from dotenv import load_dotenv

import db

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env")

SECRET_KEY = os.getenv("JWT_SECRET", "")
ALGORITHM = "HS256"
EXPIRATION_MINUTES = 60 * 24  # 24h

if not SECRET_KEY:
    # Ne bloque pas le demarrage (pratique en dev), mais previent clairement :
    # sans cle stable, tous les tokens deviennent invalides a chaque redemarrage.
    warnings.warn(
        "JWT_SECRET est vide dans .env : une cle temporaire aleatoire est "
        "utilisee, les utilisateurs seront deconnectes a chaque redemarrage "
        "de l'API. Ajoute JWT_SECRET=<chaine longue et aleatoire> dans .env."
    )
    import secrets

    SECRET_KEY = secrets.token_hex(32)

_bearer = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# Mots de passe
# ---------------------------------------------------------------------------

def hasher_mot_de_passe(mot_de_passe: str) -> str:
    # bcrypt ignore tout au-dela de 72 octets : on tronque proprement plutot
    # que de laisser une erreur peu claire remonter.
    brut = mot_de_passe.encode("utf-8")[:72]
    return bcrypt.hashpw(brut, bcrypt.gensalt()).decode("utf-8")


def verifier_mot_de_passe(mot_de_passe: str, hash_stocke: str) -> bool:
    brut = mot_de_passe.encode("utf-8")[:72]
    try:
        return bcrypt.checkpw(brut, hash_stocke.encode("utf-8"))
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------

def creer_token(user: dict) -> str:
    maintenant = datetime.now(timezone.utc)
    payload = {
        "sub": str(user["id"]),
        "email": user["email"],
        "role": user["role"],
        "iat": maintenant,
        "exp": maintenant + timedelta(minutes=EXPIRATION_MINUTES),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decoder_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


# ---------------------------------------------------------------------------
# Dependances FastAPI
# ---------------------------------------------------------------------------

def utilisateur_courant(
    identifiants: HTTPAuthorizationCredentials = Depends(_bearer),
) -> dict:
    erreur_auth = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentification requise",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if identifiants is None:
        raise erreur_auth
    try:
        payload = decoder_token(identifiants.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expiree, reconnecte-toi")
    except jwt.PyJWTError:
        raise erreur_auth

    user = db.get_user_by_id(int(payload["sub"]))
    if user is None:
        raise erreur_auth
    return user


def admin_requis(user: dict = Depends(utilisateur_courant)) -> dict:
    if user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Reserve aux administrateurs",
        )
    return user
