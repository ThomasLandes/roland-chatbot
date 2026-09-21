"""Jeu de tests et evaluation qualite du chatbot (OF1, OT3, KPI1, KPI2, KPI3
du Kit Projet).

Interroge l'API /ask en conditions reelles (backend + LLM + embeddings deja
charges) pour chaque question de eval_questions.json, puis compare la
reponse a ce qui est attendu :

- question "dans_perimetre" : correcte si le chatbot n'a PAS refuse
  (hors_perimetre=False) ET si au moins un des mots-cles attendus (noms de
  boutons/reglages reellement presents dans le manuel) apparait dans la
  reponse.
- question "hors_perimetre" : correcte si le chatbot a bien refuse
  (hors_perimetre=True), sans inventer de reponse.

C'est une verification automatique approximative (mots-cles, pas une
comprehension semantique) : elle sert de premier filtre rapide. Les cas en
echec affiches dans eval_results.md meritent une relecture manuelle avant de
conclure definitivement sur OF1/OT3.

Usage :
    python backend/evaluer.py <email> <mot_de_passe>

Prerequis : le backend doit tourner (python -m uvicorn api:app --port 8000)
et le compte donne doit exister (n'importe quel role : /ask ne demande pas
d'etre admin).
"""
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

ROOT = Path(__file__).parent
BASE = "http://localhost:8000"

CIBLE_KPI1 = 0.90   # taux de precision (OF1 / KPI1)
CIBLE_KPI2 = 0.05   # taux d'hallucination (OT3 / KPI2)
CIBLE_KPI3 = 8.0     # temps de reponse moyen en secondes (KPI3)


def se_connecter(email, mot_de_passe):
    r = requests.post(f"{BASE}/auth/login", json={"email": email, "mot_de_passe": mot_de_passe})
    r.raise_for_status()
    return r.json()["access_token"]


def poser_question(token, question):
    r = requests.post(
        f"{BASE}/ask",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": question},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()


def evaluer_reponse(cas, resultat):
    """Retourne (correct: bool, raison: str)."""
    reponse_maj = resultat["reponse"].upper()

    if cas["type"] == "hors_perimetre":
        if resultat["hors_perimetre"]:
            return True, "refus correct"
        return False, "hallucination : a repondu alors que hors perimetre"

    # dans_perimetre
    if resultat["hors_perimetre"]:
        return False, "faux refus : question dans le perimetre mais refusee"

    mots_cles = cas.get("mots_cles", [])
    trouve = [m for m in mots_cles if m.upper() in reponse_maj]
    if trouve:
        return True, f"mots-cles trouves : {', '.join(trouve)}"
    return False, f"aucun mot-cle attendu trouve ({', '.join(mots_cles)})"


def main():
    if len(sys.argv) != 3:
        print("Usage : python backend/evaluer.py <email> <mot_de_passe>")
        sys.exit(1)

    email, mot_de_passe = sys.argv[1], sys.argv[2]
    cas_de_test = json.loads((ROOT / "eval_questions.json").read_text(encoding="utf-8"))

    print(f"Connexion ({email}) ...")
    token = se_connecter(email, mot_de_passe)

    resultats = []
    print(f"\n{len(cas_de_test)} questions a tester ...\n")
    for cas in cas_de_test:
        t0 = time.time()
        try:
            resultat = poser_question(token, cas["question"])
        except Exception as e:
            resultats.append({**cas, "erreur": str(e), "correct": False, "duree": None})
            print(f"[{cas['id']:2}] ERREUR : {e}")
            continue

        correct, raison = evaluer_reponse(cas, resultat)
        duree = resultat.get("duree", time.time() - t0)
        resultats.append({
            **cas,
            "reponse": resultat["reponse"],
            "hors_perimetre": resultat["hors_perimetre"],
            "duree": duree,
            "correct": correct,
            "raison": raison,
        })
        statut = "OK" if correct else "ECHEC"
        print(f"[{cas['id']:2}] {statut:5} ({duree:.2f}s) {cas['question'][:60]}")
        if not correct:
            print(f"        -> {raison}")

    # --- Agregation KPI ---
    dans_perimetre = [r for r in resultats if r["type"] == "dans_perimetre"]
    hors_perimetre = [r for r in resultats if r["type"] == "hors_perimetre"]

    kpi1 = sum(1 for r in dans_perimetre if r["correct"]) / len(dans_perimetre) if dans_perimetre else 0
    nb_hallucinations = sum(
        1 for r in resultats
        if not r["correct"] and r.get("raison", "").startswith("hallucination")
    ) + sum(
        1 for r in dans_perimetre
        if not r["correct"] and r.get("raison", "").startswith("aucun mot-cle")
    )
    kpi2 = nb_hallucinations / len(resultats) if resultats else 0
    durees = [r["duree"] for r in resultats if r.get("duree") is not None]
    kpi3 = sum(durees) / len(durees) if durees else 0

    print("\n--- Resume ---")
    print(f"KPI1 precision   : {kpi1:.0%}  (cible >= {CIBLE_KPI1:.0%})  {'OK' if kpi1 >= CIBLE_KPI1 else 'INSUFFISANT'}")
    print(f"KPI2 hallucination: {kpi2:.0%}  (cible < {CIBLE_KPI2:.0%})  {'OK' if kpi2 < CIBLE_KPI2 else 'INSUFFISANT'}")
    print(f"KPI3 temps moyen  : {kpi3:.2f}s (cible < {CIBLE_KPI3:.0f}s)  {'OK' if kpi3 < CIBLE_KPI3 else 'INSUFFISANT'}")

    # --- Sorties ---
    horodatage = datetime.now().strftime("%Y-%m-%d %H:%M")

    (ROOT / "eval_results.json").write_text(
        json.dumps({"date": horodatage, "kpi1": kpi1, "kpi2": kpi2, "kpi3": kpi3, "resultats": resultats},
                    ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lignes = [
        "# Tableau d'evaluation qualite\n",
        f"Genere le {horodatage} avec `backend/evaluer.py` ({len(resultats)} questions, "
        f"{len(dans_perimetre)} dans le perimetre, {len(hors_perimetre)} hors perimetre).\n",
        "## Resume\n",
        "| Indicateur | Resultat | Cible | Statut |",
        "|---|---|---|---|",
        f"| KPI1 - Taux de precision | {kpi1:.0%} | >= {CIBLE_KPI1:.0%} | {'OK' if kpi1 >= CIBLE_KPI1 else 'Insuffisant'} |",
        f"| KPI2 - Taux d'hallucination | {kpi2:.0%} | < {CIBLE_KPI2:.0%} | {'OK' if kpi2 < CIBLE_KPI2 else 'Insuffisant'} |",
        f"| KPI3 - Temps de reponse moyen | {kpi3:.2f}s | < {CIBLE_KPI3:.0f}s | {'OK' if kpi3 < CIBLE_KPI3 else 'Insuffisant'} |",
        "",
        "## Detail par question\n",
        "| # | Modele | Type | Question | Resultat | Duree | Remarque |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in resultats:
        duree_str = f"{r['duree']:.2f}s" if r.get("duree") is not None else "-"
        statut = "OK" if r["correct"] else "ECHEC"
        lignes.append(
            f"| {r['id']} | {r.get('modele') or '-'} | {r['type']} | {r['question']} | "
            f"{statut} | {duree_str} | {r.get('raison', r.get('erreur', ''))} |"
        )
    (ROOT / "eval_results.md").write_text("\n".join(lignes) + "\n", encoding="utf-8")

    print(f"\nResultats ecrits dans backend/eval_results.json et backend/eval_results.md")


if __name__ == "__main__":
    main()
