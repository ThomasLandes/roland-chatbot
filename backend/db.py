"""Acces a la base SQLite des utilisateurs (comptes, roles).

Base locale, fichier unique : data/users.db (cree automatiquement au
demarrage de l'API). Volontairement simple : sqlite3 de la stdlib,
pas d'ORM, une seule table.
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
DB_FILE = ROOT / "data" / "users.db"

ROLES_VALIDES = {"user", "admin"}


def _connexion():
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Cree la table users si elle n'existe pas encore."""
    conn = _connexion()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                email         TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role          TEXT NOT NULL DEFAULT 'user',
                created_at    TEXT NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def _row_to_dict(row):
    if row is None:
        return None
    return {
        "id": row["id"],
        "email": row["email"],
        "password_hash": row["password_hash"],
        "role": row["role"],
        "created_at": row["created_at"],
    }


def create_user(email, password_hash, role="user"):
    """Cree un utilisateur. Leve sqlite3.IntegrityError si l'email existe deja."""
    email = email.strip().lower()
    if role not in ROLES_VALIDES:
        role = "user"
    conn = _connexion()
    try:
        cur = conn.execute(
            "INSERT INTO users (email, password_hash, role, created_at) "
            "VALUES (?, ?, ?, ?)",
            (email, password_hash, role, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
        return get_user_by_id(cur.lastrowid)
    finally:
        conn.close()


def get_user_by_email(email):
    conn = _connexion()
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE email = ?", (email.strip().lower(),)
        ).fetchone()
        return _row_to_dict(row)
    finally:
        conn.close()


def get_user_by_id(user_id):
    conn = _connexion()
    try:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return _row_to_dict(row)
    finally:
        conn.close()


def set_role(email, role):
    """Change le role d'un utilisateur existant. Retourne True si applique."""
    if role not in ROLES_VALIDES:
        raise ValueError(f"Role invalide : {role!r} (attendu : {sorted(ROLES_VALIDES)})")
    conn = _connexion()
    try:
        cur = conn.execute(
            "UPDATE users SET role = ? WHERE email = ?", (role, email.strip().lower())
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def count_admins():
    conn = _connexion()
    try:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM users WHERE role = 'admin'"
        ).fetchone()
        return row["n"]
    finally:
        conn.close()


def list_users():
    """Retourne tous les comptes, tries par date de creation (sans le hash)."""
    conn = _connexion()
    try:
        rows = conn.execute(
            "SELECT id, email, role, created_at FROM users ORDER BY created_at ASC"
        ).fetchall()
        return [
            {"id": r["id"], "email": r["email"], "role": r["role"], "created_at": r["created_at"]}
            for r in rows
        ]
    finally:
        conn.close()


def delete_user(user_id):
    """Supprime un compte. Retourne True si un compte a bien ete supprime."""
    conn = _connexion()
    try:
        cur = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()
