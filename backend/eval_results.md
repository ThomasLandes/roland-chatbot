# Tableau d'evaluation qualite

Genere le 2026-09-22 00:18 avec `backend/evaluer.py` (18 questions, 12 dans le perimetre, 6 hors perimetre).

## Resume

| Indicateur | Resultat | Cible | Statut |
|---|---|---|---|
| KPI1 - Taux de precision | 83% | >= 90% | Insuffisant |
| KPI2 - Taux d'hallucination | 0% | < 5% | OK |
| KPI3 - Temps de reponse moyen | 1.38s | < 8s | OK |

## Detail par question

| # | Modele | Type | Question | Resultat | Duree | Remarque |
|---|---|---|---|---|---|---|
| 1 | TR-1000 | dans_perimetre | Comment sauvegarder un pattern sur le TR-1000 ? | ECHEC | 0.80s | faux refus : question dans le perimetre mais refusee |
| 2 | TR-1000 | dans_perimetre | Comment regler le tempo sur le TR-1000 ? | OK | 1.54s | mots-cles trouves : TEMPO, C2 |
| 3 | TR-1000 | dans_perimetre | Comment utiliser la fonction Tap Tempo sur le TR-1000 ? | OK | 1.13s | mots-cles trouves : TEMPO, SHIFT |
| 4 | TB-03 | dans_perimetre | Comment regler le tempo sur le TB-03 ? | OK | 1.81s | mots-cles trouves : TEMPO, VALUE |
| 5 | TB-03 | dans_perimetre | Comment synchroniser le TB-03 sur une horloge MIDI externe ? | OK | 2.64s | mots-cles trouves : MIDI, SYNC |
| 6 | TB-03 | dans_perimetre | Comment regler le canal MIDI du TB-03 ? | ECHEC | - | 502 Server Error: Bad Gateway for url: http://localhost:8000/ask |
| 7 | JU-06A | dans_perimetre | Comment sauvegarder un patch sur le JU-06A ? | OK | 2.33s | mots-cles trouves : BANK, PATCH |
| 8 | JU-06A | dans_perimetre | Comment jouer sur le JU-06A avec un clavier MIDI externe ? | OK | 1.88s | mots-cles trouves : MIDI |
| 9 | JU-06A | dans_perimetre | Comment connecter le JU-06A en USB a un ordinateur ? | OK | 1.81s | mots-cles trouves : USB |
| 10 | SH-01A | dans_perimetre | Comment sauvegarder les donnees du SH-01A sur un ordinateur ? | OK | 1.84s | mots-cles trouves : MENU, USB, BACKUP |
| 11 | SH-01A | dans_perimetre | Comment restaurer une sauvegarde sur le SH-01A ? | OK | 2.16s | mots-cles trouves : RESTORE, MENU |
| 12 | SH-01A | dans_perimetre | Comment jouer sur le SH-01A en MIDI ? | OK | 2.56s | mots-cles trouves : MIDI |
| 16 | - | hors_perimetre | Quelle est la recette de la tarte aux pommes ? | OK | 0.04s | refus correct |
| 17 | - | hors_perimetre | Quel temps fera-t-il a Paris demain ? | OK | 0.04s | refus correct |
| 18 | - | hors_perimetre | Peux-tu m'aider a reparer ma voiture ? | OK | 0.04s | refus correct |
| 19 | - | hors_perimetre | Quel est le meilleur synthetiseur Korg du marche ? | OK | 0.94s | refus correct |
| 20 | - | hors_perimetre | Comment configurer un serveur Minecraft ? | OK | 0.87s | refus correct |
| 21 | - | hors_perimetre | Combien coute le JU-06A a l'achat ? | OK | 1.04s | refus correct |
