# Chapitre 13 — Évaluation de la robustesse et de la calibration

Ce chapitre regroupe deux phases scientifiques étroitement liées : la
robustesse face à des conditions dégradées (bruit, données manquantes,
dérive, attaques adversariales) et la calibration des scores de confiance
— la seconde s'étant révélée, en cours de projet, être la clé
d'interprétation de plusieurs échecs observés dans la première.

## 13.1 Score composite de robustesse

Sur le modèle gelé (`outputs/early_stopping_final`, F1 propre=0,3307,
AUC=0,9538), 9 dimensions sont évaluées :

| Dimension | Score /100 |
|---|---|
| Fiabilité (reliability) | 100,0 |
| Détection d'attaque inconnue | 100,0 |
| Détection hors-distribution (OOD) | 100,0 |
| Adaptation à la dérive de concept | 100,0 |
| Robustesse au bruit | 50,3 |
| Scalabilité | 50,0 |
| Robustesse adversariale | 46,1 |
| Robustesse aux pannes de capteur | 44,5 |
| **Robustesse à la dérive** | **24,7 (la plus faible)** |
| **Robustesse aux données manquantes** | **22,3 (la plus faible)** |
| **Score composite global** | **63,8/100** |

## 13.2 Le point de rupture le plus important : la dérive de distribution

À un décalage global de seulement **0,25 écart-type (σ)**, le taux de
faux positifs sature à **100%** (F1 chute de 89,03%) et reste saturé
jusqu'à 4σ. Ce n'est pas une dégradation progressive : c'est un effet de
seuil brutal, cohérent avec un système utilisant un seuil de décision fixe
calibré sur une distribution qui n'est plus celle observée en production.

## 13.3 Un résultat contre-intuitif : les attaques déguisées deviennent PLUS détectables

Une attaque de type « dérive de concept » (l'attaquant déplace
progressivement son signal vers la moyenne de population pour se fondre
dans la normalité) fait passer le rappel de **0,5753 à 1,000** — l'inverse
de l'intuition initiale. Explication mesurée (cohérente avec le Chapitre
12.4) : en rapprochant son signal de la moyenne globale, l'attaquant
s'éloigne en réalité du comportement *local* attendu de son propre
compteur/zone, ce qui le rend plus, et non moins, détectable par un modèle
sensible aux features contextuelles de zone (`ZoneAggregator`,
Chapitre 7.4).

## 13.4 Attaques adversariales : FGSM contre PGD

| ε | FGSM (taux de détection) | PGD (taux de détection) |
|---|---|---|
| 0,00 | 0,575 | 0,575 |
| 0,05 | 0,548 | 0,260 |
| 0,10 | 1,000 | **0,164** |
| 0,25 | 1,000 | 0,233 |
| 0,50 | 1,000 | 0,534 |
| 1,00 | 1,000 | 1,000 |

**PGD** (multi-étapes, 10 pas, α=ε/4) parvient à une évasion réelle à
budget modéré (taux de détection minimal 0,164 à ε=0,1). **FGSM** (un seul
grand pas) dépasse la surface de perte de reconstruction — non convexe —
et devient paradoxalement **plus** détectable à mesure que ε augmente : un
résultat classique de la littérature en apprentissage adversarial,
rapporté ici tel quel plutôt que lissé.

## 13.5 Fiabilité et scalabilité (résultats rassurants)

- **Test de fiabilité** (60 secondes, 28 927 appels d'inférence) : **0
  erreur**, croissance mémoire de **−1,44 Mo** (pas de fuite), p99 de
  latence 2,44ms.
- **Test de charge** : débit mesuré stable à **~11 000 séquences/sec** de
  100K à 1M séquences ; au-delà, le budget de temps fixé (90s) a été
  atteint avant de traiter les 5M séquences demandées — fait rapporté
  explicitement plutôt que masqué par une extrapolation silencieuse
  (Chapitre 5.1).
- **Feature la plus fragile** (corruption isolée) : `type_industriel`
  (F1=0,0363 quand cette seule feature est corrompue).

## 13.6 Calibration : le score est-il une probabilité fiable ?

Un score de reconstruction n'est pas nativement une probabilité
interprétable. Quatre méthodes de calibration sont comparées (ECE = erreur
de calibration attendue) :

| Méthode | ECE | MCE robuste | Brier |
|---|---|---|---|
| **Platt (score brut) — retenue** | **0,0240** | 0,2128 | 0,0184 |
| Isotonic | 0,0292 | 0,5332 | 0,0280 |
| Platt (log(score+ε)) | 0,0237 | 0,7370 | 0,0218 |
| Température | 0,2298 | 0,7882 | 0,1139 |

Diagnostic de la cause racine : les scores en validation sont fortement
asymétriques (asymétrie=19,94). Un log-transform réduit cette asymétrie
(→2,00) mais introduit une **sur-confiance** mesurée dans la queue des
scores élevés — un correctif qui déplace le problème plutôt que de le
résoudre. Platt sur score brut reste le meilleur compromis mesuré.

## 13.7 Le résultat le plus actionnable du projet

> **La recalibration seule, sans aucune modification des poids du modèle,
> récupère 98,3% de la dégradation du taux de faux positifs causée par la
> dérive.**

| Condition | ECE | FPR |
|---|---|---|
| Propre | 0,0240 | 3,59% |
| Dérive, calibrateur périmé | 0,7699 | **100,00%** |
| Dérive, RECALIBRÉ | 0,0406 | **5,24%** |

Ce résultat relie directement le point de rupture du §13.2 (dérive) à un
mécanisme de correction opérationnel simple : un programme de
recalibration périodique (`recalibrate.py`, déjà implémenté, Chapitre 7.7)
plutôt qu'un réentraînement complet du modèle. C'est, à notre sens, le
résultat le plus directement exploitable de l'ensemble du projet pour un
opérateur réel.

## 13.8 Validation croisée et signification statistique

Validation croisée groupée par compteur : F1=0,5270±0,1651 (k=5),
0,3246±0,2802 (k=10). Certains replis ne contiennent que 7-9 attaques,
produisant un F1=0 par pur effet d'échantillonnage — une variance réelle et
attendue, pas une erreur de méthode. Significativité (5 replis appariés) :
supériorité significative sur Isolation Forest (d de Cohen=2,954,
p≈0) ; différence NON significative face au LSTM Autoencoder (d=0,239,
cohérent avec le Chapitre 11) ; face à One-Class SVM, taille d'effet
modérée-à-forte mais test sous-puissanté à n=5 replis.

## 13.9 Scores de synthèse

Score Qualité de Calibration : **91,5/100**. Score Rigueur Statistique :
**100/100** (rigueur = exhaustivité de la batterie de tests exécutée ; une
forte variance est rapportée honnêtement, pas pénalisée dans ce score).

## 13.10 Figures associées

`robustness/reports/` : `noise_curve.png`, `missing_curve.png`,
`drift_curves.png`, `feature_sensitivity.png`, `adversarial.png`,
`reliability.png`, `stress.png`. `calibration/reports/` :
`score_skew_diagnosis.png`, `reliability_all_methods.png`,
`calibration_comparison_bars.png`, `drift_fpr_recovery.png`,
`summary_dashboard.png`, `threshold_sensitivity.png`.
