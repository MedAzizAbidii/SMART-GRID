# Chapitre 7 — Pipeline d'apprentissage automatique

## 7.1 Choix de l'approche : reconstruction non supervisée

Le modèle central du système est un **autoencodeur Transformer**, entraîné
à reconstruire des séquences de lectures *normales* uniquement. L'anomalie
est définie opérationnellement comme une erreur de reconstruction (MSE)
élevée relativement à un seuil — l'hypothèse sous-jacente étant qu'un
modèle n'ayant appris que le comportement normal reconstruira mal un
comportement qui s'en écarte, qu'il s'agisse d'une attaque connue ou
inconnue au moment de l'entraînement. Ce choix, ses justifications et ses
limites mesurées sont discutés en détail au Chapitre 11 (le modèle
supervisé XGBoost obtient un F1 très supérieur, mais au prix de nécessiter
des labels d'attaque).

## 7.2 Architecture du modèle

`TransformerAutoencoder` (`ml_pipeline/realtime_detector.py`) :

| Paramètre | Valeur |
|---|---|
| Dimension du modèle (`model_dim`) | 128 |
| Têtes d'attention (`num_heads`) | 4 |
| Couches d'encodeur (`num_layers`) | 3 |
| Dimension feed-forward | 256 |
| Dropout | 0,1 |
| Fonction d'activation | GELU |
| Longueur de séquence (`seq_len`) | 8 |
| Dimension d'entrée (`input_dim`) | 84 (3 types de consommateurs) |
| Encodage positionnel | sinusoïdal, max_len=512 |

Le modèle suit une architecture encodeur-décodeur classique : l'encodeur
(3 couches, auto-attention multi-têtes) projette la séquence d'entrée dans
un espace latent, le décodeur reconstruit la séquence. L'erreur de
reconstruction (MSE) sert de score d'anomalie brut.

## 7.3 EnsembleDetector : deux modèles, deux rôles

Le détecteur de production combine deux instances entraînées séparément
(`EnsembleDetector`, diagramme de classes `04_class_diagram.png`) :

- **v2** (`outputs/test_run_now`) — optimisé pour le **rappel** :
  précision=0,527, rappel=0,588, F1=0,556 (métriques du run enregistré).
  C'est ce modèle qui **déclenche** l'alarme.
- **v3** (`outputs/early_stopping_final`) — optimisé pour la
  **précision** : précision=0,425, rappel=0,615, F1=0,503. Ce modèle
  **confirme** ou non le niveau de confiance.

La confiance rapportée est « HIGH » si les deux modèles s'accordent,
« MEDIUM » si seul v2 déclenche, « NONE » sinon — une stratégie à deux
étages qui reflète un compromis opérationnel classique en détection
d'intrusion : mieux vaut une alerte à confiance modérée qu'un silence, mais
la gradation de confiance évite la fatigue d'alerte.

**Limite assumée** (reprise du Chapitre 5.2) : ces deux artefacts sont des
exécutions antérieures à la correction de la fuite de données (Phase 0) —
leurs métriques ci-dessus ne suivent pas le protocole sans fuite décrit au
Chapitre 5, et ne doivent pas être confondues avec les métriques du
Chapitre 11 (benchmark, qui lui suit strictement le protocole sans fuite).

## 7.4 Prétraitement et ingénierie de features

Chaque lecture brute traverse, avant d'atteindre le modèle :
1. **Validation Pydantic** (bornes de sécurité : rejette une consommation
   négative, une tension aberrante, etc., sans rejeter une valeur
   physiquement possible mais inhabituelle — cette distinction est
   documentée explicitement dans le code : la validation garde contre les
   erreurs de saisie/injection grossière, pas contre les anomalies
   fines, qui sont le travail du modèle).
2. **Maintien d'un tampon glissant par compteur** (`deque`, taille
   `seq_len + 6` pour disposer d'un historique suffisant au calcul des
   features de différence/moyenne mobile en bord de fenêtre, puis rognage
   à `seq_len`).
3. **Mise à jour de `ZoneAggregator`** (singleton partagé entre toutes les
   instances de détecteur d'un même processus) — calcule une moyenne de
   consommation par zone, utilisée comme feature contextuelle
   (`zone_consumption_mean`) permettant au modèle de situer une lecture par
   rapport à ses pairs géographiques, pas seulement par rapport à son
   propre historique.
4. **Features cycliques** (encodage sinus/cosinus de l'heure et du jour de
   la semaine) et **features de tendance** (moyennes/écarts mobiles,
   différences premières).
5. **Normalisation** via `StandardScaler`, ajusté sur l'ensemble
   d'entraînement uniquement (Chapitre 5.2).

## 7.5 Trois bugs corrigés en cours de projet — documentés pour leur valeur méthodologique

Trois bugs d'inférence en production, découverts via un harnais de test de
scénarios dédié (`scenario_test.py`) et non par simple relecture de code,
illustrent l'écart possible entre de bonnes métriques hors-ligne et un
comportement défaillant en ligne :

1. **Mise à zéro forcée des one-hot `meter_id`** — une « correction »
   antérieure pour les compteurs inconnus mettait à zéro l'identité du
   compteur pour TOUS les compteurs, y compris ceux connus, gonflant
   l'erreur de reconstruction d'un facteur ~75 sur des fenêtres pourtant
   identiques à l'entraînement. Le modèle s'appuie sur l'identité du
   compteur pour sa charge de base — supprimer cette information était en
   réalité la régression, pas la correction.
2. **`zone_consumption_mean` calculé sur un buffer mono-compteur** en
   production (taille de groupe = 1) contre une moyenne inter-compteurs
   réelle à l'entraînement — corrigé par l'introduction du singleton
   `ZoneAggregator` partagé (§7.4).
3. **Détection de fuseau horaire incorrecte** (`hasattr(dtype, 'tz')`
   toujours faux pour un datetime64 naïf) faisant retomber les features
   heure/jour sur la position dans le buffer plutôt que sur l'horodatage
   réel.

Conséquence mesurée de ces trois corrections : le taux de faux positifs en
test de scénarios est passé de **100% à 5%**, avec 15/15 scénarios
d'attaque détectés (5 types d'attaques français × 3 types de
consommateurs). Ce résultat est cité ici, au chapitre du pipeline, plutôt
que relégué à une note de bas de page, car il illustre un principe
d'ingénierie ML central : **une bonne métrique hors-ligne ne garantit pas
un comportement correct en ligne** si le chemin de featurisation diffère,
même subtilement, entre les deux contextes.

## 7.6 Cycle d'entraînement

Le script `run_transformer_autoencoder.py` orchestre : préparation du split
(Chapitre 5.2) → pré-entraînement (40 époques par défaut, toutes les
lectures, objectif non supervisé) → fine-tuning (40 époques, lectures
normales uniquement) → early stopping (patience=8) → sélection du seuil sur
validation → évaluation sur test retenu → sauvegarde des artefacts (poids
`.pt`, scaler, `training_report.json`).

## 7.7 De la prédiction brute à la décision

Le score de reconstruction brut n'est pas directement comparé au seuil :
il traverse une étape de **calibration** (Platt scaling sur score brut,
Chapitre 13.2) transformant le score en probabilité interprétable, avant
comparaison au seuil adaptatif par compteur (`MeterThresholdTracker`),
lui-même optionnellement auto-recalibré (`SMARTGRID_AUTO_RECAL`,
désactivé par défaut pour préserver un comportement validé).
