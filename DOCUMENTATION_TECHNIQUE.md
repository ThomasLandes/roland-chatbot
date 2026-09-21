# Documentation technique

**Assistant Roland — Chatbot RAG sur documentation technique**

| | |
|---|---|
| Projet | Chatbot Intelligent basé sur RAG |
| Élève | Thomas LANDES |
| Tuteur | Stéphane CEZERA |
| Établissement | Institut Limayrac, ESI 2, Titre RNCP niveau 7 |
| Période | Février 2026 à Septembre 2026 |
| Version du document | 1.1 |

---

## Sommaire

1. [Objet du document](#1-objet-du-document)
2. [Contexte et périmètre](#2-contexte-et-périmètre)
3. [Architecture générale](#3-architecture-générale)
4. [Choix technologiques et justifications](#4-choix-technologiques-et-justifications)
5. [Pipeline d'ingestion](#5-pipeline-dingestion)
6. [Pipeline de génération augmentée](#6-pipeline-de-génération-augmentée)
7. [API REST](#7-api-rest)
8. [Interface web](#8-interface-web)
9. [Gestion des profils utilisateurs](#9-gestion-des-profils-utilisateurs)
10. [Traçabilité et journalisation](#10-traçabilité-et-journalisation)
11. [Installation et exécution](#11-installation-et-exécution)
12. [Structure du dépôt](#12-structure-du-dépôt)
13. [Paramètres de configuration](#13-paramètres-de-configuration)
14. [Résultats mesurés](#14-résultats-mesurés)
15. [Limites connues et incidents documentés](#15-limites-connues-et-incidents-documentés)
16. [Considérations légales et éthiques](#16-considérations-légales-et-éthiques)
17. [Reste à faire](#17-reste-à-faire)

---

## 1. Objet du document

Ce document décrit l'architecture, les choix techniques et le fonctionnement interne du chatbot. Il s'adresse à un développeur devant reprendre, maintenir ou faire évoluer le projet, ainsi qu'au jury d'évaluation.

La documentation destinée à l'utilisateur final fait l'objet d'un document séparé : `GUIDE_UTILISATEUR.md`.

---

## 2. Contexte et périmètre

### 2.1 Besoin

Roland Corporation distribue ses instruments électroniques avec une documentation technique volumineuse. La prise en main d'une boîte à rythmes ou d'un synthétiseur suppose de naviguer dans des manuels de plusieurs dizaines de pages pour retrouver une procédure précise. Cette friction pénalise particulièrement les utilisateurs débutants.

L'objectif est de fournir un assistant conversationnel francophone qui répond à une question de prise en main en citant systématiquement le passage du manuel dont provient l'information.

### 2.2 Périmètre retenu

| Inclus | Exclu |
|---|---|
| Questions/réponses sur la documentation Roland | Conversations multi-tours |
| Citation systématique des sources | Contexte conversationnel |
| Interface web simple | Application mobile |
| Refus explicite des questions hors périmètre | LLM auto-hébergé |
| Deux profils utilisateurs, authentification réelle | UX/UI avancée |
| Base vectorielle ChromaDB | Multilingue |
| API LLM externe | |

La gestion de documents décrite en section 7.4 et 8 (upload, suppression, réindexation à chaud depuis l'interface admin) va au-delà du périmètre initial, qui excluait la mise à jour dynamique du corpus. Elle est présentée comme un bonus construit une fois le périmètre de base sécurisé, pas comme un engagement du cahier des charges.

L'absence de contexte conversationnel est un choix assumé : chaque question est traitée indépendamment. Cela simplifie l'architecture et évite une classe entière de problèmes de dérive contextuelle, au prix de l'impossibilité de poser une question de suivi du type « et ensuite ? ».

---

## 3. Architecture générale

Le système suit une architecture RAG (Retrieval Augmented Generation) en deux temps distincts : une phase d'indexation hors ligne, exécutée une fois, et une phase d'interrogation en ligne, exécutée à chaque question.

### 3.1 Phase d'indexation (hors ligne)

```
PDF Roland
    │
    ▼
Extraction texte (pypdf)
    │  conservation de la correspondance offset → page
    ▼
Nettoyage (normalisation espaces et sauts de ligne)
    │
    ▼
Découpage en chunks (1400 caractères, chevauchement 300)
    │  découpage aligné sur les sauts de ligne
    ▼
Vectorisation (multilingual-e5-base, exécution locale)
    │  préfixe "passage:" imposé par le modèle
    ▼
ChromaDB (persistant, distance cosinus)
    métadonnées : source, page, modèle d'instrument
```

### 3.2 Phase d'interrogation (en ligne)

```
Question utilisateur
    │
    ▼
Enrichissement par synonymes métier
    │
    ▼
Détection du modèle d'instrument mentionné
    │
    ▼
Vectorisation de la requête (préfixe "query:")
    │
    ▼
Recherche vectorielle
    │  filtrage par métadonnée "modele" si un instrument est détecté
    │  (dans ce cas, pool élargi à 50 candidats)
    ▼
Reclassement lexical (si un instrument est détecté)
    │  bonus de tri pour les chunks contenant les mots de la question
    │  (la distance affichée n'est pas modifiée)
    ▼
Conservation des 15 meilleurs chunks
    ▼
FILTRE 1 : distance minimale parmi les chunks retenus > 0.19 ?
    │  oui → refus, redirection support Roland
    ▼  non
Construction du prompt (contexte + question)
    │
    ▼
Appel LLM via API externe
    │
    ▼
FILTRE 2 : la réponse contient INFORMATION_ABSENTE ?
    │  oui → refus, redirection support Roland
    ▼  non
Extraction des marqueurs [Source N] cités
    │
    ▼
Réponse + sources effectivement utilisées
```

### 3.3 Choix architectural central : embeddings locaux, génération distante

Les deux étapes coûteuses d'un système RAG sont la vectorisation et la génération. Le projet les traite différemment.

La **vectorisation s'exécute localement**, sur CPU, avec un modèle de 470 Mo. Elle représente le volume d'appels le plus important, puisqu'elle est appliquée à chaque chunk lors de l'indexation puis à chaque requête. La faire tourner en local supprime tout coût variable et rend l'indexation reproductible sans connexion ni clé API.

La **génération passe par une API externe**, conformément au périmètre défini. Elle ne représente qu'un appel par question. Le cahier des charges exclut explicitement le LLM auto-hébergé, et l'expérience confirme ce choix : la tâche consiste à lire des extraits techniques et à produire une réponse structurée en français sans inventer, ce qu'un petit modèle local exécuté sur poste de développement ne fait pas de manière fiable dans le budget temps de 5 secondes fixé par l'objectif OT2.

---

## 4. Choix technologiques et justifications

| Composant | Technologie retenue | Justification |
|---|---|---|
| Extraction PDF | `pypdf` | Les manuels Roland sont des PDF avec couche texte native. Un contrôle préalable a mesuré un ratio supérieur à 200 caractères par page sur l'ensemble du corpus, ce qui écarte le recours à l'OCR et évite la dépendance à Tesseract. |
| Embeddings | `intfloat/multilingual-e5-base` | Modèle multilingue (768 dimensions) capable de rapprocher une requête française d'un passage technique, y compris en anglais. Cette propriété est indispensable : une partie de la documentation Roland n'existe qu'en anglais. Remplace la version `-small` (384 dimensions) initialement retenue : des embeddings plus discriminants sur des paragraphes voisins d'un même manuel, au prix d'un modèle un peu plus lourd (transfert unique au premier lancement). |
| Base vectorielle | ChromaDB | Mode persistant sur disque, aucun serveur à administrer, filtrage natif par métadonnées. Imposé par le cahier des charges. |
| LLM | API externe, `mistral-small-latest` | Le code encapsule quatre fournisseurs interchangeables (Anthropic, OpenAI, Groq, Mistral) derrière une fonction unique. Changer de fournisseur consiste à modifier une variable d'environnement. |
| Backend | Python 3.13, FastAPI | Documentation OpenAPI générée automatiquement, validation des entrées par Pydantic, chargement du modèle au démarrage plutôt qu'à chaque requête. |
| Frontend | React 19, Vite, Tailwind CSS | Tailwind est chargé par CDN afin d'éviter une configuration PostCSS sans valeur ajoutée pour un projet de cette taille. |

### 4.1 Pourquoi RAG plutôt que fine-tuning

Le cahier des charges de l'école évoque les deux approches. Le RAG a été retenu pour trois raisons.

D'abord la **traçabilité**. Un modèle affiné produit une réponse sans pouvoir désigner le passage dont elle provient. L'objectif OF2 impose la citation systématique de la source, ce qu'un système de récupération fournit par construction puisque les extraits transitent explicitement dans le prompt.

Ensuite la **maîtrise des hallucinations**. Le fine-tuning encode la connaissance dans les poids du modèle, où elle se mélange à ses connaissances générales. Le RAG maintient une séparation nette entre ce que le modèle sait et ce qu'il a le droit d'utiliser, ce qui rend possible une consigne de refus explicite.

Enfin le **coût de mise à jour**. Ajouter un manuel au corpus consiste à déposer un PDF et à relancer un script. Le même ajout par fine-tuning suppose la constitution d'un jeu annoté et un réentraînement.

---

## 5. Pipeline d'ingestion

Fichier : `backend/ingest.py`

### 5.1 Extraction avec conservation de la pagination

L'extraction ne se contente pas de concaténer le texte. Elle construit en parallèle une table de correspondance entre la position d'un caractère dans le texte global et le numéro de page dont il provient.

```python
def read_pdf(path):
    reader = PdfReader(path)
    parts, offsets = [], []
    cursor = 0
    for i, page in enumerate(reader.pages, start=1):
        txt = clean(page.extract_text() or "")
        if not txt:
            continue
        offsets.append((cursor, i))
        parts.append(txt)
        cursor += len(txt) + 1
    return "\n".join(parts), offsets
```

Cette table est ce qui permet, en bout de chaîne, d'afficher à l'utilisateur « TR-1000, page 27 » plutôt qu'un simple nom de fichier. Sans elle, la citation perdrait l'essentiel de son intérêt : la possibilité de vérifier dans le manuel officiel.

### 5.2 Découpage aligné sur les sauts de ligne

Une première implémentation découpait le texte tous les 800 caractères sans considération pour son contenu. Le contrôle des chunks produits a révélé des morceaux commençant au milieu d'un mot, du type `outon [ENTER].` pour `bouton [ENTER].`, et des procédures numérotées amputées de leurs premières étapes.

La version retenue accumule des lignes entières jusqu'à atteindre la taille cible, puis reporte la fin du tampon dans le chunk suivant pour assurer le chevauchement.

```python
CHUNK_SIZE = 1400
OVERLAP = 300
```

Le passage de 800 à 1400 caractères répond à la nature du corpus : les procédures Roland sont des séquences de 4 à 8 étapes numérotées qu'il faut conserver entières dans un même chunk pour que le modèle puisse les restituer sans les compléter lui-même.

### 5.3 Vectorisation

Le modèle e5 impose une convention de préfixage qu'il faut respecter sous peine de dégrader significativement la qualité de la recherche : les documents indexés sont préfixés par `passage:`, les requêtes par `query:`.

```python
vectors = model.encode(
    [f"passage: {c['text']}" for c in chunks],
    batch_size=32,
    normalize_embeddings=True,
).tolist()
```

La normalisation des vecteurs, combinée à la configuration `hnsw:space: cosine` de la collection, garantit que les distances retournées sont comparables entre elles et donc exploitables comme seuil de décision.

### 5.4 Métadonnées

Chaque chunk est indexé avec trois métadonnées :

| Clé | Contenu | Usage |
|---|---|---|
| `source` | Nom du fichier PDF | Affichage de la citation |
| `page` | Numéro de page d'origine | Affichage de la citation, vérification manuelle |
| `modele` | Modèle d'instrument, déduit du nom de fichier | Filtrage de la recherche |

Le champ `modele` est extrait du nom de fichier avant le premier caractère de soulignement. Cette convention impose une règle de nommage stricte du corpus, documentée en section 11.

### 5.5 Idempotence

Le script supprime et recrée la collection à chaque exécution. Il peut donc être relancé sans précaution après tout ajout de document ou modification des paramètres de découpage.

---

## 6. Pipeline de génération augmentée

Fichier : `backend/rag.py`

### 6.1 Enrichissement de la requête

Un décalage de vocabulaire a été identifié entre la formulation naturelle d'une question et la terminologie des manuels. Un utilisateur demande comment « sauvegarder » un pattern, là où le manuel décrit une opération nommée `WRITE`.

Un dictionnaire de synonymes métier étend la requête avant vectorisation :

```python
SYNONYMES = {
    "sauvegarder": "sauvegarder enregistrer write memoriser",
    "enregistrer": "enregistrer write sauvegarder",
    "supprimer": "supprimer effacer clear delete",
    "connecter": "connecter brancher synchroniser midi",
    "regler": "regler parametrer configurer setting",
    "régler": "regler parametrer configurer setting",
}
```

Le procédé est volontairement simple. Il traite les cas les plus fréquents sans introduire de dépendance supplémentaire ni de latence mesurable.

### 6.2 Détection du modèle et filtrage

La recherche vectorielle seule ne distingue pas les instruments. La question « comment sauvegarder un pattern sur le TR-1000 » est sémantiquement proche de passages du TB-03 et du JU-06A, qui décrivent des opérations analogues sur d'autres appareils. Les mesures ont montré des distances de 0.127 pour le bon document contre 0.128 et 0.134 pour les autres, un écart trop faible pour discriminer.

La solution exploite le filtrage par métadonnées de ChromaDB :

```python
modele = detecter_modele(question)
kwargs = {"query_embeddings": [vec], "n_results": n}
if modele:
    kwargs["where"] = {"modele": modele}
    kwargs["n_results"] = max(n, N_ELARGI)   # N_ELARGI = 50
```

Lorsque la question mentionne explicitement un instrument, la recherche est restreinte à ses documents. Sinon elle porte sur l'ensemble du corpus. La comparaison est insensible à la casse et aux tirets, de sorte que `TR-1000`, `tr1000` et `TR 1000` sont reconnus.

### 6.3 Reclassement lexical

Le jeu de tests constitué (section 14) a mis en évidence un cas où le passage attendu existait bien dans le corpus mais ressortait très loin dans le classement purement vectoriel (38ᵉ position sur 100 candidats), derrière des passages du même document évoquant un vocabulaire voisin sans contenir la procédure recherchée. Un premier correctif a porté sur le découpage (chunk plus petit, coupure nette aux titres de section) : il a bien isolé le passage visé mais a fait empirer son rang (55ᵉ) et cassé un cas qui fonctionnait jusque-là sur un autre document. Le découpage a donc été restauré à sa version d'origine (1400/300, section 13.2), et le correctif a été déplacé côté recherche.

Quand un instrument est détecté, le pool de candidats est élargi à 50 (recherche peu coûteuse car filtrée sur un seul document). Chaque candidat reçoit ensuite un bonus de tri s'il contient littéralement des mots de la question (hors mots vides, accents ignorés) :

```python
BONUS_PAR_MOT_CLE = 0.03
BONUS_MAX = 0.09

score = distance - min(hits * BONUS_PAR_MOT_CLE, BONUS_MAX)
```

Les 50 candidats sont triés par ce score puis tronqués aux 15 premiers. La distance affichée à l'utilisateur et utilisée pour le filtre de refus (section 6.4) reste la distance vectorielle brute, non modifiée par le bonus : le score ne sert qu'au tri, jamais à la décision de refus ni à l'affichage. Sur le cas diagnostiqué, ce reclassement a fait remonter le passage attendu de la 38ᵉ à la 8ᵉ position.

### 6.4 Double filtre de refus

L'objectif OF3 impose le refus explicite des questions hors périmètre. Deux mécanismes indépendants y concourent.

**Filtre 1, seuil de distance.** Si la meilleure distance parmi les chunks retenus dépasse 0.19, le système refuse sans appeler le LLM. Ce seuil a été calibré empiriquement : les questions légitimes du corpus se situent entre 0.116 et 0.155, une question manifestement hors sujet remonte à 0.209. La valeur de 0.19 place la frontière entre les deux populations. Le filtre compare le **minimum** des distances brutes parmi les chunks renvoyés, et non celle du premier chunk de la liste : depuis le reclassement lexical (section 6.3), l'ordre d'affichage peut différer de l'ordre par distance pure. L'économie d'un appel API est un effet secondaire appréciable, mais l'intérêt principal est d'obtenir un comportement déterministe, indépendant du modèle de génération.

**Filtre 2, aveu du modèle.** Le prompt système impose au LLM d'écrire exactement `INFORMATION_ABSENTE` lorsque les extraits fournis ne contiennent pas la réponse. Ce marqueur est intercepté avant affichage et remplacé par le message de redirection.

Le premier filtre attrape les questions hors domaine. Le second attrape les questions dans le domaine dont la réponse ne figure pas dans le corpus indexé, cas que la distance seule ne permet pas de détecter. La cause du refus est conservée dans la réponse (`cause: "distance"` ou `cause: "llm"`), ce qui a permis de diagnostiquer précisément les incidents décrits en section 15.

### 6.5 Prompt système

Le prompt encadre strictement le comportement du modèle :

```
1. Reponds UNIQUEMENT a partir des extraits de documentation fournis.
2. Chaque etape que tu ecris doit etre presente MOT POUR MOT dans un extrait.
   Si tu ne retrouves pas une etape dans les extraits, ne l'ecris pas.
3. Si les extraits ne contiennent pas la procedure complete, ecris exactement :
   INFORMATION_ABSENTE
4. Ne complete jamais une procedure partielle avec tes connaissances generales
   sur les instruments Roland ou sur d'autres appareils.
5. Cite chaque etape avec le marqueur [Source N] correspondant a l'extrait exact.
6. Reponds en francais, avec des etapes numerotees.
7. Reste concis.
```

Les règles 2 et 4 sont les plus importantes. Elles répondent à un incident d'hallucination observé et documenté en section 15, où le modèle avait complété une procédure incomplète avec des connaissances générales sur les instruments Roland.

### 6.6 Extraction des sources citées

Les quinze chunks récupérés sont numérotés et injectés dans le prompt. Le modèle n'en utilise généralement qu'une fraction. Les afficher tous noierait la source réelle dans le bruit.

Une expression régulière extrait les marqueurs effectivement présents dans la réponse, et seules les sources correspondantes sont affichées :

```python
citees = set(int(n) for n in re.findall(r"Source\s+(\d+)", texte))
```

Le motif est volontairement permissif afin de capturer les variantes de formatage, notamment `[Source 2, Source 8]` que le modèle produit lorsqu'une étape s'appuie sur plusieurs extraits. Un garde-fou affiche l'ensemble des sources si aucun marqueur n'est détecté, plutôt que de laisser une réponse sans aucune citation.

### 6.7 Abstraction du fournisseur LLM

Une fonction unique encapsule les fournisseurs supportés. Anthropic utilise un format de requête distinct, les autres partagent le format compatible OpenAI.

```python
endpoints = {
    "openai":  ("https://api.openai.com/v1/chat/completions", "gpt-4o-mini"),
    "groq":    ("https://api.groq.com/openai/v1/chat/completions", "llama-3.3-70b-versatile"),
    "mistral": ("https://api.mistral.ai/v1/chat/completions", "mistral-small-latest"),
    "grok":    ("https://api.x.ai/v1/chat/completions", "grok-4.6"),
}
```

Cette abstraction a une valeur opérationnelle directe : elle permet de comparer plusieurs modèles sur le même jeu de tests en changeant une seule variable d'environnement, sans toucher au code.

---

## 7. API REST

Fichier : `backend/api.py`

L'API est documentée automatiquement par FastAPI et explorable à l'adresse `http://localhost:8000/docs`.

### 7.1 Chargement au démarrage

Le modèle d'embeddings et la connexion ChromaDB sont initialisés une fois au démarrage du serveur, pas à chaque requête.

```python
@app.on_event("startup")
def startup():
    rag._init()
```

L'impact est déterminant sur l'objectif OT2. En exécution ligne de commande, une réponse prend environ 7 secondes, dont l'essentiel est consacré au chargement du modèle. Via l'API, le temps mesuré descend à 1.56 seconde.

### 7.2 Authentification

Fichiers : `backend/auth.py`, `backend/db.py`. Les profils déclaratifs de la version initiale (section 9) ont été remplacés par une authentification réelle : comptes stockés en base SQLite (`data/users.db`), mots de passe hashés avec bcrypt, sessions portées par un JWT signé (`Authorization: Bearer <token>`), sans état côté serveur.

#### `POST /auth/register`

Crée un compte de rôle `user` (email + mot de passe, 8 caractères minimum). Retourne un token. Un compte `admin` s'obtient en promouvant un compte existant via `backend/make_admin.py` ou `PATCH /admin/users/{id}/role`, jamais à l'inscription.

#### `POST /auth/login`

```json
{ "email": "t.landes@test.fr", "mot_de_passe": "..." }
```

```json
{ "access_token": "eyJ...", "token_type": "bearer", "email": "t.landes@test.fr", "role": "admin" }
```

#### `GET /auth/me`

Retourne l'identité et le rôle associés au token fourni.

### 7.3 Chatbot

#### `GET /health`

Vérification de disponibilité, sans authentification.

```json
{ "status": "ok", "provider": "mistral" }
```

#### `POST /ask`

Nécessite un token valide (`Authorization: Bearer <token>`). Le rôle n'est plus déclaré par le client : il est lu depuis le token vérifié côté serveur, ce qui empêche un utilisateur de se l'attribuer lui-même.

```json
{ "question": "Comment sauvegarder un pattern sur le TR-1000 ?" }
```

Réponse pour le rôle `user` :

```json
{
  "reponse": "1. Appuyez sur ... [Source 2]",
  "sources": [
    { "n": 2, "source": "TR-1000_fra02_W.pdf", "page": 27, "distance": 0.127 }
  ],
  "hors_perimetre": false,
  "duree": 1.56
}
```

Le rôle `admin` reçoit en supplément un objet `debug` contenant la cause du refus le cas échéant, le modèle d'instrument détecté, la requête après enrichissement, et l'intégralité des chunks récupérés avec leur distance et un extrait de 300 caractères.

Codes d'erreur : `400` pour une question vide, `401` si le token est absent, invalide ou expiré, `502` en cas d'échec de l'appel au fournisseur LLM.

#### `GET /admin/stats`

Réservé au rôle `admin`. Statistiques du corpus et d'usage.

```json
{
  "documents": 4,
  "chunks_total": 275,
  "chunks_par_document": {
    "TR-1000_fra02_W.pdf": 96,
    "JU-06A_fra02_W.pdf": 28,
    "TB-03_fra03_W.pdf": 27,
    "SH-01A_fra04_W.pdf": 22
  },
  "config": {
    "provider": "mistral",
    "seuil_hors_perimetre": 0.19,
    "n_results": 15
  },
  "usage": {
    "questions_posees": 5,
    "refus": 5,
    "duree_moyenne_s": 1.01
  }
}
```

Cet endpoint alimente directement le suivi des indicateurs KPI3 (temps de réponse) et KPI4 (couverture du corpus).

### 7.4 Gestion des utilisateurs (admin)

Réservé au rôle `admin`. `GET /admin/users` liste les comptes (sans le hash de mot de passe). `PATCH /admin/users/{id}/role` change le rôle d'un compte. `DELETE /admin/users/{id}` supprime un compte. Deux garde-fous protègent le système contre un blocage : un administrateur ne peut ni modifier son propre rôle ni supprimer son propre compte depuis cette interface, et le dernier compte `admin` du système ne peut être ni rétrogradé ni supprimé.

### 7.5 Gestion des documents (admin)

Fichier : `backend/ingest.py` (fonction `reindexer`), exposé par `backend/api.py`. Ajouté après le périmètre initial (voir la note de la section 2.2) pour éviter de repasser par une ligne de commande à chaque évolution du corpus.

| Endpoint | Rôle |
|---|---|
| `GET /admin/documents` | Liste les PDF présents dans `data/pdf/` avec leur taille |
| `POST /admin/documents/upload` | Dépose un nouveau PDF (multipart, 30 Mo max, extension `.pdf` imposée, nom de fichier assaini) |
| `DELETE /admin/documents/{nom}` | Supprime le fichier PDF du disque |
| `POST /admin/documents/reindex` | Relance l'indexation complète, exécutée dans un threadpool pour ne pas geler le serveur |
| `GET /admin/documents/reindex/status` | Avancement de la réindexation en cours (pour la barre de progression du frontend, en interrogation périodique) |

Deux points méritent d'être notés. D'abord, la suppression d'un PDF retire le fichier mais pas ses chunks de ChromaDB : ceux-ci ne disparaissent qu'à la prochaine réindexation, qui reconstruit la collection entière à partir des PDF présents à ce moment-là. C'est volontairement simple plutôt que de gérer une suppression ciblée dans la base vectorielle. Ensuite, la réindexation déclenchée à chaud réutilise le même `chromadb.PersistentClient` que celui utilisé pour répondre aux questions (`rag.get_client()`) : un incident réel a montré qu'une seconde instance de client pointée sur le même dossier peut garder une vue périmée de la collection après un `delete_collection()`/`create_collection()`, même une fois « rafraîchie » via `get_collection()` (voir section 15).

### 7.6 CORS

Le middleware CORS autorise toutes les origines. Cette configuration est acceptable en développement, le frontend et le backend étant servis sur des ports distincts. Elle devra être restreinte avant toute exposition publique.

---

## 8. Interface web

Fichier : `frontend/src/App.jsx`

L'interface tient dans un composant unique. Ce choix est délibéré : le périmètre exclut l'UX/UI avancée, et une découpe en composants n'apporterait aucune lisibilité supplémentaire à cette échelle.

### 8.1 Fonctionnalités

- Écran de connexion / inscription, préalable à l'accès au chatbot (voir section 9)
- Zone de conversation avec distinction visuelle entre les messages de l'utilisateur et ceux de l'assistant
- Trois questions d'exemple cliquables sur l'écran d'accueil, utiles pour la démonstration
- Affichage des sources sous chaque réponse, avec le nom du document et le numéro de page
- Codage couleur du type de réponse : neutre pour une réponse normale, orange pour un refus hors périmètre, rouge pour une erreur technique
- Indicateur de chargement pendant l'appel
- Défilement automatique vers le dernier message
- Affichage du temps de réponse
- Avertissement permanent sur les limites du système en pied de page

### 8.2 Panneau d'administration « Documents »

Visible uniquement pour le rôle `admin`. Liste les PDF indexés avec leur taille, propose l'ajout d'un nouveau document (glisser-déposer ou sélection), sa suppression, et un bouton « Réindexer ».

Le déclenchement d'une réindexation affiche une barre de progression alimentée par `GET /admin/documents/reindex/status`, interrogée à intervalle régulier tant que `en_cours` vaut vrai côté serveur. Sans ce retour visuel, une réindexation (plusieurs dizaines de secondes sur le corpus actuel) donnait l'impression d'une interface figée. Le composant ne bloque jamais la fin de l'appel `POST /admin/documents/reindex` : la barre disparaît dès que le statut serveur repasse à « terminé », y compris en cas d'erreur (le compteur de progression est remis à zéro dans un bloc `finally` côté serveur).

Un ajout ou une suppression de document ne prend effet dans les réponses du chatbot qu'après un clic sur « Réindexer » : déposer ou retirer un fichier ne modifie que le disque, pas encore la base vectorielle interrogée par `/ask`.

### 8.3 Gestion des erreurs

Toute défaillance de l'API est capturée et affichée sous forme de message d'erreur dans le fil de conversation. L'interface ne se bloque jamais et ne présente jamais de page blanche, ce qui est une garantie utile en situation de démonstration.

---

## 9. Gestion des profils utilisateurs

L'objectif OF4 demande la gestion de deux profils. Le cahier des charges ne détaille pas le mécanisme d'authentification ; une première version s'appuyait sur un sélecteur déclaratif côté client, explicitement documentée comme non sécurisée. Cette version a été remplacée par une authentification réelle (section 7.2) : création de compte, connexion par email et mot de passe, rôle vérifié côté serveur à chaque appel.

| Rôle | Accès |
|---|---|
| `user` | Réponse, sources citées avec document et page, temps de réponse |
| `admin` | Idem, plus le bandeau de statistiques du corpus, les distances vectorielles associées à chaque source, un panneau dépliable listant les chunks récupérés avec leur extrait, le modèle d'instrument détecté, la requête enrichie et la cause du refus le cas échéant, la gestion des comptes utilisateurs et le panneau de gestion des documents (section 8.2) |

Le rôle `admin` n'a pas qu'une fonction de démonstration. Il constitue l'outil de diagnostic principal du système : il permet de déterminer, face à une réponse insatisfaisante, si le problème vient de la récupération des chunks ou de la génération. Plusieurs incidents décrits en section 15 ont été diagnostiqués grâce à lui.

Le premier compte administrateur ne peut pas s'auto-désigner à l'inscription (`POST /auth/register` crée toujours un compte `user`) : il se crée soit via le script `backend/make_admin.py`, soit en promouvant un compte existant depuis un compte admin déjà en place. Le dernier administrateur du système ne peut être ni rétrogradé ni supprimé, pour éviter de verrouiller l'accès au panneau d'administration.

Le token JWT expire après 24 heures ; au-delà, l'utilisateur doit se reconnecter. Le mot de passe n'est jamais stocké en clair (hash bcrypt) ni renvoyé par l'API après inscription.

---

## 10. Traçabilité et journalisation

Chaque requête est enregistrée dans `data/logs.csv` :

| Colonne | Contenu |
|---|---|
| `date` | Horodatage ISO 8601 |
| `question` | Question posée |
| `hors_perimetre` | Booléen |
| `cause` | `distance`, `llm` ou vide |
| `duree_s` | Temps de traitement en secondes |
| `nb_sources` | Nombre de sources citées |

Ce fichier répond à l'output « Logs » du SIPOC et fournit la matière brute du calcul des indicateurs de suivi. Sa lecture agrégée est exposée par l'endpoint `/admin/stats`.

Le format CSV a été préféré à une base de données : il est directement exploitable dans un tableur pour produire le tableau d'évaluation qualité attendu en livrable.

Une base SQLite distincte, `data/users.db`, stocke les comptes (email, hash bcrypt du mot de passe, rôle, date de création). Elle ne journalise pas l'activité : c'est un annuaire de comptes, pas un journal. Les implications RGPD de ce stockage sont traitées en section 16.2.

---

## 11. Installation et exécution

### 11.1 Prérequis

- Python 3.10 ou supérieur
- Node.js 20 LTS ou supérieur
- Une clé API auprès d'un des fournisseurs supportés

### 11.2 Installation

```bash
git clone https://github.com/ThomasLandes/roland-chatbot.git
cd roland-chatbot

python -m venv .venv
.venv\Scripts\Activate.ps1        # Windows
source .venv/bin/activate         # macOS et Linux

pip install -r requirements.txt

copy .env.example .env            # puis renseigner LLM_API_KEY
```

### 11.3 Constitution du corpus

Les manuels ne sont pas versionnés dans le dépôt. Ils se téléchargent depuis le centre de support Roland et se déposent dans `data/pdf/`.

**Convention de nommage obligatoire.** Le modèle d'instrument est déduit du nom de fichier, tronqué au premier caractère de soulignement. Le fichier `TR-1000_fra02_W.pdf` produit ainsi le modèle `TR-1000`. Le non-respect de cette convention désactive silencieusement le filtrage par instrument.

La liste `MODELES` de `backend/rag.py` doit être tenue à jour avec les instruments présents dans le corpus.

### 11.4 Indexation

```bash
python backend/ingest.py
```

Le premier lancement télécharge le modèle d'embeddings, soit environ 470 Mo. Le script affiche le nombre de chunks produits par document et le total. Il est idempotent et peut être relancé après tout ajout au corpus.

### 11.5 Lancement

Deux terminaux sont nécessaires.

Backend :
```bash
cd backend
python -m uvicorn api:app --reload --port 8000
```

Attendre le message `API prete.` avant de solliciter le service.

Frontend :
```bash
cd frontend
npm install
npm run dev
```

| Service | Adresse |
|---|---|
| Interface | http://localhost:5173 |
| API | http://localhost:8000 |
| Documentation OpenAPI | http://localhost:8000/docs |

### 11.6 Scripts de contrôle

| Script | Fonction |
|---|---|
| `backend/check_pdf.py` | Vérifie que les PDF comportent une couche texte exploitable et signale ceux qui nécessiteraient un OCR |
| `backend/test_search.py` | Teste la recherche vectorielle seule, sans appel LLM, et affiche les distances |
| `backend/test_api.py` | Teste les endpoints et les deux rôles |
| `backend/make_admin.py` | Promeut un compte existant au rôle `admin` en ligne de commande |
| `backend/evaluer.py` | Rejoue le jeu de tests (`eval_questions.json`) contre l'API, calcule KPI1/KPI2/KPI3, écrit `eval_results.json` et `eval_results.md` (section 14) |

Le mode debug de `rag.py` affiche les chunks récupérés et la réponse brute du modèle :

```bash
python backend/rag.py --debug "Comment regler le tempo sur le TR-1000 ?"
```

---

## 12. Structure du dépôt

```
roland-chatbot/
├── backend/
│   ├── ingest.py           Extraction, découpage, vectorisation, indexation
│   ├── rag.py              Recherche, reclassement, filtres, appel LLM, citation
│   ├── api.py              API FastAPI, authentification, journalisation
│   ├── auth.py             Hash des mots de passe, JWT, dépendances FastAPI
│   ├── db.py                Accès à la base SQLite des comptes utilisateurs
│   ├── make_admin.py       Promotion d'un compte au rôle admin (CLI)
│   ├── check_pdf.py        Contrôle de la couche texte des PDF
│   ├── test_search.py      Test de la recherche vectorielle
│   ├── test_api.py         Test des endpoints
│   ├── evaluer.py          Jeu de tests automatisé (KPI1/KPI2/KPI3)
│   └── eval_questions.json Questions et mots-clés attendus du jeu de tests
├── frontend/
│   ├── index.html          Point d'entrée, chargement de Tailwind
│   └── src/
│       ├── main.jsx        Montage React
│       └── App.jsx         Interface complète (connexion, chat, admin)
├── data/
│   ├── pdf/                Corpus source, non versionné
│   ├── chroma/             Base vectorielle, non versionnée
│   ├── users.db            Comptes utilisateurs (email, hash, rôle), non versionné
│   └── logs.csv            Journal des requêtes, non versionné
├── .env                    Configuration locale, non versionnée
├── .env.example            Modèle de configuration
├── .gitignore
├── requirements.txt
├── README.md
├── DOCUMENTATION_TECHNIQUE.md
└── GUIDE_UTILISATEUR.md
```

Le fichier `.env` et le dossier `.venv/` sont exclus du versionnement. La clé API ne doit en aucun cas être committée.

---

## 13. Paramètres de configuration

### 13.1 Variables d'environnement

| Variable | Valeurs | Défaut |
|---|---|---|
| `LLM_PROVIDER` | `mistral`, `anthropic`, `openai`, `groq`, `grok` | `mistral` |
| `LLM_API_KEY` | Clé du fournisseur retenu | Aucun |
| `JWT_SECRET` | Chaîne longue et aléatoire, signature des tokens de session | Généré aléatoirement au démarrage si absent (avertissement affiché ; tous les tokens deviennent invalides au redémarrage suivant) |

### 13.2 Paramètres d'ingestion

Définis dans `backend/ingest.py`. Toute modification impose une réindexation complète.

| Paramètre | Valeur | Effet |
|---|---|---|
| `CHUNK_SIZE` | 1400 | Taille cible d'un chunk. Une valeur plus faible fragmente les procédures, une valeur plus élevée dilue la pertinence de la recherche. |
| `OVERLAP` | 300 | Chevauchement entre chunks consécutifs, destiné à éviter qu'une information soit coupée à la frontière. |

### 13.3 Paramètres de récupération

Définis dans `backend/rag.py`, applicables sans réindexation.

| Paramètre | Valeur | Effet |
|---|---|---|
| `SEUIL_HORS_PERIMETRE` | 0.19 | Distance au-delà de laquelle la question est refusée. Abaisser la valeur rend le système plus strict et augmente le taux de refus. |
| `N_RESULTS` | 15 | Nombre de chunks injectés dans le prompt. Augmenter améliore le rappel mais accroît le coût par requête et le risque de dilution. Relevé depuis 8 : sur les manuels courts, les distances sont très resserrées et le bon extrait peut être devancé de peu par des paragraphes voisins. |
| `N_ELARGI` | 50 | Taille du pool de candidats soumis au reclassement lexical (section 6.3) quand un instrument est détecté. Sans effet sur une recherche non filtrée par modèle. |
| `BONUS_PAR_MOT_CLE` / `BONUS_MAX` | 0.03 / 0.09 | Poids du reclassement lexical par mot de la question retrouvé littéralement dans un chunk, plafonné. Un bonus trop élevé risquerait de faire remonter un chunk peu pertinent au seul motif qu'il répète les mots de la question. |
| `MODELES` | Déduit automatiquement des noms de fichiers présents dans `data/pdf/` | Instruments reconnus pour le filtrage. Un ajout de document via le panneau admin (section 8.2) suivi d'une réindexation met cette liste à jour sans redémarrage, sans intervention manuelle sur le code. |

---

## 14. Résultats mesurés

État à la date de rédaction, corpus de 4 documents (TR-1000, TB-03, JU-06A, SH-01A ; le TR-8S, testé un temps via le panneau d'upload admin, a été retiré du corpus).

| Indicateur | Cible | Mesure | Statut |
|---|---|---|---|
| OT1, architecture RAG avec ChromaDB | Fonctionnelle | Opérationnelle | Atteint |
| OT2, temps de réponse | Moins de 5 s | 1.2 à 2.4 s selon la question | Atteint |
| KPI3, temps moyen | Moins de 8 s | 1.24 s | Atteint |
| OF2, citation des sources | Systématique | Document et page affichés | Atteint |
| OF3, refus hors périmètre | Explicite | Double filtre opérationnel | Atteint |
| OF4, deux profils | Gérés, authentification réelle | Comptes, rôles, JWT | Atteint |
| KPI2, taux d'hallucination | Moins de 5 % | 0 % sur les 12 questions dans le périmètre | Atteint |
| KPI1, précision | 90 % | 83 % (10/12) | Non atteint |
| KPI4, couverture du corpus | 6 documents minimum | 4 documents | Non atteint |
| OT4, déploiement Docker | Conteneurisé | Non réalisé | À faire |

### 14.1 Jeu de tests et tableau d'évaluation qualité

Constitué dans `backend/eval_questions.json` (12 questions dans le périmètre réparties sur les 4 documents, 6 hors périmètre) et rejoué automatiquement par `backend/evaluer.py` contre l'API en conditions réelles (authentification, appel LLM effectif). Chaque question dans le périmètre porte des mots-clés attendus, extraits manuellement du texte réel des manuels ; une question est jugée correcte si la réponse n'est pas un refus et contient au moins un des mots-clés. Les résultats détaillés sont écrits à chaque exécution dans `backend/eval_results.json` et `backend/eval_results.md`.

Sur la dernière campagne complète, les 6 questions hors périmètre ont toutes été correctement refusées (0 fausse réponse), et 10 des 12 questions dans le périmètre ont obtenu une réponse correcte. Deux cas ont été analysés individuellement avec le mode `--debug` de `rag.py` :

- Une question sur le SH-01A (jouer en MIDI) refusée à tort pendant la campagne automatisée mais correctement répondue lors d'un test isolé immédiatement après, ce qui pointe vers un aléa ponctuel (appel LLM raté sous la charge de la campagne) plutôt qu'un défaut de récupération reproductible.
- Une question sur le TR-1000 (sauvegarder un pattern) refusée de façon reproductible : le passage attendu (procédure `WRITE`, page 27) ne figure dans aucun des 15 chunks récupérés malgré l'enrichissement de synonymes existant (section 6.1). Conservé comme limite connue, section 15.5.

### 14.2 Distances observées

La calibration du seuil s'appuie sur les mesures suivantes, réalisées sur le corpus initial.

| Question | Distance du meilleur chunk |
|---|---|
| Comment sauvegarder un pattern ? | 0.131 |
| Comment régler le tempo ? | 0.149 |
| Comment connecter l'instrument en MIDI ? | 0.132 |
| Quelle est la recette de la tarte aux pommes ? | 0.209 |

L'écart entre les questions du domaine et la question témoin hors domaine est net mais modéré. Cette marge réduite justifie le maintien du second filtre : le seuil de distance seul serait fragile.

---

## 15. Limites connues et incidents documentés

### 15.1 Insuffisance du corpus

Le corpus actuel compte 173 chunks pour 4 documents, dont 96 pour le seul TR-1000. Les trois autres documents sont des guides de prise en main de deux à trois pages, non des manuels de référence complets.

Cette insuffisance est la cause racine de la majorité des comportements dégradés observés. Le pipeline fonctionne, mais il dispose de trop peu de matière. Elle explique un taux de refus élevé sur les premières mesures et compromet l'atteinte de l'objectif OF1.

Le KPI4 exige un minimum de 6 documents indexés. La correction consiste à récupérer les Reference Manuals complets, documents de 40 à 100 pages, et à relancer l'indexation. Il s'agit du point bloquant prioritaire.

### 15.2 Incident d'hallucination documenté

Un cas d'hallucination a été observé, reproduit et conservé comme premier cas du jeu de tests.

**Question.** « Comment sauvegarder un pattern sur le TR-1000 ? »

**Réponse produite.** Une procédure en quatre étapes, formatée correctement, en français, portant des marqueurs de citation `[Source 2, Source 8]`, dont la première étape indiquait d'appuyer sur `[COPY]` en maintenant `[SHIFT]`.

**Analyse.** L'inspection des chunks récupérés via le profil administrateur a établi que la source 2 traitait de l'effacement de motifs et non de leur sauvegarde, que la source 8 était un schéma de structure sans procédure, et qu'aucun des huit chunks ne mentionnait la combinaison de touches indiquée. Le modèle avait complété une procédure absente du contexte avec ses connaissances générales, puis attribué le résultat à des sources qui ne le contenaient pas.

**Gravité.** Ce type de défaillance est plus dangereux qu'un refus, car la réponse est plausible, bien structurée et apparemment sourcée. Elle correspond exactement au risque « Hallucinations LLM » identifié dans le kit projet.

**Correctifs appliqués.** Ajout au prompt système des règles 2 et 4, qui imposent la présence littérale de chaque étape dans un extrait et interdisent explicitement de compléter une procédure partielle. La validation de l'efficacité de ces règles fait partie du jeu de tests à constituer.

**Piste complémentaire.** Le modèle `mistral-small-latest` est le maillon faible identifié. La comparaison avec un modèle plus capable constituera un axe du tableau d'évaluation qualité, et l'abstraction du fournisseur rend cette comparaison immédiate.

### 15.3 Décalage entre le corpus et la problématique annoncée

Le kit projet décrit une documentation Roland majoritairement anglophone constituant un frein pour le public francophone. Le corpus effectivement constitué est composé de manuels en version française.

L'architecture reste valide, le modèle d'embeddings multilingue permettant précisément de traiter les deux cas. L'ajout de Reference Manuals anglophones, qui ne sont pas systématiquement traduits par Roland, permettrait à la fois d'enrichir le corpus et de restaurer la cohérence entre la problématique annoncée et la solution démontrée.

### 15.4 Autres limites

- **Absence de contexte conversationnel.** Conforme au périmètre, mais une question de suivi n'est pas comprise comme telle.
- **Réindexation manuelle.** Le panneau admin (section 8.2) permet d'ajouter ou de supprimer un PDF sans ligne de commande, mais un clic sur « Réindexer » reste nécessaire pour que le changement soit pris en compte par le chatbot : aucune détection automatique de nouveau fichier.
- **CORS permissif.** Acceptable en développement, à restreindre avant toute exposition.
- **Dictionnaire de synonymes statique.** Il couvre les formulations les plus courantes mais reste à compléter manuellement.

### 15.5 Cas résiduel de récupération non résolu (TR-1000)

Documenté en détail en section 14.1 et 6.3. La question « comment sauvegarder un pattern sur le TR-1000 » reste refusée à tort malgré l'enrichissement de synonymes (section 6.1) et le reclassement lexical (section 6.3), qui ont pourtant réglé un cas comparable (le réglage du tempo, section 6.3). Le passage attendu (procédure `WRITE`) ne figure simplement pas dans les 15 chunks retournés pour cette question précise.

Deux pistes de correction ont été écartées faute de temps pour les valider sans risque de régression avant la fin du projet : retoucher encore le découpage (déjà tenté sans succès sur un cas voisin, section 6.3) et élargir encore le pool de reclassement. Elles sont conservées comme axe d'amélioration (section 17).

---

## 16. Considérations légales et éthiques

### 16.1 Droit d'auteur

Le corpus est constitué de documentation technique éditée par Roland Corporation. Le système ne reproduit pas les manuels : il en restitue des extraits courts en réponse à une question précise, systématiquement accompagnés de leur référence. Les PDF sources ne sont pas versionnés dans le dépôt public.

Le projet s'inscrit dans un cadre pédagogique. Toute exploitation réelle supposerait un accord de Roland Corporation.

### 16.2 Données personnelles

L'authentification introduite après la première version du système (section 7.2, 9) modifie ce point : le système collecte désormais une adresse email et un mot de passe (jamais stocké en clair, uniquement son hash bcrypt) pour chaque compte créé, conservés dans `data/users.db`. C'est une donnée personnelle au sens du RGPD, ce que la version initiale de ce document, rédigée avant l'ajout de l'authentification, ne mentionnait pas encore.

Le journal `logs.csv` reste non nominatif : il enregistre les questions posées et leurs métriques, sans lien vers le compte qui les a posées. Le rapprochement entre une question et un utilisateur identifié n'est donc pas possible à partir des données actuellement stockées.

Dans le cadre pédagogique de ce projet, aucun compte réel d'utilisateur final n'est constitué en dehors des comptes de test des évaluateurs. Une mise en production réelle imposerait a minima une politique de confidentialité, un mécanisme de suppression de compte à la demande de l'utilisateur (actuellement possible uniquement par un administrateur via `DELETE /admin/users/{id}`, pas en autonomie par l'utilisateur lui-même), et une durée de conservation définie pour `data/users.db` et `data/logs.csv`.

Les questions transitent par ailleurs par l'API du fournisseur LLM retenu, dont la politique de traitement s'applique. Cette dépendance doit être mentionnée à l'utilisateur en cas de déploiement réel.

### 16.3 Transparence et limites

Trois dispositifs matérialisent la transparence exigée au point 7.3 du cahier des charges.

Chaque réponse porte ses sources, ce qui permet la vérification dans le manuel officiel. Un avertissement permanent en pied d'interface rappelle que le système répond uniquement à partir du corpus indexé et que les informations critiques doivent être vérifiées. Le refus explicite en cas d'information absente évite de laisser croire à une couverture qui n'existe pas.

Le profil administrateur pousse cette transparence plus loin en exposant les mécanismes internes : chunks récupérés, distances, requête enrichie, cause du refus.

---

## 17. Reste à faire

Par ordre de priorité.

**1. Cas résiduel de récupération (TR-1000).** Voir section 15.5. Investiguer plus avant sans risquer de régresser les cas déjà corrects (tempo TR-1000, tous les cas TB-03/JU-06A/SH-01A), en s'appuyant sur les outils de diagnostic existants (`rag.py --debug`, `diag_chunk.py`).

**2. Enrichissement du corpus.** Récupération des Reference Manuals complets et passage à 6 documents minimum (KPI4). Le panneau d'administration (section 8.2) rend cet ajout possible sans ligne de commande.

**3. Comparaison de modèles.** Exécution du jeu de tests existant (`backend/evaluer.py`) sur plusieurs fournisseurs afin de documenter l'impact du modèle de génération sur le taux d'hallucination.

**4. Conteneurisation Docker.** Objectif OT4. Un conteneur unique servant le build React en fichiers statiques depuis FastAPI est suffisant au regard du périmètre.

**5. Autonomie des utilisateurs sur leurs données.** Actuellement, seul un administrateur peut supprimer un compte (section 16.2). Une route permettant à un utilisateur de supprimer son propre compte serait cohérente avec le point RGPD soulevé.

Fait depuis la version 1.0 de ce document : authentification réelle (comptes, rôles, JWT), jeu de tests automatisé et tableau d'évaluation qualité (KPI1/KPI2/KPI3, section 14), panneau d'administration des documents avec réindexation à chaud et barre de progression (section 8.2), passage au modèle d'embeddings e5-base, reclassement lexical de la recherche (section 6.3).

---

*Document rédigé dans le cadre du projet de fin d'études ESI 2, Institut Limayrac.*
