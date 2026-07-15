# Chapitre 14 — Validation sur données réelles (SGCC)

## 14.1 Pourquoi cette phase est indispensable

Toutes les phases précédentes (Chapitres 11-13) reposent sur des données
**synthétiques**, générées par un simulateur basé sur des règles
(Chapitre 6). Aussi soigné que soit ce simulateur, aucun résultat obtenu
uniquement sur données synthétiques ne peut être présenté comme validé
pour un usage réel sans confrontation à des données indépendantes réelles.
Cette phase utilise le jeu de données public **SGCC** (State Grid
Corporation of China), la référence de facto dans la littérature sur la
détection de vol d'énergie (fraude électrique).

## 14.2 Le jeu de données et ses défauts réels

42 372 consommateurs × 1 034 colonnes journalières, 3 615 cas de vol
(8,53%), période du 1er janvier 2014 au 31 octobre 2016. Deux défauts de
qualité de données, découverts et corrigés avant toute modélisation
(« Step-0 ») :

1. **Colonnes de dates en ordre lexicographique**, pas chronologique
   (`2014/1/1, 2014/1/10, 2014/1/11, ...`) — un piège qui, non détecté,
   aurait complètement invalidé toute fenêtre temporelle construite sur ces
   données. Corrigé par un tri chronologique explicite avant fenêtrage.
2. **25,64% de cellules manquantes** (médiane par consommateur : 10,64% ;
   11 184 consommateurs avec plus de 50% de données manquantes) — traité
   par interpolation linéaire par consommateur, la fraction de données
   manquantes étant elle-même conservée comme feature (signal potentiel de
   fraude : un fraudeur peut chercher à masquer des lectures).

## 14.3 Décision de sémantique des labels — un choix assumé, pas une approximation silencieuse

Le label SGCC (`FLAG`) est défini au **niveau du consommateur** (« a déjà
fraudé, oui/non ») et non au niveau de chaque lecture journalière, à la
différence des labels synthétiques des chapitres précédents. Décision
retenue, discutée et validée avant poursuite du projet : évaluer au niveau
consommateur (une prédiction par consommateur), en faisant remonter les
scores de reconstruction des modèles de séquence par agrégation. **Aucun
label journalier n'a été fabriqué** pour contourner cette limite — un choix
de rigueur qui a un coût direct (impossibilité de localiser précisément
le jour de fraude), assumé explicitement plutôt que masqué par une
labellisation artificielle.

## 14.4 Résultats (AUC, test au niveau consommateur, split sans fuite par consommateur)

| Modèle | AUC |
|---|---|
| **Random Forest** | **0,7453 (meilleur)** |
| LightGBM | 0,7287 |
| XGBoost | 0,7209 |
| Transformer Autoencoder (proposé) | 0,6554 |
| LSTM Autoencoder | 0,6543 (quasi égalité) |
| Isolation Forest | 0,5957 |
| One-Class SVM | 0,4066 |

## 14.5 Ce qui a survécu au passage synthétique → réel

Trois constats obtenus sur données synthétiques (Chapitres 11-12) sont
retestés indépendamment ici et **confirmés** :

1. **L'attention n'aide pas** : retirer l'attention améliore légèrement
   l'AUC (0,6554→0,6669) ; retirer aussi l'encodage positionnel améliore
   encore (→0,7148). Le constat du Chapitre 12 n'est donc pas un artefact
   du simulateur — il se reproduit sur un jeu de données réel, indépendant,
   d'une nature de fraude différente (vol d'énergie chinois vs attaques
   FDIA/DoS/Fraude algériennes synthétiques).
2. **Le Transformer ≈ LSTM** : 0,6554 contre 0,6543 — les deux
   architectures de reconstruction se valent, cohérent avec le Chapitre 11.
3. **Les modèles supervisés (arbres) gagnent** : Random Forest en tête,
   cohérent avec le Chapitre 11.

## 14.6 Ce qui n'a PAS survécu

La performance absolue chute fortement : ~0,99 (métriques synthétiques,
selon la métrique) contre ~0,75 (AUC réel, au mieux) — **le jeu de données
synthétique était sensiblement plus facile** que la réalité, un
avertissement à ne jamais perdre de vue en interprétant les résultats des
Chapitres 11-13 comme des bornes supérieures optimistes, pas comme des
performances attendues en production.

## 14.7 Transfert de la calibration

La méthode de calibration retenue au Chapitre 13.6 (Platt sur score brut)
se transfère proprement aux données réelles SGCC : ECE=0,0014,
Brier=0,0769 — un résultat rassurant sur la généralité de la méthode de
calibration, indépendamment du jeu de données.

## 14.8 Position par rapport à la littérature

| Méthode | AUC rapportée |
|---|---|
| Wide & Deep CNN (Zheng et al., 2018) | ≈0,79 |
| **Random Forest (ce projet)** | **0,745** |
| SVM (Nagi et al., référence citée) | ≈0,72 |

Cette place — ni état de l'art, ni aberrante — est cohérente avec un
sous-échantillon stratifié de 8 000 consommateurs et un budget
d'entraînement fixe adoptés pour la tractabilité de cette phase, une limite
assumée (Chapitre 18) plutôt qu'un résultat présenté comme définitif.

## 14.9 Figures associées

`realdata/plots/` : `benchmark.png`, `ablation.png`, `literature.png`,
`sgcc_calibration.png`, `sgcc_consumption_profiles.png`,
`sgcc_missingness.png`.
