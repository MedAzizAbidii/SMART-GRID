# Chapitre 5 — Méthodologie

## 5.1 Principe directeur : mesurer avant de conclure

Ce projet adopte, de façon systématique à travers ses huit phases
scientifiques et d'ingénierie, un principe méthodologique unique : **toute
affirmation de performance, de robustesse ou de comportement doit être
appuyée par une mesure reproductible, jamais par une estimation ou une
extrapolation non signalée comme telle**. Ce principe a des conséquences
concrètes documentées à travers ce mémoire : lorsqu'un test de charge n'a
pu être mené jusqu'à l'échelle demandée dans le temps imparti (Chapitre
13.6, test à 5M séquences interrompu à 1M par un budget de 90 secondes),
le rapport l'indique explicitement plutôt que de présenter une
extrapolation silencieuse comme une mesure.

## 5.2 La fuite de données : diagnostic et correction (Phase 0)

Le point de départ méthodologique du projet a été un audit qui a révélé un
biais classique mais sérieux : le `StandardScaler` de normalisation était
ajusté sur l'intégralité du jeu de données (train+validation+test réunis)
et le seuil de décision était sélectionné sur les mêmes données que celles
utilisées pour rapporter la performance finale — un jeu de test qui n'en
était pas un, puisqu'aucune partie des données n'était réellement tenue à
l'écart de l'ajustement du système.

**Correction implémentée** (`prepare_split_sequences()`,
`run_transformer_autoencoder.py`) :
1. **Split temporel PAR COMPTEUR** : pour chaque compteur, les lectures sont
   ordonnées chronologiquement puis découpées en TRAIN (premières lectures)
   → VALIDATION → TEST (dernières lectures), de sorte que le test soit
   strictement postérieur, dans le temps, aux données d'entraînement de ce
   même compteur.
2. **Ajustement du scaler sur TRAIN uniquement**, puis application
   (transform seul, sans refit) sur validation et test.
3. **Aucune fenêtre glissante ne traverse une frontière** de split ou de
   compteur — une fenêtre de 8 lectures consécutives appartient
   entièrement à un seul split et un seul compteur.
4. **Sélection du seuil de décision sur VALIDATION uniquement** ; les
   métriques rapportées comme résultat final proviennent exclusivement du
   TEST, jamais vu avant l'évaluation finale.

**Preuve quantifiée de l'impact du biais** (données de scénario,
Chapitre 11) : F1 en validation = 0,91 (optimiste, seuil ajusté sur ces
mêmes données) contre F1 en test retenu = **0,64** (AUC 0,98, Rappel 0,95,
Précision 0,48). L'écart 0,91→0,64 EST la mesure directe du biais que
l'ancien protocole masquait — c'est le chiffre que ce mémoire retient
comme référence honnête, et non le chiffre optimiste de validation.

Un mode `--legacy` reproduisant l'ancien flux est conservé dans le code
pour la reproductibilité des résultats antérieurs à cette correction, mais
n'est plus recommandé. **Point de vigilance explicite** : les artefacts du
modèle actuellement chargés en production (`outputs/early_stopping_final`,
`outputs/test_run_now`) sont des exécutions antérieures à cette correction
(confirmé par l'absence du champ `"protocol"` dans leurs
`training_report.json`) — le protocole sans fuite a été validé
séparément mais le modèle champion déployé n'a pas encore été
ré-entraîné sous ce protocole. Ce point est repris et assumé comme limite
au Chapitre 18.

## 5.3 Architecture logicielle de la recherche : réutilisation, pas duplication

Chaque phase scientifique postérieure au Phase 0 (benchmark, ablation,
robustesse, calibration, données réelles) est un package Python autonome
(`benchmark/`, `ablation/`, `robustness/`, `calibration/`, `realdata/`) qui
**réutilise** `prepare_split_sequences()` et les métriques communes
(`benchmark.metrics`) plutôt que de dupliquer la logique de split et
d'évaluation. Ce choix d'architecture logicielle a une justification
méthodologique directe : une seule implémentation du split évite que deux
phases utilisent, sans le savoir, des définitions légèrement différentes
de « fuite » ou de « split correct », ce qui rendrait les résultats entre
phases non comparables.

## 5.4 Vérification systématique de l'absence de fuite

Chaque package de test associé à une phase (`test_benchmark.py`,
`test_ablation.py`, `test_robustness.py`, `test_calibration.py`,
`test_realdata.py`) inclut des tests dédiés vérifiant explicitement la
disjonction des lignes sources entre splits (`_validate_split` dans le
framework de benchmark) — la non-fuite n'est donc pas seulement une
propriété visée du code, mais une propriété testée automatiquement à
chaque exécution.

## 5.5 Traitement statistique des résultats

Les comparaisons de modèles s'appuient systématiquement sur :
- des **intervalles de confiance bootstrap à 95%** (1000 itérations) pour
  F1, ROC-AUC, PR-AUC et MCC (Chapitre 11) ;
- le **test de McNemar apparié** pour la significativité statistique entre
  le modèle proposé et chaque baseline (Chapitre 11.4) ;
- une **validation croisée groupée par compteur** (k=5, k=10, répétée sur 3
  graines aléatoires) pour quantifier la variance d'échantillonnage
  (Chapitre 13.5), avec un constat honnête : certains replis ne contiennent
  que 7 à 9 attaques, produisant un F1 de 0 par pur effet d'échantillonnage
  — un résultat rapporté et expliqué plutôt que masqué.

## 5.6 Séquencement des phases et jalons de validation utilisateur

Le projet a procédé par phases strictement séquentielles, chacune
conditionnant la suivante, avec des jalons explicites de validation avant
de poursuivre (par exemple : validation du choix de sémantique des labels
SGCC au niveau consommateur avant de lancer le Phase 6 de durcissement
production). Cette structure séquentielle, documentée intégralement dans
les mises à jour de suivi de projet, garantit qu'aucune phase ultérieure ne
s'appuie sur un résultat non validé par la phase précédente.

## 5.7 Limites méthodologiques assumées

- Les jeux de données synthétiques (benchmark, ablation, robustesse,
  calibration) reposent sur un seul générateur basé sur des règles
  (Chapitre 6) ; leur validité externe est testée, mais seulement
  partiellement confirmée, par la validation sur données réelles SGCC
  (Chapitre 14) — certains constats survivent au passage au réel,
  d'autres non (écart de performance absolue).
- Le budget d'ablation utilise une configuration réduite (dimension 64, 5
  époques de pré-entraînement) pour rendre les 38 expériences traitables en
  temps raisonnable ; les écarts relatifs (ΔF1) restent interprétables mais
  les valeurs absolues de F1 à ce budget ne sont pas directement comparables
  à celles du benchmark complet (Chapitre 11 vs Chapitre 12).
