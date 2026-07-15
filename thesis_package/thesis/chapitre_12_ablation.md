# Chapitre 12 — Étude d'ablation et investigation de l'attention

## 12.1 Objectif

Après le benchmark (Chapitre 11), qui compare des architectures entières,
cette phase pose une question plus fine : **au sein même de l'architecture
Transformer Autoencoder, quels composants contribuent réellement à la
performance ?** 38 expériences, chacune retirant ou modifiant un seul
composant par rapport à une configuration de référence (budget réduit :
dimension 64, 5 époques de pré-entraînement, pour rendre les 38 exécutions
traitables), couvrant 6 catégories : architecture, capacité,
entraînement, seuil, features, exécution.

## 12.2 Référence et classement de contribution

Baseline (budget réduit) : F1=0,4475, ROC-AUC=0,9749. Classement par ΔF1
quand le composant est retiré/modifié (plus la valeur est élevée, plus le
composant était important) :

| Rang | Composant | ΔF1 |
|---|---|---|
| 1 | **Stratégie de seuil** (seuil adaptatif au lieu de F1-optimal) | **+0,2884** |
| 2 | **Normalisation** (suppression) | **+0,1997** |
| 3 | **Longueur de séquence** (32 au lieu de 8) | **+0,1782** |
| 4 | Dropout (0,0) | +0,0499 |
| 5 | Perte de reconstruction (Huber au lieu de MSE) | +0,0475 |
| … | Goulot d'étranglement AE, batch, couches, activation, features | +0,02 à +0,03 |
| — | Dimension latente | −0,0048 (amélioration) |
| — | **Encodeur Transformer** (remplacé par un encodeur dense) | **−0,0841 (amélioration)** |
| — | **Self-attention** (remplacée par un FFN token-wise) | **−0,0841 (amélioration)** |

## 12.3 Le résultat qui ne devait pas surprendre, mais a surpris

Les trois lignes en gras du bas du tableau constituent le résultat le plus
important de cette phase, et le plus contre-intuitif : **retirer
l'encodeur Transformer et son mécanisme d'attention self-attention
n'aggrave pas le F1 — il l'améliore légèrement** (+0,0841 en F1 lorsqu'on
les retire). Ce résultat aurait pu être ignoré, minimisé, ou attribué à du
bruit d'échantillonnage. Le projet a fait le choix inverse : le
sous-vérifier par une phase d'investigation dédiée (Phase 2.5), plutôt que
de la reporter telle quelle sans explication.

## 12.4 Investigation : pourquoi l'attention n'aide pas ici

Quatre expériences diagnostiques, indépendantes de l'étude d'ablation,
apportent une explication mesurée plutôt qu'une conjecture :

1. **Test de permutation temporelle** — permuter aléatoirement l'ordre des
   pas de temps à l'intérieur de chaque fenêtre change l'AUC de
   reconstruction de **Δ = −0,0004** (0,9538 → 0,9542, quasiment nul). Un
   modèle qui exploiterait réellement l'ordre temporel verrait sa
   performance chuter fortement si cet ordre est détruit — ce n'est pas le
   cas ici.
2. **Arbre de décision sur le dernier pas de temps seul** vs séquence
   complète : F1=0,9733 (dernier pas seul) contre F1=0,9722 (séquence
   complète) — la richesse temporelle de la séquence n'apporte
   pratiquement rien par rapport à la seule dernière observation.
3. **Entropie de l'attention** : 0,9611/1,0 (1,0 = uniforme parfait) — le
   mécanisme d'attention ne se concentre pas sur des pas de temps
   spécifiques, il répartit son poids presque uniformément.
4. **AUC maximale sur une seule feature** : 0,748 (feature identité de
   compteur `meter_id_SM_0015`) — une part substantielle du signal
   discriminant est déjà présente dans des features statiques/univariées,
   sans recours à la modélisation de séquence.

## 12.5 Verdict et sa portée exacte

Verdict retenu, cité textuellement : **« Rendre le Transformer
optionnel »** — conserver l'encodeur Transformer comme option de
déploiement pour des réseaux réels où les séries temporelles présentent
une structure plus riche (montées en charge progressives, attaques
coordonnées en plusieurs étapes), tout en reconnaissant explicitement que
**le résultat mesuré est une propriété des données synthétiques
utilisées, pas un défaut intrinsèque de l'architecture**. Cette
distinction est importante : elle évite la generalisation abusive « les
Transformers ne servent à rien pour les Smart Grids », qui ne serait pas
soutenue par la preuve apportée. Le Chapitre 14 (validation sur données
réelles SGCC) reviendra sur cette question avec un second jeu de données
indépendant, arrivant à la même conclusion par une voie différente — un
renforcement de la robustesse externe de ce constat, pas une simple
répétition.

## 12.6 Ce que l'ablation identifie comme réellement décisif

Le message inverse et positif de cette étude, à ne pas minimiser derrière
le résultat négatif sur l'attention : **la stratégie de sélection du
seuil de décision, la normalisation des features et la longueur de la
fenêtre de séquence sont les trois leviers qui affectent le plus la
performance** — des choix de prétraitement et de post-traitement, pas
l'architecture du réseau de neurones lui-même. Ce constat oriente
directement l'effort du projet vers la calibration et la robustesse du
seuil (Chapitre 13) plutôt que vers une recherche architecturale plus
poussée, un choix de priorisation justifié empiriquement plutôt
qu'arbitrairement.

## 12.7 Figures et données associées

`ablation/reports/` : `contribution.png`, `heatmap.png`, `sensitivity.png`,
`radar.png`, `train_time.png` ; `investigation/reports/` :
`temporal_autocorrelation.png`, `attention_analysis.png`,
`latent_space.png`, `feature_separability.png`, et le rapport détaillé
`investigation_report.md` (style discussion IEEE).
