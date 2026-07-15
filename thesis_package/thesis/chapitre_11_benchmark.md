# Chapitre 11 — Résultats du benchmark comparatif

## 11.1 Objectif et configuration

Cette phase compare, sous un protocole strictement identique (Chapitre 10),
7 modèles de 3 familles sur les données de scénario synthétiques : split
19 850 / 3 950 / 3 950 séquences (train/val/test), architecture Transformer
Autoencoder dim=128/heads=4/layers=3/seq_len=8, entraînement 20 époques de
pré-entraînement + 2 de fine-tuning.

## 11.2 Résultats sur le test retenu

| Modèle | Famille | F1 | ROC-AUC | Précision | Rappel |
|---|---|---|---|---|---|
| **XGBoost** | supervisé | **0,9861** | 1,0000 | 1,0000 | 0,9726 |
| LightGBM | supervisé | 0,9796 | 1,0000 | 0,9730 | 0,9863 |
| Random Forest | supervisé | 0,8000 | 0,9988 | 0,9615 | 0,6849 |
| **Transformer AE (proposé)** | reconstruction | **0,5823** | 0,9837 | 0,4207 | 0,9452 |
| LSTM AE | reconstruction | 0,4755 | 0,9659 | 0,3192 | 0,9315 |
| One-Class SVM | anomalie | 0,0901 | 0,4762 | 0,0567 | 0,2192 |
| Isolation Forest | anomalie | 0,0817 | 0,7778 | 0,0428 | 0,8904 |

Intervalles de confiance bootstrap (95%, F1) : XGBoost [0,9624–1,0000] ;
Transformer AE [0,4999–0,6561] ; Isolation Forest [0,0637–0,1024]. Le test
de McNemar confirme que le Transformer AE diffère significativement de
**chacune** des 6 baselines (p < 10⁻⁹ dans tous les cas, Chapitre 5.5).

## 11.3 Lecture du tableau : deux histoires, pas une

Une lecture superficielle ne retiendrait que « XGBoost bat le Transformer
de 40 points de F1 ». Cette lecture est correcte mais incomplète — elle
occulte la différence de nature entre les deux résultats.

- **XGBoost, LightGBM, Random Forest** sont des modèles **supervisés** :
  ils ont accès, à l'entraînement, aux étiquettes des 5 types d'attaques
  simulées. Leur performance mesure leur capacité à reconnaître des
  **signatures d'attaques connues**.
- **Transformer AE, LSTM AE, Isolation Forest, One-Class SVM** sont des
  modèles **non supervisés** : ils n'ont accès, à l'entraînement, qu'aux
  lectures considérées comme normales (ou à l'ensemble des lectures sans
  étiquette). Leur performance mesure leur capacité à détecter une
  déviation par rapport à la normalité — y compris, en principe, pour un
  type d'attaque non présent dans l'entraînement (Chapitre 2.2).

Sous cette lecture, le résultat pertinent n'est pas « le Transformer perd
face à XGBoost » mais **« parmi les méthodes ne nécessitant aucun label
d'attaque, le Transformer Autoencoder proposé est le plus performant »**
(F1=0,5823 contre 0,4755 pour le LSTM AE, 0,0901 pour l'OCSVM, 0,0817 pour
l'Isolation Forest) — la comparaison opérationnellement pertinente pour un
déploiement anticipant des attaques inconnues.

## 11.4 Signification statistique

Le test de McNemar apparié, appliqué au Transformer AE contre chacune des
6 baselines, rejette l'hypothèse nulle d'équivalence dans tous les cas
(exemples : χ²=1350,088, p=1,47×10⁻²⁹⁵ contre Isolation Forest ;
χ²=39,683, p=2,99×10⁻¹⁰ contre LSTM AE) — les écarts observés, dans les
deux sens (supériorité sur les méthodes non supervisées, infériorité face
aux méthodes supervisées), ne sont pas des artefacts d'échantillonnage.

## 11.5 Le compromis assumé : label-free vs performance brute

Ce résultat cristallise le compromis de conception central du projet
(Chapitre 2.2), qu'il convient d'énoncer sans ambiguïté plutôt que de le
diluer :

> **Un système supervisé (XGBoost) est mesurablement supérieur pour
> détecter des attaques dont le type est connu à l'avance. Le système
> proposé (Transformer Autoencoder non supervisé) sacrifie cette
> performance brute contre la capacité, non testée dans ce benchmark mais
> visée par construction, de détecter des attaques dont le type n'a
> jamais été vu à l'entraînement.**

Ce mémoire ne prétend pas que ce compromis est gratuit ni sans coût — le
Chapitre 17 (Discussion) revient sur la question de savoir si ce compromis
est le bon choix pour un déploiement réel, notamment à la lumière du
résultat de la Phase 5 (Chapitre 14) où, sur données réelles, un modèle
supervisé (Random Forest) reste également en tête.

## 11.6 Figures et tables associées

`benchmark/reports/` : `roc_overlay.png`, `pr_overlay.png`, `f1_ci.png`
(F1 avec IC bootstrap), `confusion_grid.png`, `score_dists.png`,
`calibration.png`, `feature_importance.png` ; tableaux exportés
`comparison.{csv,md,tex,xlsx}`.
