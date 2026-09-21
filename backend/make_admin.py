"""Promeut un compte existant au role 'admin'.

Tous les comptes crees via /auth/register sont 'user' par defaut.
Pour obtenir le premier compte administrateur (ou en ajouter un autre),
il faut donc creer le compte normalement dans l'appli, puis lancer :

    python backend/make_admin.py monadresse@exemple.com

Le compte doit deja exister (il faut s'etre inscrit une fois dans
l'application avant de lancer ce script).
"""

import sys

import db


def main():
    if len(sys.argv) != 2:
        print("Usage : python backend/make_admin.py <email>")
        sys.exit(1)

    email = sys.argv[1].strip().lower()

    db.init_db()
    user = db.get_user_by_email(email)
    if user is None:
        print(f"Aucun compte avec l'email '{email}'. Inscris-toi d'abord dans l'application.")
        sys.exit(1)

    if user["role"] == "admin":
        print(f"'{email}' est deja administrateur.")
        return

    db.set_role(email, "admin")
    print(f"'{email}' est maintenant administrateur.")


if __name__ == "__main__":
    main()
