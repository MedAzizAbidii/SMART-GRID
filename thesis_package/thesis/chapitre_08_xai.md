# Chapitre 8 — IA explicable (XAI)

## 8.1 Pourquoi l'explicabilité est nécessaire ici

Un score d'anomalie seul (« 0,014 ») n'est pas exploitable par un opérateur
humain devant décider d'une action (couper l'alimentation, envoyer une
équipe technique, ignorer une fausse alerte). Le système répond à deux
questions distinctes, correspondant à deux mécanismes XAI différents :
**QUAND** (quel pas de temps de la séquence a motivé la décision) et
**POURQUOI** (quelle variable — tension, courant, facteur de puissance —
est la cause principale).

## 8.2 Trois implémentations XAI dans le code

Le projet contient trois modules XAI avec des rôles et des statuts
différents, une distinction importante à ne pas aplatir dans une
présentation simplifiée :

| Module | Question | Méthode | Statut |
|---|---|---|---|
| `AttentionExplainer` | QUAND (WHERE) | Poids d'attention extraits du modèle | Utilisé en analyse |
| `SHAPExplainer` | POURQUOI (WHY) | KernelSHAP / DeepSHAP | Analyse hors-ligne (coûteux) |
| `ExplanationFusion` | QUAND + POURQUOI | Fusion des deux précédents | Combine les deux |
| **`integrated_gradients` (dans `realtime_detector.py`)** | **POURQUOI, temps réel** | **Gradients intégrés, 20 pas** | **Utilisé en production (`ingest()`)** |

Ce tableau reflète une réalité d'ingénierie assumée : SHAP, bien que
théoriquement plus rigoureux (valeurs de Shapley, garanties d'équité
d'attribution), est trop coûteux en calcul pour le chemin temps réel
(~275ms de budget total mesuré au Chapitre 16). Le pipeline de production
utilise donc **integrated gradients**, une méthode plus rapide, pour le
« POURQUOI » en temps réel, et réserve SHAP à l'analyse hors-ligne ou à la
justification approfondie d'un cas particulier.

## 8.3 Attention comme explication du « QUAND »

`AttentionExplainer.identify_critical_timesteps(attention, top_k=3)`
retourne les 3 pas de temps de la séquence de 8 lectures ayant reçu le plus
de poids d'attention moyen (sur les 4 têtes et les 3 couches). C'est ce
mécanisme qui alimente le champ `critical_timestep` retourné par
`ingest()`.

**Constat critique, développé au Chapitre 12** : sur les données de ce
projet, l'entropie normalisée de l'attention mesurée est de **0,9611/1,0**
— quasi uniforme. Concrètement, cela signifie que le mécanisme d'attention
ne sélectionne pas réellement un ou plusieurs pas de temps comme
significativement plus importants que les autres ; le `critical_timestep`
renvoyé, bien que techniquement calculé, porte une information faible.
Cette limite est assumée explicitement dans ce chapitre plutôt que
présentée comme une fonctionnalité pleinement fiable — un exemple concret
du principe méthodologique du Chapitre 5.1 (mesurer avant de conclure)
appliqué à l'explicabilité elle-même : une méthode XAI implémentée
correctement n'est pas nécessairement une méthode XAI informative sur les
données considérées.

## 8.4 Integrated Gradients comme explication du « POURQUOI » en temps réel

`integrated_gradients()` (`ml_pipeline/realtime_detector.py`) calcule
l'attribution par feature de la perte de reconstruction MSE :
1. Une **baseline nulle** (vecteur de zéros) sert de référence.
2. **20 pas d'interpolation** (α de 0 à 1) entre la baseline et l'entrée
   réelle.
3. Le gradient de la perte MSE de reconstruction est calculé à chaque pas
   interpolé.
4. Les gradients moyens sont multipliés par le delta (entrée − baseline) et
   sommés sur l'axe temporel, produisant un vecteur d'attribution de forme
   `(input_dim,)`.

Les 5 features avec l'attribution la plus élevée en valeur absolue
constituent `top_features`, retournées à chaque appel de `ingest()`.

## 8.5 Fusion des explications

`ExplanationFusion.fuse()` combine `critical_timestep` (attention) et
`top_causes` (attribution de features) en un message synthétique destiné à
l'opérateur — implémentation observée dans `ml_pipeline/xai.py` :
*« Attention indique où l'anomalie apparaît ; contributions indiquent
pourquoi »*. Cette phrase, bien que correcte sur le plan du principe,
doit être lue à la lumière du constat du §8.3 : la composante « où »
(attention) est empiriquement peu discriminante sur ce système, tandis que
la composante « pourquoi » (gradients intégrés) reste la source
d'explication la plus fiable en l'état.

## 8.6 Implication pour la conception d'interface (tableau de bord)

Le tableau de bord (Chapitre 4.7) affiche `top_features` avec une barre de
contribution visuelle, et `critical_timestep` de façon plus discrète — un
choix d'interface qui, a posteriori, s'aligne avec le constat scientifique
du §8.3, bien qu'il n'ait pas été conçu en connaissance de ce résultat au
moment du développement du tableau de bord (le constat sur l'entropie de
l'attention est postérieur, Phase 2.5). Une recommandation pour un
développement futur (Chapitre 19) serait d'aligner explicitement la
proéminence visuelle de chaque explication sur sa fiabilité mesurée.
