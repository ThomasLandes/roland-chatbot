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
| Embeddings | sentence-transformers, multilingual-e5-small (local) |
| Base vectorielle | ChromaDB |
| LLM | API externe (Mistral, configurable : Anthropic, OpenAI, Groq) |
| Backend | Python 3.13, FastAPI |
| Frontend | React 19, Vite, Tailwind CSS |

## Installation

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

copy .env.example .env
# renseigner LLM_API_KEY

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
| `/health` | GET | Etat du service |
| `/ask` | POST | Question, retourne reponse et sources |
| `/admin/stats` | GET | Statistiques du corpus et d'usage |

## Profils utilisateurs

Deux profils, selectionnables dans l'interface et persistes en localStorage :

- **Utilisateur** : reponse et sources citees
- **Administrateur** : ajoute les statistiques du corpus, les chunks
  recuperes, les distances vectorielles et la requete enrichie

## Objectifs et etat d'avancement

| ID | Objectif | Etat |
|---|---|---|
| OF1 | 90% d'exactitude | En cours (phase de tests) |
| OF2 | Citation systematique des sources | Fait |
| OF3 | Refus hors perimetre avec redirection | Fait (double filtre) |
| OF4 | 2 profils utilisateurs | Fait |
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
