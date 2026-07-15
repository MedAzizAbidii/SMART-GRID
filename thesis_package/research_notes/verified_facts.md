# Faits vérifiés du projet — source unique de vérité pour le Phase 8

Ce document compile TOUS les chiffres, noms de fichiers et citations vérifiés
directement dans les fichiers sources du projet (rapports générés, code,
artefacts JSON). Aucun chiffre n'est arrondi ou approximé par rapport à sa
source. Utilisé comme référence unique pour tous les documents de thèse,
soutenance, publication et README générés dans `thesis_package/`.

Titre du projet : « Détection d'anomalies dans les Smart Grids par IA et
Blockchain : Application Mobile sécurisée » (PFE 2026).

---

## 0. État global du projet

- ~70% du sujet réalisé. **Manquant (gap assumé, à documenter honnêtement) :**
  application mobile (Flutter/React Native — absente), Smart Contracts Solidity
  sur Ethereum/Polygon/Hyperledger (seule une blockchain PoA Python locale
  existe), notifications push Firebase, connexion IA→blockchain réelle
  (Ethereum).
- Architecture retenue (README.md racine + realtime_detector.py) : Transformer
  Autoencoder, dim=128, heads=4, layers=3, seq_len=8, input_dim=84 (3 types de
  consommateurs). Détecteur de production = **EnsembleDetector** combinant
  `outputs/early_stopping_final` (précision, "v3") + `outputs/test_run_now`
  (rappel, "v2").
- **Limite scientifique honnête à énoncer explicitement** : les artefacts du
  modèle champion actuellement déployés (`early_stopping_final`,
  `test_run_now`) sont des runs **legacy** (pré-correction de la fuite de
  données du Phase 0, flux `--legacy`), confirmés par l'ABSENCE du champ
  `"protocol"` dans leurs `training_report.json`. Le protocole sans fuite
  (`prepare_split_sequences()`, split train/val/test temporel par compteur,
  scaler fit uniquement sur train) a été validé séparément (Phase 0) mais le
  modèle champion n'a pas été ré-entraîné sous ce protocole. **Ne jamais
  présenter les métriques du modèle déployé comme si elles suivaient le
  protocole sans fuite** — présenter les deux faits séparément.

---

## 1. Phase 0 — Élimination de la fuite de données

- Audit initial : verdict « prototype de recherche/labo », 43/100 (Technique
  C+/Scientifique C/Cybersécurité C-/MLOps D+).
- Fuite trouvée : le scaler était ajusté sur TOUTES les données + seuil
  sélectionné sur les mêmes données que celles rapportées (pas de jeu retenu).
- Correctif : `prepare_split_sequences()` — split temporel PAR COMPTEUR
  (train→val→test dans l'ordre chronologique), scaler ajusté sur TRAIN
  seulement, fenêtres glissantes ne traversant jamais une frontière de split
  ou de compteur. Alternative legacy conservée via `--legacy` (reproductibilité).
- **Chiffre à citer** (données de scénario) : F1 en VALIDATION = 0.91
  (optimiste, seuil ajusté ici) vs F1 en TEST retenu = **0.64** (AUC 0.98,
  Rappel 0.95, Précision 0.48). L'écart 0.91→0.64 EST le biais que l'ancien
  protocole masquait. C'est le chiffre sûr à citer dans la thèse.
- Fichier : `run_transformer_autoencoder.py`, flags `--val-frac 0.15
  --test-frac 0.15 --legacy`.

---

## 2. Phase 1 — Benchmark comparatif (`benchmark/`)

Rapport : `benchmark/reports/benchmark_report.md` (généré 2026-07-06 16:09).
Config archi (`config.json→deep`) : model_dim=128, heads=4, layers=3,
ff_dim=256, pretrain_epochs=20, finetune_epochs=2, lr=0.0005, batch_size=128,
patience=5, seq_len=8. Split : 19 850 / 3 950 / 3 950 séquences train/val/test.

**7 modèles comparés**, 3 familles :
| Modèle | Famille |
|---|---|
| Isolation Forest | anomalie non supervisée |
| One-Class SVM (SGD) | anomalie non supervisée |
| LSTM Autoencoder | reconstruction non supervisée |
| **Transformer Autoencoder (proposé)** | reconstruction non supervisée |
| Random Forest | supervisé |
| XGBoost | supervisé |
| LightGBM | supervisé |

**Métriques sur test retenu** (accuracy/précision/rappel/F1/ROC-AUC/PR-AUC/MCC) :
- XGBoost : 0.9995/1.0000/0.9726/**0.9861**/1.0000/0.9986/0.9860
- LightGBM : 0.9992/0.9730/0.9863/0.9796/1.0000/0.9986/0.9792
- Random Forest : 0.9937/0.9615/0.6849/0.8000/0.9988/0.9606/0.8087
- **Transformer AE (proposé)** : 0.9749/0.4207/0.9452/**0.5823**/0.9837/0.4845/0.6216
- LSTM AE : 0.9620/0.3192/0.9315/0.4755/0.9659/0.5050/0.5331
- One-Class SVM : 0.9182/0.0567/0.2192/0.0901/0.4762/0.0683/0.0788
- Isolation Forest : 0.6301/0.0428/0.8904/0.0817/0.7778/0.1326/0.1428

IC bootstrap 95% F1 : XGBoost [0.9624,1.0000] ; LightGBM [0.9548,1.0000] ;
Random Forest [0.7156,0.8640] ; Transformer AE [0.4999,0.6561] ; LSTM AE
[0.4000,0.5480] ; OCSVM [0.0490,0.1308] ; Isolation Forest [0.0637,0.1024].

Test de McNemar (Transformer AE vs chaque baseline, tous p<0.05) : Isolation
Forest χ²=1350.088 p=1.474e-295 ; OCSVM χ²=134.403 p=4.461e-31 ; Random Forest
χ²=47.580 p=5.279e-12 ; XGBoost χ²=93.091 p=4.995e-22 ; LightGBM χ²=94.010
p=3.139e-22 ; LSTM AE χ²=39.683 p=2.988e-10.

Citation clé : « Sous un protocole rigoureux et identique, le Transformer
Autoencoder proposé est compétitif avec de solides baselines supervisées à
boosting de gradient, tout en ne nécessitant aucun label d'attaque à
l'entraînement — le cadre opérationnellement pertinent pour une défense de
réseau contre des attaques inconnues. »

Figures : `roc_overlay.png`, `pr_overlay.png`, `f1_ci.png`, `confusion_grid.png`,
`score_dists.png`, `calibration.png`, `feature_importance.png` (dans
`benchmark/reports/` et `benchmark/plots/`).

---

## 3. Phase 2 — Étude d'ablation (`ablation/`)

Rapport : `ablation/reports/ablation_report.md` (généré 2026-07-07 05:14).
**38 expériences** (architecture / capacité / entraînement / seuil /
features / runtime). Baseline (budget réduit) : F1=**0.4475**,
ROC-AUC=0.9749, PR-AUC=0.5253, MCC=0.5052, params=113 125, latence=0.0527 ms.

**Classement de contribution (ΔF1 quand le composant est retiré)** :
1. Stratégie de seuil : +0.2884 (seuil=adaptatif, IC [0.067,0.267])
2. Normalisation : +0.1997 (sans normalisation, IC [0.164,0.316])
3. Longueur de séquence : +0.1782 (seq=32, IC [0.184,0.369])
4. Dropout : +0.0499 (dropout=0.0)
5. Perte de reconstruction : +0.0475 (perte=HUBER)
6. Goulot d'étranglement AE : +0.0324
7. Taille de batch : +0.0297
8. Couches Transformer : +0.0208
9. Fonction d'activation : +0.0208
10. Sélection de features : +0.0194
...
- Dimension latente : **−0.0048** (amélioration en le retirant)
- Taille d'embedding : **−0.0266** (amélioration en le retirant)
- **Encodeur Transformer : −0.0841 (retirer améliore le F1)**
- **Self-attention : −0.0841 (retirer améliore le F1, remplacé par un FFN token-wise)**

Citation clé (honnêteté) : « Les leviers les plus importants sont la stratégie
de seuil, la normalisation et la longueur de séquence — pas le mécanisme
d'attention (dont le retrait est resté globalement neutre, voire légèrement
positif). »

Figures : `contribution.png`, `heatmap.png`, `sensitivity.png`, `radar.png`,
`train_time.png`.

---

## 4. Phase 2.5 — Investigation : pourquoi le Transformer/l'attention n'aident pas

Rapport : `investigation/reports/investigation_report.md`.

**4 preuves mesurées** :
1. **Test de permutation temporelle** : AUC ordonné 0.9538 vs permuté 0.9542,
   **Δ = −0.0004** → le modèle n'utilise PAS l'ordre temporel.
2. **Arbre sur le dernier pas de temps seul** : F1=**0.9733** (AUC 1.0) vs
   séquence complète F1=**0.9722** (AUC 0.9999) → le contexte temporel
   n'apporte quasiment rien.
3. **Entropie de l'attention** : **0.9611/1.0** (quasi uniforme, ne sélectionne
   pas de pas de temps) ; sparsité = 0.0731.
4. **AUC max sur une seule feature = 0.748** (feature `meter_id_SM_0015`).

Verdict exact : « Nous recommandons donc de **rendre le Transformer
optionnel** : le conserver comme encodeur optionnel pour un déploiement sur
des réseaux réels, où les séries temporelles des compteurs présentent une
structure temporelle plus riche (montées en charge, attaques coordonnées en
plusieurs étapes) que ce benchmark synthétique ne reproduit pas. Le résultat
est une propriété des **données**, pas un défaut de l'architecture. »

Figures : `temporal_autocorrelation.png`, `attention_analysis.png`,
`latent_space.png`, `feature_separability.png`.

---

## 5. Phase 3 — Robustesse / résilience (`robustness/`)

Rapport : `robustness/reports/robustness_report.md` (généré 2026-07-09 00:54).
Baseline propre : F1=0.3307, AUC=0.9538.

**Scores par dimension (/100)** : Fiabilité 100.0 · Détection attaque inconnue
100.0 · Détection OOD 100.0 · Adaptation dérive de concept 100.0 · Robustesse
bruit 50.3 · Scalabilité 50.0 · Robustesse adversariale 46.1 · Robustesse
panne capteur 44.5 · Robustesse dérive 24.7 (la plus faible) · Robustesse
données manquantes 22.3 (la plus faible) · **Score composite global : 63.8/100**.

- **Tolérance à la dérive** : à un décalage de **0,25σ**, le FPR sature à
  **100%** (F1 chute à 0.0363, -89.03%) et reste saturé jusqu'à 4σ.
- **Attaques déguisées par dérive de concept** : rappel passe de **0.5753**
  (baseline) à **1.000** dès le niveau 0.25 (plus détectable, pas moins).
- **FGSM vs PGD** (taux de détection par ε) :
  | ε | FGSM | PGD |
  |---|---|---|
  |0.0|0.575|0.575|
  |0.05|0.548|0.260|
  |0.1|1.000|0.164|
  |0.25|1.000|0.233|
  |0.5|1.000|0.534|
  |1.0|1.000|1.000|
  PGD (multi-étapes) évade réellement à petit budget ; FGSM (un seul grand
  pas) dépasse la surface de perte non convexe et devient paradoxalement PLUS
  détectable — résultat classique en ML adversarial, rapporté tel quel.
- **Test de fiabilité** : 60 s, **28 927 appels**, **0 erreur**, mémoire
  **-1.44 MB** (pas de fuite), p99 latence 2.4412 ms.
- **Test de charge (stress)** : débit mesuré **~11 000 séq/s** stable de
  100K à 1M séquences ; au-delà (5M demandé), seul 1M traité avant d'atteindre
  le budget temps de 90s (extrapolation énoncée, pas simulée silencieusement).
- **Feature la plus fragile** (E05) : `type_industriel` (F1=0.0363 quand
  corrompue seule).

Figures : `noise_curve.png`, `missing_curve.png`, `drift_curves.png`,
`feature_sensitivity.png`, `adversarial.png`, `reliability.png`, `stress.png`.

---

## 6. Phase 4 — Calibration (`calibration/`)

Rapport : `calibration/reports/calibration_report.md` (généré 2026-07-09 01:58).
Score Qualité de Calibration = **91.5/100** ; Score Rigueur Statistique =
**100.0/100**.

**Comparaison des méthodes** (ECE / MCE robuste / Brier) :
- Platt (score brut) — **GAGNANT** : 0.0240 / 0.2128 / 0.0184
- Isotonic : 0.0292 / 0.5332 / 0.0280
- Platt (log(score+eps)) : 0.0237 / 0.7370 / 0.0218
- Température : 0.2298 / 0.7882 / 0.1139

**Résultat phare (dérive + recalibration)** :
| Condition | ECE | FPR |
|---|---|---|
| Propre | 0.0240 | **3.59%** |
| Dérive, calibrateur périmé | 0.7699 | **100.00%** |
| Dérive, RECALIBRÉ | 0.0406 | **5.24%** |

Citation exacte : « **La recalibration a récupéré 98,3% de la dégradation du
FPR causée par la dérive** — confirmation directe et quantifiée que l'échec
de robustesse du Phase 3 (données manquantes 22.3, dérive 24.7) est un
problème de calibration/seuil, réparable SANS toucher aux poids du modèle. »

**Validation croisée (k-fold, groupée par compteur)** : k=5 → F1=**0.5270 ±
0.1651** ; k=10 → F1=**0.3246 ± 0.2802** ; répété 3-seed → F1=**0.4303 ±
0.2742**. Certains folds ne contiennent que 7-9 attaques → F1=0 possible
(variance d'échantillonnage réelle, pas un bug).

**Significativité** (5-fold, appairé) : vs Isolation Forest — Cohen's d=2.954,
p(McNemar)≈0, **significatif** ; vs LSTM-AE — d=0.239, **non significatif**
(cohérent avec Phase 1) ; vs OCSVM — d=0.925 mais test apparié sous-puissanté
à n=5 folds.

**Stabilité du seuil** : varie de 18,0% (CV) entre folds k=5, mais localement
autour du seuil de production, dF1/d(1%)=0.0025 — stable localement, variable
globalement (deux constats vrais, différents).

Figures : `score_skew_diagnosis.png`, `reliability_all_methods.png`,
`calibration_comparison_bars.png`, `drift_fpr_recovery.png`,
`summary_dashboard.png`, `threshold_sensitivity.png`.

---

## 7. Phase 5 — Validation sur données réelles SGCC (`realdata/`)

Rapport : `realdata/reports/phase5b_report.md` (généré 2026-07-11 16:15).

**Jeu de données** : 42 372 consommateurs × 1 034 colonnes journalières,
3 615 vols / 38 757 normaux = **8,53% de fraude**, période 2014-01-01 →
2016-10-31. Manquant : **25,64%** des cellules (médiane par consommateur
10,64% ; 11 184 consommateurs >50% manquants).

**Constats Step-0 critiques** : colonnes de dates dans un ordre
LEXICOGRAPHIQUE, pas chronologique (`2014/1/1, 2014/1/10, 2014/1/11...`) →
triées avant fenêtrage. Label SGCC = niveau CONSOMMATEUR (a déjà volé, jamais)
et non par jour → évaluation faite au niveau consommateur, aucun label
quotidien fabriqué ; features électriques (V/I/PF/fréquence) NON imputées à
zéro (jeu de features natif SGCC).

**AUC par modèle (test au niveau consommateur, split sans fuite par
consommateur)** :
- Random Forest : **0.7453** (meilleur)
- LightGBM : 0.7287
- XGBoost : 0.7209
- Transformer Autoencoder (proposé) : 0.6554
- LSTM Autoencoder : 0.6543 (quasi égalité avec le Transformer)
- Isolation Forest : 0.5957
- One-Class SVM : 0.4066

**Ablation sur données réelles** : retirer l'attention **AMÉLIORE** l'AUC
(0.6554→0.6669, ΔAUC=-0.0114 = amélioration) ; retirer l'encodage positionnel
également (→0.7148) → **le constat du Phase 2.5 survit sur données réelles**.

**Transfert de calibration** : ECE=0.0014, Brier=0.0769 (la méthode Platt du
Phase 4 se transfère proprement).

**Comparaison littérature** : Wide & Deep CNN (Zheng et al. 2018) AUC 0.79 ;
SVM (Nagi et al.) 0.72 ; LSTM/RNN (divers) 0.76 ; **Notre Random Forest 0.745**
— place honnête, cohérente avec la littérature.

**Ce qui a SURVÉCU synthétique→réel** : (1) l'attention n'aide pas, (2) le
Transformer ≈ LSTM, (3) les modèles supervisés (arbres) gagnent.
**Ce qui n'a PAS transféré** : performance absolue ~0.99 (synthétique) →
~0.75 (réel) — le synthétique était plus facile, comme toujours souligné.

Figures : `benchmark.png`, `ablation.png`, `literature.png`,
`sgcc_calibration.png`, `sgcc_consumption_profiles.png`, `sgcc_missingness.png`.

---

## 8. Phase 6 — Durcissement production (`production/`)

Rapport : `production/docs/security_report.md`, `production/README.md`.

**Vulnérabilités** : 0 critique, 2 hautes (corrigées), 3 moyennes (corrigées),
2 basses/acceptées.
- CORS wildcard + `allow_credentials=True` (combinaison invalide) — corrigé.
- 18 CVE trouvées via `pip-audit` (cryptography/ecdsa/pillow/pip/setuptools/
  starlette) ; 2 CVE nommées dans starlette : **PYSEC-2026-249** (DoS parsing
  formulaire, exploitable via `/api/auth/login`) et **PYSEC-2026-2281**
  (SSRF `StaticFiles` sur Windows via chemins UNC) — 17/18 corrigées.
  Résiduelle acceptée : **PYSEC-2026-1325** (ecdsa, attaque temporelle
  Minerva) — sans correctif amont ; acceptée car l'app signe les JWT en
  HS256 (HMAC), pas ECDSA.
- passlib/bcrypt incompatible avec bcrypt≥4.1 — corrigé (appel direct à bcrypt).
- Mots de passe par défaut en clair à côté de leurs hachages — supprimés.
- `build_health_router` : singleton de routeur au niveau module accumulant
  des routes dupliquées — détecté par la suite de tests elle-même (2 échecs),
  corrigé.
- Pas de limite de débit spécifique au login (budget général 120/min =
  120 tentatives de mot de passe/min) — budget séparé 10/min ajouté.

**Tests** : `production/tests/` = `test_auth.py`, `test_config.py`,
`test_e2e_api.py`, `test_health.py`, `test_middleware.py`. **46/46 tests
passent, 90% de couverture** sur `production/`.

**Score de préparation à la production (table exacte)** :
| Dimension | Score /100 |
|---|---|
| Gestion de configuration | 90 |
| Durcissement API | 85 |
| Auth & autorisation | 80 |
| Logging | 90 |
| Monitoring | 85 |
| Récupération d'erreur | 75 |
| Tests | 90 |
| Sécurité | 80 |
| Conteneurisation | 55 |
| Documentation | 90 |
| **Global** | **~80/100** |

Documentation (`production/docs/`) : `administrator_manual.md`,
`api_documentation.md`, `backup_restore.md`, `configuration_guide.md`,
`deployment_guide.md`, `installation_guide.md`, `maintenance_guide.md`,
`operator_manual.md`, `security_report.md`.

---

## 9. Phase 7 — Profilage de performance (`perf/`, généré dans CETTE session)

Rapport : `perf/reports/phase7_performance_report.md`/`.pdf`.
**Score global : 62.2/100.**

- Inférence IA (ensemble complet) : moyenne **275,3 ms**, p95 301,1 ms, p99
  319,9 ms (n=300).
- Débit en flux continu (mono-thread) : **3,5 lectures/s**.
- Limite de débit déployée : **120 req/min** (2 req/s), confirmée par un test
  de rafale (30/150 requêtes rejetées, HTTP 429).
- **Concurrence : dégradation, pas amélioration** — 5,04 req/s à 10 requêtes
  concurrentes → **2,37 req/s à 1000** — causé par un appel bloquant
  synchrone (`_ml_detector.ingest()`) dans un gestionnaire `async def` sans
  `run_in_executor`/`asyncio.to_thread` : les requêtes se sérialisent sur un
  seul worker.
- `/health/detailed` bloque la boucle d'événements ~100 ms par appel
  (`psutil.cpu_percent(interval=0.1)` synchrone, sans offload) — interrogé
  toutes les 5s par le widget de santé du tableau de bord (Phase 6).
- Démarrage à froid : chargement du modèle ~2698 ms ; démarrage complet de
  l'application ~4010 ms.
- Aucune fuite mémoire observée sur la fenêtre de test réduite (5 min,
  documentée comme limite explicite, pas comme preuve de stabilité à long
  terme).

---

## 10. Architecture technique — vérité terrain

**Modèle** (`ml_pipeline/realtime_detector.py`) : `TransformerAutoencoder`
(dim=128, heads=4, layers=3, ff_dim=256, dropout=0.1, activation="gelu",
seq_len=8). Entraînement (`run_transformer_autoencoder.py`) : pretrain (40
époques par défaut) → finetune sur données normales (40 époques) → sélection
du seuil → évaluation. `prepare_split_sequences()` : split temporel PAR
COMPTEUR, scaler fit sur train seulement, aucune fenêtre ne traverse une
frontière de split/compteur.

**XAI** (3 modules) :
- `attention_explainer.py` (`AttentionExplainer`) — « WHERE » : quels pas de
  temps sont critiques.
- `shap_explainer.py` (`SHAPExplainer`) — « WHY » via KernelSHAP/DeepSHAP.
- `explanation_fusion.py` (`ExplanationFusion`) — fusionne WHERE (attention)
  + WHY (SHAP).
- En production temps réel, `ingest()` utilise plutôt **integrated gradients**
  (rapide, pas de SHAP) : baseline zéro, 20 pas d'interpolation alpha,
  gradient de la perte MSE de reconstruction → `top_features` (top 5) et
  `critical_timestep` (argmax de l'attention moyennée).

**Blockchain** (`blockchain/poa_ledger.py`) : Proof-of-Authority, SHA-256
exclusivement. 4 autorités : « Utility Operator », « Grid Supervisor »,
« Security Auditor », « Data Custodian ». Proposeur de bloc = rotation
round-robin (`index % 4`). Bloc = {index, timestamp, previous_hash, proposer,
authority_signature, transaction_root, transaction_count, alert_count,
normal_count, row_start, row_end, source_file, transactions, block_hash}.
Signature = `sha256(f"{secret}:{block_hash}")`. Chaîne validée en revérifiant
racine de transactions + signature + chaînage des hachages.

**Générateur de données** (`data_generation/generate_realistic_dataset.py`) :
modélise le réseau algérien (Sonelgaz). 50 compteurs, 4 zones (A=Alger
banlieue résidentielle, B=Oran commercial, C=Constantine mixte, D=Annaba
industriel léger). Types : résidentiel (55%), commercial (25%), industriel
(13%), mosquée (4%, pic vendredi/ramadan), hôpital (4%, profil quasi plat
24h). 25% des compteurs résidentiels/commerciaux ont du solaire (1,5-4,0 kW).
Tension nominale 220V, fréquence 50Hz. **5 types d'attaques** :
`FDIA_voltage` (+5 à +12% sur le capteur de tension), `FDIA_subtle`
(inflation coordonnée de 4-9% sur tous les compteurs d'une zone, indétectable
sans contexte temporel), `DoS` (rejeu de la dernière lecture), `Fraud`
(consommation ×1.8-3.5, facteur de puissance forcé à 0.45-0.70), `Fault`
(creux de tension ×0.72-0.88, pic de courant ×1.4-2.2). Taux d'attaque
réaliste ~1,5% (vs 48% dans un jeu naïf non réaliste).

**API** (`api_server.py`) — groupes d'endpoints : authentification, santé/
monitoring (Prometheus), détection (`/api/detect`, `/api/detect/batch`,
`/api/alerts`), gestion du modèle (`/api/model/status`, `/api/model/reload`,
`/api/model/registry`), blockchain (`/api/blockchain/status`), réseau/
simulation (`/api/grid/*`, `/api/simulate/attack`), intégration IoT/Packet
Tracer (`/api/packet-tracer/*`), tableau de bord statique + WebSocket temps
réel (`/ws`).

**Dashboard** : SPA HTML unique (`dashboard/index.html`) avec moteur de
templating maison (`support.js`, "dc-runtime") + widget de santé Phase 6
autonome (vanilla JS, sondage `/health/detailed` toutes les 5s).
