# Chapitre 18 — Limitations

Ce chapitre consolide, en un lieu unique, toutes les limitations déjà
énoncées ponctuellement dans les chapitres précédents — par choix éditorial
de ne pas les disperser ni les diluer.

## 18.1 Limitations de périmètre (le sujet complet non entièrement réalisé)

- **Application mobile absente** — aucun fichier Flutter/React Native
  n'existe dans le projet. C'est l'écart le plus significatif par rapport
  au sujet initial (« IA + Blockchain + Application Mobile sécurisée »).
- **Pas de Smart Contract Solidity, pas de blockchain publique/permissionnée
  externe** — le registre implémenté est une Preuve d'Autorité locale en
  Python (Chapitre 9), justifiée fonctionnellement pour le cas d'usage à
  autorité unique, mais qui ne satisfait pas littéralement l'exigence
  « blockchain » au sens où le sujet pouvait l'entendre (Ethereum/Polygon/
  Hyperledger).
- **Pas de notifications push Firebase** — conséquence directe de l'absence
  d'application mobile.

## 18.2 Limitations scientifiques

- **Modèle champion déployé non ré-entraîné sous le protocole sans fuite** —
  les artefacts `early_stopping_final`/`test_run_now` actuellement chargés
  en production sont des exécutions antérieures à la correction du Phase 0
  (absence du champ `"protocol"` dans leurs `training_report.json`,
  Chapitre 5.2). Le protocole a été validé séparément mais pas appliqué au
  modèle de production actuel — un écart concret à corriger avant tout
  usage réel, pas une question de principe.
- **Dépendance à un simulateur unique basé sur des règles** pour toutes les
  phases hors Phase 5 — la validation croisée sur SGCC (Chapitre 14) montre
  que certains constats qualitatifs survivent, mais que la performance
  absolue ne se généralise pas (~0,99→~0,75).
- **Budget d'ablation réduit** (dimension 64, 5 époques) — les écarts
  relatifs (ΔF1) restent interprétables, mais les valeurs absolues à ce
  budget ne se comparent pas directement au benchmark complet.
- **Variance d'échantillonnage substantielle en validation croisée**
  (F1 de 0,000 à ~0,78 selon les replis, Chapitre 13.8) — un résultat
  honnête sur la difficulté d'estimer une performance stable avec un
  nombre limité d'attaques par repli, pas un défaut de méthode.
- **Test de charge interrompu avant l'échelle maximale demandée** (1M
  séquences traitées sur 5M demandées, contrainte de temps, Chapitre 13.5)
  — rapporté explicitement comme mesuré-jusqu'à plutôt que comme atteint.

## 18.3 Limitations d'ingénierie de production

- **Conteneurisation Docker jamais construite réellement** (revue statique
  uniquement, absence de Docker sur la machine de développement,
  Chapitre 15.5) — le score le plus bas (55/100) du tableau de préparation
  à la production, et une action de suivi concrète avant déploiement.
- **CVE résiduelle acceptée** (`ecdsa`, sans correctif amont) — un risque
  accepté et documenté plutôt qu'ignoré, atténué par le fait que le système
  utilise HS256/HMAC et non ECDSA pour ses JWT.
- **Points de terminaison en lecture seule non authentifiés** (dont
  `/api/detect`) — compromis assumé pour préserver le fonctionnement du
  tableau de bord existant, pas un oubli, mais un point à revisiter si le
  modèle de menace évolue (accès réseau non maîtrisé, par exemple).
- **État en mémoire, mono-processus** (limite de débit et registre PoA) —
  ne survit pas à un déploiement multi-workers/multi-nœuds sans migration
  vers un stockage partagé (Redis ou équivalent).
- **Pas d'API de gestion des utilisateurs** — la création/modification de
  comptes se fait par édition manuelle de `users.json`.

## 18.4 Limitations révélées par le profilage de performance

- **Le système ne scale pas horizontalement en l'état** — un appel
  bloquant synchrone dans un gestionnaire asynchrone sérialise les requêtes
  concurrentes sur un seul worker (Chapitre 16.4), précisément identifié
  mais non corrigé dans le périmètre de ce projet (phase de mesure
  uniquement, aucune modification de code autorisée).
- **`/health/detailed` bloque la boucle d'événements ~100ms par appel**,
  sondé toutes les 5 secondes par le tableau de bord — un coût cumulé non
  négligeable sur un déploiement multi-client.
- **Le coût de validation de la blockchain croît avec l'historique
  complet** — négligeable aujourd'hui (1 seul bloc en production au moment
  du profilage), mais un point de vigilance pour la durée de vie
  opérationnelle du système.

## 18.5 Limitations méthodologiques de ce Phase 8 lui-même

- Les diagrammes et chapitres de ce mémoire ont été produits par un
  processus assisté ; **chaque chiffre a été vérifié contre les fichiers
  sources réels** du projet (voir `thesis_package/research_notes/
  verified_facts.md`) plutôt que reconstitué de mémoire, mais une relecture
  humaine complète par l'étudiant et son encadrant reste nécessaire avant
  dépôt.
- Le Chapitre 3 (Travaux connexes) identifie les axes de comparaison
  pertinents mais ne fournit pas une revue de littérature bibliographique
  complète — une tâche qui requiert une recherche documentaire que ce
  processus ne peut engager de façon fiable sans fabriquer de fausses
  citations, et qui reste donc à la charge de l'étudiant.
