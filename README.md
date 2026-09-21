# Assistant Roland

Chatbot RAG repondant en francais aux questions sur la documentation
technique des instruments Roland (boites a rythmes et synthetiseurs).

Projet ESI 2 - Institut Limayrac
Eleve : Thomas LANDES - Tuteur : Stephane CEZERA

## Architecture

```
PDF Roland
   -> extraction (pypdf)
   -> chunking (1400 car., chevauchement 300)
   -> embeddings (intfloat/multilingual-e5-small, local)
   -> ChromaDB (persistant, distance cosinus)

Question
   -> enrichissement par synonymes
   -> detection du modele d'instrument
   -> recherche vectorielle filtree par metadonnees
   -> filtre de distance (seuil 0.19)
   -> generation LLM via API externe
   -> filtre INFORMATION_ABSENTE
   -> reponse + citation des sources
```

## Stack

| Composant | Technologie |
|---|---|
| Extraction PDF | pypdf |
| Embeddings | sentence-transformers, multilingual-e5-base (local) |
| Base vectorielle | ChromaDB |
| LLM | API externe (Mistral, configurable : Anthropic, OpenAI, Groq, xAI/Grok) |
| Comptes / auth | SQLite (data/users.db) + bcrypt + JWT (PyJWT) |
| Backend | Python 3.13, FastAPI |
| Frontend | React 19, Vite, Tailwind CSS |

## Installation

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

copy .env.example .env
# renseigner LLM_API_KEY et JWT_SECRET (chaine longue et aleatoire,
# par exemple : python -c "import secrets; print(secrets.token_hex(32))")

python backend/ingest.py
```

## Lancement

Backend :
```bash
cd backend
python -m uvicorn api:app --reload --port 8000
```

Frontend :
```bash
cd frontend
npm install
npm run dev
```

Interface : http://localhost:5173
Documentation API : http://localhost:8000/docs

## API

| Endpoint | Methode | Description |
|---|---|---|
| `/health` | GET | Etat du service (public) |
| `/auth/register` | POST | Creation de compte (`email`, `mot_de_passe`), retourne un token |
| `/auth/login` | POST | Connexion, retourne un token |
| `/auth/me` | GET | Utilisateur courant (necessite le token) |
| `/ask` | POST | Question, retourne reponse et sources (necessite le token) |
| `/admin/stats` | GET | Statistiques du corpus et d'usage (reserve aux admins) |

## Comptes et roles

L'acces au chatbot necessite desormais un compte (creation + connexion,
formulaire dans l'interface). L'authentification repose sur un token JWT
signe cote serveur, envoye dans l'en-tete `Authorization: Bearer <token>` ;
le role n'est jamais fourni par le client, il vient du token verifie.

- **Utilisateur** (role par defaut a l'inscription) : reponse et sources
  citees
- **Administrateur** : ajoute les statistiques du corpus, les chunks
  recuperes, les distances vectorielles et la requete enrichie

Tous les comptes crees via le formulaire sont `user`. Pour obtenir un
compte administrateur, inscris-toi normalement puis lance :

```bash
python backend/make_admin.py ton-email@exemple.com
```

Reconnecte-toi ensuite dans l'interface : un token deja emis garde le role
qu'il avait au moment de la connexion pendant 24h, il faut donc se
reconnecter apres une promotion pour que le nouveau role prenne effet.

## Objectifs et etat d'avancement

| ID | Objectif | Etat |
|---|---|---|
| OF1 | 90% d'exactitude | En cours (phase de tests) |
| OF2 | Citation systematique des sources | Fait |
| OF3 | Refus hors perimetre avec redirection | Fait (double filtre) |
| OF4 | 2 profils utilisateurs | Fait (avec authentification reelle) |
| OT1 | Architecture RAG avec ChromaDB | Fait |
| OT2 | Temps de reponse < 5s | Fait (~1.5s mesure) |
| OT3 | Taux d'hallucination < 5% | En cours |
| OT4 | Deploiement Docker | A faire |

## Reste a faire

- Enrichissement du corpus (Reference Manuals complets)
- Jeu de tests et tableau d'evaluation qualite (KPI1, KPI2)
- Conteneurisation Docker
- Documentation utilisateur

## Limites connues

Le systeme repond uniquement a partir du corpus indexe. Les informations
critiques doivent etre verifiees dans le manuel officiel Roland.
