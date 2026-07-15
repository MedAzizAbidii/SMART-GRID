# Chapitre 2 — Énoncé du problème

## 2.1 Le problème opérationnel

Un gestionnaire de réseau de distribution électrique reçoit en continu des
lectures de compteurs intelligents (consommation, tension, courant, facteur
de puissance, fréquence). Parmi ces lectures, une fraction infime — de
l'ordre de 1 à 2% dans les jeux de données réalistes utilisés ici — reflète
soit une attaque délibérée, soit un défaut d'équipement. Le problème posé
est double :

1. **Détecter** ces événements en temps quasi réel, à partir du flux de
   lectures, sans disposer nécessairement d'exemples étiquetés pour chaque
   nouveau type d'attaque (le cas dit *unknown-attack*, opérationnellement
   le plus réaliste : un attaquant ne prévient pas de sa méthode).
2. **Prouver** qu'une détection n'a pas été falsifiée après coup — par
   exemple par un opérateur malveillant souhaitant dissimuler une fraude
   énergétique déjà détectée — ce qui motive l'ancrage blockchain des
   détections confirmées.

## 2.2 Pourquoi ce n'est pas un problème de classification supervisée classique

Un classifieur supervisé entraîné sur des exemples étiquetés d'attaques
obtient, dans ce travail, des scores très supérieurs à l'approche proposée
(XGBoost : F1=0.9861 vs Transformer Autoencoder : F1=0.5823, sur le
benchmark du Chapitre 11). Ce résultat n'est pas ignoré ni minimisé — il
est au contraire l'un des constats les plus importants du mémoire — mais il
ne répond pas à la question opérationnelle réelle : un modèle supervisé
apprend à reconnaître les *signatures* des attaques présentes dans son jeu
d'entraînement, pas la notion générale d'anomalie. Une attaque inédite,
absente des données d'entraînement, échappera structurellement à un
classifieur supervisé alors qu'un modèle de reconstruction non supervisé,
entraîné uniquement sur le comportement *normal*, a par construction une
chance de la signaler comme divergente. Ce compromis — performance
supervisée supérieure mais dépendante des labels, contre performance
non supervisée inférieure mais généralisable aux attaques inconnues — est
le choix de conception central du projet, assumé et documenté avec ses deux
faces (Chapitre 11.5).

## 2.3 Pourquoi la donnée temporelle complique l'évaluation

Une séquence de lectures d'un compteur est une série temporelle multivariée
avec forte autocorrélation (lag-1 mesuré à 0.93 pour la consommation,
Chapitre 12.2) et une distribution qui dérive dans le temps (saisons,
usages). Deux conséquences directes pour la méthodologie d'évaluation,
développées au Chapitre 5 :

- **Le risque de fuite de données** est élevé si le prétraitement
  (normalisation, sélection de seuil) est calculé sur l'ensemble du jeu de
  données avant le split train/test — un biais mesuré à un écart de F1 de
  0.91 (validation) à 0.64 (test retenu) dans ce projet avant correction.
- **La dérive de distribution** dégrade la détection à seuil fixe de façon
  spectaculaire : un décalage global de 0.25σ sature le taux de faux
  positifs à 100% (Chapitre 13), ce qui a orienté une part significative du
  travail (Chapitre 13-14) vers la calibration et la recalibration plutôt
  que vers la seule architecture du modèle.

## 2.4 Pourquoi la preuve d'intégrité (blockchain) est nécessaire

Un système de détection d'anomalies dans un contexte de fraude énergétique
a un adversaire potentiel qui n'est pas seulement l'auteur de la fraude,
mais possiblement un acteur ayant accès au système de détection lui-même
(opérateur corrompu, compromission du serveur). Un score d'anomalie stocké
uniquement dans une base de données classique peut être modifié ou
supprimé après coup sans laisser de trace. Le registre à Preuve d'Autorité
implémenté (Chapitre 9) répond à cette exigence spécifique : chaque
détection confirmée est chaînée cryptographiquement (SHA-256) à la
précédente et signée par une autorité désignée selon une rotation
round-robin, rendant toute modification rétroactive détectable par
recalcul des empreintes.

## 2.5 Questions de recherche

Ce mémoire répond empiriquement, avec preuves mesurées, aux questions
suivantes — chacune correspondant à une phase scientifique du projet :

- **Q1.** Un protocole d'évaluation naïf (sans split temporel) surestime-t-il
  la performance réelle, et de combien ? (Chapitre 5, Phase 0)
- **Q2.** Comment un autoencodeur Transformer non supervisé se positionne-t-il
  face à des baselines supervisées et non supervisées fortes, sous un
  protocole rigoureux et identique ? (Chapitre 11, Phase 1)
- **Q3.** Le mécanisme d'attention du Transformer contribue-t-il réellement à
  la performance sur ce type de données, ou est-ce une hypothèse à
  vérifier plutôt qu'à supposer ? (Chapitre 12, Phases 2 et 2.5)
- **Q4.** Le système résiste-t-il à des conditions dégradées (bruit, données
  manquantes, dérive, attaques adversariales) et où se situent précisément
  ses points de rupture ? (Chapitre 13, Phase 3)
- **Q5.** Les scores de confiance produits par le modèle sont-ils fiables
  (bien calibrés), et la calibration se dégrade-t-elle sous dérive comme la
  détection elle-même ? (Chapitre 13, Phase 4)
- **Q6.** Les constats obtenus sur données synthétiques survivent-ils au
  passage à des données réelles de fraude énergétique (SGCC, Chine) ?
  (Chapitre 14, Phase 5)
- **Q7.** Le système, une fois durci pour un usage en production, tient-il
  la charge et la concurrence réelles, et où se situe le goulot
  d'étranglement effectif ? (Chapitre 16, Phase 7)

La réponse à chacune de ces questions est parfois contre-intuitive (Q3 :
l'attention n'aide pas) ou défavorable au système proposé par rapport à une
alternative plus simple (Q2 : les arbres supervisés gagnent nettement) —
choix éditorial assumé du mémoire de rapporter le résultat mesuré plutôt que
le résultat espéré.
