# Chapitre 3 — Travaux connexes

> **Note méthodologique importante** : ce chapitre structure les axes de
> comparaison pertinents pour situer le projet et cite explicitement les
> deux seules références externes vérifiées dans les artefacts du projet
> (Chapitre 14, comparaison littérature de la Phase 5 SGCC). Il ne fabrique
> aucune référence bibliographique supplémentaire. **L'étudiant doit
> compléter ce chapitre avec sa propre revue de littérature** (recherche
> dans IEEE Xplore, ScienceDirect, ACM Digital Library) pour chacun des
> axes ci-dessous, en s'appuyant sur les catégories et les questions de
> positionnement déjà identifiées.

## 3.1 Détection d'anomalies dans les Smart Grids

La détection d'anomalies dans les réseaux électriques intelligents se
répartit classiquement en trois familles de méthodes, toutes représentées
dans le benchmark de ce projet (Chapitre 11) : les méthodes non supervisées
à base de distance/densité (Isolation Forest, One-Class SVM), les méthodes
de reconstruction (autoencodeurs LSTM ou Transformer), et les méthodes
supervisées (arbres de décision, boosting de gradient) lorsque des attaques
étiquetées sont disponibles. **Point de positionnement à documenter par
l'étudiant** : la littérature récente sur la détection de vol d'énergie
(*electricity theft detection*) privilégie majoritairement les approches
supervisées sur des jeux de données étiquetés au niveau consommateur (à
l'image de SGCC, utilisé au Chapitre 14), ce qui coïncide avec le constat
empirique de ce projet (Random Forest en tête sur SGCC, AUC=0.7453).

**Référence vérifiée et citée dans ce projet** (Chapitre 14, tableau de
comparaison littérature de `realdata/reports/phase5b_report.md`) :
- Zheng et al. (2018), architecture *Wide & Deep CNN* sur le jeu de données
  SGCC — AUC rapportée ≈ 0.79.
- Nagi et al., approche SVM sur données de fraude énergétique — AUC
  rapportée ≈ 0.72 (baseline citée dans la littérature du domaine).

Le Random Forest de ce projet obtient AUC=0.745 sur le même jeu de données
(SGCC, split sans fuite par consommateur), une place cohérente et honnête
par rapport à ces deux repères — ni un résultat état de l'art, ni un
résultat aberrant.

## 3.2 Modèles Transformer pour les séries temporelles

L'application de l'architecture Transformer (mécanisme d'attention
multi-têtes) aux séries temporelles est un axe de recherche actif,
initialement motivé par ses succès en traitement du langage naturel. **Axe
de discussion propre à ce projet** (Chapitre 12) : ce mémoire apporte une
contribution empirique directement pertinente à ce débat — sur les deux
jeux de données étudiés (synthétique et SGCC réel), le retrait du mécanisme
d'attention n'a PAS dégradé la performance (et l'a même légèrement
améliorée : ΔF1=+0.084 en ablation synthétique, ΔAUC=+0.011 sur SGCC réel).
L'investigation dédiée (Chapitre 12.3) attribue ce résultat à une faible
structure temporelle exploitable dans les fenêtres de séquence utilisées
(test de permutation temporelle : Δ AUC=-0.0004, quasi nul), plutôt qu'à un
défaut de l'architecture elle-même. **L'étudiant devra situer ce résultat
par rapport aux travaux qui rapportent, à l'inverse, un gain significatif de
l'attention sur des séries temporelles à structure riche** (électricité à
haute fréquence, séries multi-capteurs fortement couplées), afin de
circonscrire précisément la portée de la conclusion « rendre le Transformer
optionnel ».

## 3.3 Explicabilité (XAI) pour les modèles de détection d'anomalies

Les deux familles de méthodes XAI mobilisées dans ce projet — l'attention
comme proxy d'explication *post-hoc* et les méthodes basées gradients/valeurs
de Shapley (SHAP, integrated gradients) — correspondent aux deux grandes
approches de la littérature XAI pour les réseaux de neurones : les méthodes
*intrinsèques* (le mécanisme d'attention est nativement interprétable comme
poids d'importance) et les méthodes *post-hoc model-agnostic* (SHAP).
**Point de vigilance à documenter** : la validité de l'attention comme
explication a été remise en question dans la littérature générale sur les
Transformers (débat « attention n'est pas explication ») ; le constat du
Chapitre 12 — l'attention est quasi uniforme (entropie 0.9611/1.0) sur ce
système — est un exemple empirique concret de ce risque, à citer et discuter
par l'étudiant en regard des travaux critiques sur l'interprétabilité de
l'attention.

## 3.4 Blockchain pour l'IoT et les Smart Grids

L'utilisation de registres distribués pour la traçabilité de données IoT/
Smart Grid est un axe établi, généralement décliné en trois approches :
blockchains publiques (Ethereum), blockchains à permission (Hyperledger
Fabric), et registres à Preuve d'Autorité légers, adaptés aux contraintes de
latence et de gouvernance d'un opérateur de réseau unique — la voie retenue
ici (Chapitre 9). **Positionnement à assumer explicitement** : ce projet
n'utilise pas de blockchain publique ni de Smart Contract (Solidity), un
écart au sujet initial documenté au Chapitre 18. L'étudiant devra situer le
choix PoA local par rapport aux travaux qui utilisent Ethereum/Hyperledger
pour des cas d'usage Smart Grid comparables, et articuler pourquoi (coût de
transaction, latence, gouvernance à autorité unique vs décentralisée) ce
choix a été fait pour ce projet, au-delà de la seule contrainte de temps.

## 3.5 Calibration et fiabilité des modèles de détection

La calibration des scores de confiance (rendre une probabilité prédite
réellement représentative de la fréquence empirique) est un axe moins
systématiquement traité dans la littérature spécifique aux Smart Grids que
dans le machine learning générique (Platt scaling, isotonic regression,
temperature scaling — toutes comparées au Chapitre 13.2). **Contribution à
situer** : le résultat selon lequel la recalibration seule restaure 98,3%
de la dégradation de FPR causée par une dérive de distribution, sans
retoucher les poids du modèle, est un argument opérationnel fort en faveur
d'un pipeline de maintenance (recalibration périodique) plutôt que d'un
seul réentraînement — argument à confronter à la littérature sur le
*concept drift* dans les systèmes de détection déployés en continu.

## 3.6 Synthèse du positionnement

Ce projet se positionne comme une étude empirique rigoureuse plutôt que
comme une contribution architecturale nouvelle : aucune des briques
(Transformer autoencodeur, PoA, JWT/RBAC, Platt scaling) n'est une
invention de ce travail. L'apport est la **combinaison bout-en-bout**
(données réalistes → IA explicable → preuve blockchain → API durcie →
profilage de performance) et la **rigueur du protocole d'évaluation à
chaque étape** (Chapitres 5, 10) — en particulier le fait, rare dans les
projets de fin d'études, de rapporter des résultats défavorables à
l'hypothèse initiale (l'attention n'aide pas) plutôt que de les taire.
