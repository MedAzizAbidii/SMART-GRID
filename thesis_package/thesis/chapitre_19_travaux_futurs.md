# Chapitre 19 — Travaux futurs

Les pistes ci-dessous sont directement dérivées des limitations du
Chapitre 18 et des constats mesurés des chapitres précédents — elles ne
sont pas des souhaits génériques mais des suites concrètes à des résultats
spécifiques de ce projet.

## 19.1 Compléter la triade du sujet initial

1. **Application mobile** (Flutter, pour un développement multiplateforme
   unique) consommant l'API existante (`/api/detect`, `/api/alerts`,
   `/api/blockchain/status`, WebSocket `/ws`) — l'API étant déjà conçue en
   REST/JSON, l'effort porte sur le client, pas sur une refonte du backend.
2. **Notifications push Firebase Cloud Messaging**, déclenchées côté
   backend sur les mêmes événements qui alimentent aujourd'hui
   `attacks.log` (Chapitre 4.10) — l'infrastructure de journalisation
   structurée existante est un point d'ancrage naturel pour cette
   intégration.
3. **Ancrage blockchain externe** : plutôt que de remplacer le registre PoA
   existant (dont la latence de 0,027ms/enregistrement est un atout
   opérationnel réel, Chapitre 16.2), ancrer périodiquement le hachage de
   tête de chaîne sur une blockchain publique (Ethereum/Polygon) via un
   Smart Contract Solidity minimal — combinant la performance du PoA local
   à l'horodatation non répudiable d'une chaîne publique.

## 19.2 Ré-entraîner le modèle de production sous le protocole sans fuite

Action directement actionnable et prioritaire (Chapitre 18.2) : exécuter
`run_transformer_autoencoder.py` **sans** l'option `--legacy` sur un jeu de
données de production représentatif, afin que les artefacts effectivement
chargés en production portent le champ `"protocol"` et les métriques
`validation_metrics`/test séparées — remplaçant `early_stopping_final`/
`test_run_now` par des équivalents entraînés sous le protocole validé au
Chapitre 5.

## 19.3 Architecture hybride supervisée + non supervisée

Suite directe de la discussion du Chapitre 17.3 : combiner un modèle
supervisé (XGBoost, F1=0,986 sur signatures connues) et le Transformer
Autoencoder proposé (filet de sécurité pour signaux hors distribution)
dans un pipeline à deux étages, avec une évaluation dédiée du gain net de
cette combinaison — un design non implémenté ni évalué dans ce projet.

## 19.4 Corriger le goulot d'étranglement de concurrence identifié

Suite directe du Chapitre 16.4 : déporter `_ml_detector.ingest()` sur un
exécuteur de threads (`asyncio.to_thread`) ou déployer plusieurs workers
uvicorn, puis **rejouer le protocole de profilage de la Phase 7 à
l'identique** pour quantifier le gain réel — le projet a délibérément
laissé cette correction hors périmètre (phase de mesure uniquement) mais a
produit tous les outils nécessaires (`perf/`) pour vérifier son effet.

## 19.5 Tester réellement la topologie Docker

Suite directe du Chapitre 15.5 : exécuter `docker compose up --build` sur
une machine dotée de Docker, suivant exactement les commandes documentées
dans `deployment_guide.md`, et consigner les éventuels écarts entre la
revue statique et le comportement réel.

## 19.6 Explorer l'attention sur des données à structure temporelle plus riche

Suite directe du Chapitre 12.5 : le verdict « rendre le Transformer
optionnel » est spécifique aux fenêtres de 8 lectures à intervalle de 2
minutes utilisées dans ce projet. Une piste de recherche naturelle
consiste à retester la même méthodologie d'ablation et d'investigation
(Chapitre 12.4) sur des séquences plus longues et/ou des attaques
multi-étapes coordonnées dans le temps (montées en charge progressives),
où l'hypothèse d'une structure temporelle exploitable est plus plausible.

## 19.7 Programme de recalibration en production

Suite directe du résultat le plus actionnable du projet (Chapitre 13.7) :
opérationnaliser `recalibrate.py` en tâche planifiée périodique plutôt
qu'en outil à exécution manuelle, avec un déclencheur basé sur un indicateur
de dérive mesurable (par exemple, un test de Kolmogorov-Smirnov sur la
distribution des scores récents contre celle de calibration).

## 19.8 Étendre la validation sur données réelles

Le Chapitre 14 valide sur un seul jeu de données réel (SGCC, fraude
énergétique chinoise). Une validation sur un second jeu de données réel,
idéalement européen ou nord-africain et incluant des signaux électriques
(tension/courant/fréquence, absents de SGCC), renforcerait la généralité
des constats du Chapitre 14.5 au-delà d'un seul contexte géographique et
d'un seul type de fraude.

## 19.9 API de gestion des utilisateurs

Suite directe du Chapitre 18.3 : remplacer l'édition manuelle de
`users.json` par un endpoint d'administration minimal (création/révocation
de comptes, rotation de mots de passe), réservé au rôle `administrator`.
