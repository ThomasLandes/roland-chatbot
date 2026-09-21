# Guide utilisateur

**Assistant Roland**

Version 1.1

---

## Sommaire

1. [À quoi sert cet assistant](#1-à-quoi-sert-cet-assistant)
2. [Premiers pas](#2-premiers-pas)
3. [Poser une question efficace](#3-poser-une-question-efficace)
4. [Comprendre une réponse](#4-comprendre-une-réponse)
5. [Les différents types de réponses](#5-les-différents-types-de-réponses)
6. [Le rôle administrateur](#6-le-rôle-administrateur)
7. [Limites à connaître](#7-limites-à-connaître)
8. [Questions fréquentes](#8-questions-fréquentes)

---

## 1. À quoi sert cet assistant

L'Assistant Roland répond en français à vos questions sur l'utilisation des instruments Roland, à partir de la documentation technique officielle du constructeur.

Il vous évite de parcourir un manuel de plusieurs dizaines de pages pour retrouver une procédure. Vous posez votre question en langage courant, il vous répond en citant précisément le document et la page dont provient l'information.

### Ce qu'il sait faire

- Expliquer une procédure de prise en main
- Décrire une fonctionnalité de l'instrument
- Aider à la connexion entre instruments : synchronisation, MIDI, audio, configuration

### Ce qu'il ne sait pas faire

- Répondre sur un instrument absent de sa documentation
- Diagnostiquer une panne matérielle
- Conseiller sur un achat ou une comparaison de produits
- Répondre à une question de suivi. Chaque question est traitée indépendamment, il faut donc reformuler complètement plutôt qu'écrire « et ensuite ? »

---

## 2. Premiers pas

Ouvrez l'interface dans votre navigateur à l'adresse indiquée par votre administrateur, par défaut `http://localhost:5173`.

### Créer un compte ou se connecter

L'accès au chatbot nécessite un compte. Lors de votre première visite, créez un compte avec une adresse email et un mot de passe (8 caractères minimum) via le lien d'inscription. Les visites suivantes, connectez-vous simplement avec ces mêmes identifiants.

Un compte créé par inscription a le rôle **Utilisateur**. Le rôle **Administrateur** (section 6) ne s'obtient pas par inscription : il est attribué par un administrateur déjà en place, ou par la personne ayant déployé l'application.

Votre session reste active 24 heures. Passé ce délai, une reconnexion est demandée.

### Poser une question

L'écran d'accueil vous propose trois questions d'exemple. Cliquez sur l'une d'elles pour la faire apparaître dans le champ de saisie, ou tapez directement votre propre question.

Appuyez sur la touche Entrée ou cliquez sur **Envoyer**. La réponse arrive généralement en une à deux secondes, parfois un peu plus selon la complexité de la question.

---

## 3. Poser une question efficace

La qualité de la réponse dépend beaucoup de la formulation. Trois conseils.

### Nommez votre instrument

C'est le conseil le plus important. L'assistant reconnaît le modèle mentionné dans votre question et restreint alors sa recherche à la documentation de cet appareil.

| Formulation | Résultat |
|---|---|
| « Comment sauvegarder un pattern sur le TR-1000 ? » | Recherche limitée au TR-1000 |
| « Comment sauvegarder un pattern ? » | Recherche sur tous les instruments, réponse possiblement issue d'un autre modèle |

Plusieurs instruments Roland décrivent des opérations semblables avec des procédures différentes. Sans précision de votre part, l'assistant peut vous répondre à propos du mauvais appareil.

L'écriture du modèle est souple : `TR-1000`, `TR 1000` et `tr1000` sont reconnus indifféremment.

### Posez une question à la fois

Une question portant sur un seul sujet obtient une réponse plus précise qu'une question qui en combine plusieurs.

Préférez deux questions successives à « comment régler le tempo et sauvegarder mon pattern ».

### Utilisez le vocabulaire de l'instrument quand vous le connaissez

L'assistant comprend les formulations courantes et sait rapprocher « sauvegarder » de l'opération `WRITE` décrite dans les manuels. Mais si vous connaissez le terme exact employé par Roland, l'utiliser améliore la précision de la recherche.

---

## 4. Comprendre une réponse

Une réponse se compose de trois éléments.

**Le texte de la réponse**, généralement présenté sous forme d'étapes numérotées lorsqu'il s'agit d'une procédure. Des marqueurs `[Source N]` y sont insérés pour indiquer d'où provient chaque information.

**Les sources**, listées sous la réponse dans un encadré séparé. Chacune indique le nom du document et le numéro de page.

**Le temps de réponse**, affiché en petits caractères.

### Vérifier dans le manuel

Les sources ne sont pas décoratives. Elles vous permettent d'ouvrir le manuel officiel à la page indiquée et de vérifier l'information par vous-même.

Prenez cette habitude pour toute opération importante : mise à jour du système, formatage d'une clé USB, réinitialisation d'usine, ou toute manipulation susceptible d'effacer vos données.

---

## 5. Les différents types de réponses

L'interface distingue trois cas par un code couleur.

### Réponse normale, fond blanc

L'assistant a trouvé l'information dans la documentation et vous la restitue avec ses sources.

### Refus, fond orange

L'assistant vous indique ne pas disposer de l'information et vous redirige vers le support Roland.

Deux situations conduisent à ce message. Soit votre question sort du domaine couvert, soit elle porte bien sur un instrument Roland mais la réponse ne figure pas dans les documents indexés.

**Ce refus est un comportement volontaire, pas un dysfonctionnement.** L'assistant est conçu pour reconnaître ses limites plutôt que d'inventer une réponse plausible. Un refus est toujours préférable à une procédure erronée.

Si vous pensez que la question aurait dû trouver réponse, essayez de la reformuler en précisant le modèle d'instrument, ou en employant un vocabulaire plus proche de celui du manuel.

### Erreur technique, fond rouge

La communication avec le service a échoué. Vérifiez votre connexion et réessayez. Si le problème persiste, signalez-le à votre administrateur.

---

## 6. Le rôle administrateur

Si votre compte a le rôle **Administrateur**, l'interface affiche des éléments supplémentaires, invisibles pour un compte **Utilisateur** classique. Ce rôle est attribué par un autre administrateur (section 2) et ne se choisit pas soi-même.

### 6.1 Diagnostic des réponses

**Un bandeau de statistiques** en haut de l'écran : nombre de documents indexés, nombre de fragments de texte, fournisseur utilisé, seuil de refus, et statistiques d'usage.

**Les distances vectorielles** à côté de chaque source. Il s'agit d'une mesure de proximité entre votre question et le passage retrouvé. Plus la valeur est basse, plus le passage est jugé pertinent. En pratique, une valeur inférieure à 0.15 indique une correspondance forte.

**Un panneau « Détails techniques »** dépliable sous chaque réponse, qui expose le fonctionnement interne : le modèle d'instrument détecté, la requête après enrichissement automatique, la cause d'un éventuel refus, et l'intégralité des passages consultés avec leur extrait.

Ce rôle sert au diagnostic. Face à une réponse insatisfaisante, il permet de déterminer si l'assistant a consulté les bons passages ou s'il a mal exploité les bons passages. Ce sont deux problèmes distincts qui appellent des corrections différentes.

### 6.2 Gérer les documents indexés

Un panneau « Documents » liste les PDF actuellement indexés avec leur taille. Il permet d'ajouter un nouveau manuel (glisser-déposer ou sélection du fichier, format PDF uniquement) et de supprimer un document existant.

**Important : ajouter ou supprimer un fichier ne suffit pas.** Ces deux actions modifient uniquement la liste des documents disponibles. Pour que le chatbot tienne compte du changement dans ses réponses, il faut ensuite cliquer sur **Réindexer**. Une barre de progression s'affiche pendant l'opération, qui peut prendre de quelques secondes à quelques dizaines de secondes selon le nombre et la taille des documents. Le chatbot reste utilisable normalement une fois la réindexation terminée, sans redémarrage du service.

### 6.3 Gérer les comptes utilisateurs

Un panneau « Utilisateurs » liste les comptes créés, avec leur rôle. Un administrateur peut changer le rôle d'un autre compte ou le supprimer. Par sécurité, il est impossible de modifier son propre rôle ou de supprimer son propre compte depuis cette interface, et le dernier compte administrateur du système ne peut être ni rétrogradé ni supprimé.

---

## 7. Limites à connaître

### L'assistant ne connaît que ce qui a été indexé

Il ne consulte pas Internet et n'accède pas au site de Roland. Sa connaissance se limite strictement aux documents chargés dans sa base. Un instrument absent de cette base lui est totalement inconnu.

### Il ne se souvient pas de vos échanges précédents

Chaque question est traitée seule. Vos messages précédents restent affichés à l'écran, mais l'assistant n'en tient pas compte. Reformulez donc complètement à chaque nouvelle question.

### Il peut se tromper

C'est la limite la plus importante. Bien que conçu pour ne répondre qu'à partir de la documentation et pour refuser lorsqu'il ne sait pas, l'assistant reste construit sur un modèle de langage susceptible de produire une réponse inexacte.

Un cas a été observé où une procédure plausible et correctement formatée s'est révélée inexacte après vérification dans le manuel.

**Vérifiez toujours les informations critiques dans la documentation officielle**, à la page que l'assistant vous indique. C'est précisément la raison pour laquelle chaque réponse est sourcée.

### Vos questions transitent par un service externe

Les questions posées sont transmises à un fournisseur d'intelligence artificielle externe pour produire la réponse. N'y faites pas figurer d'informations personnelles ou confidentielles.

---

## 8. Questions fréquentes

**L'assistant refuse toutes mes questions.**

Vérifiez d'abord que votre instrument fait partie des modèles couverts. Le bandeau administrateur indique le nombre de documents indexés. Si votre instrument n'y figure pas, aucune reformulation n'y changera rien.

**Il me répond à propos d'un autre instrument que le mien.**

Vous n'avez probablement pas mentionné le modèle dans votre question. Ajoutez-le et reposez la question.

**La réponse ne correspond pas à ce que je vois sur mon appareil.**

Ouvrez le manuel à la page citée en source et comparez. Deux explications possibles : la réponse est inexacte, ou votre version du logiciel interne diffère de celle documentée. Dans le premier cas, signalez-le à votre administrateur, cela contribue à l'amélioration du système.

**Puis-je lui demander de comparer deux instruments ?**

Il n'est pas conçu pour cela. Il retrouve des passages de documentation, il ne construit pas d'analyse comparative. Posez plutôt une question distincte pour chaque instrument.

**Combien de temps doit prendre une réponse ?**

Une à deux secondes. Au-delà de cinq secondes, signalez-le à votre administrateur.

**Comment obtenir de l'aide sur une question hors périmètre ?**

Adressez-vous au support Roland, dont l'adresse figure dans le message de refus.

---

*Assistant Roland, projet de fin d'études ESI 2, Institut Limayrac. Cet outil complète la documentation officielle Roland sans s'y substituer.*
