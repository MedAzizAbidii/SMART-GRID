# Chapitre 10 — Protocole expérimental

## 10.1 Environnement matériel et logiciel

Toutes les expériences scientifiques (Phases 1 à 5) et le profilage de
performance (Phase 7) ont été exécutés sur une machine de développement
unique : processeur 8 cœurs logiques, GPU NVIDIA GeForce GTX 1650 (Max-Q)
présent mais **non utilisé** par le pipeline (`torch.cuda.is_available()`
retourne `False` — confirmé par échantillonnage `nvidia-smi` pendant le
profilage, Chapitre 16), environnement Python géré par un environnement
virtuel dédié (`smartgrid_simulation/.venv`, PyTorch 2.12, scikit-learn
1.7). **Conséquence méthodologique assumée** : tous les temps d'inférence
et d'entraînement rapportés dans ce mémoire sont des temps CPU, non
représentatifs d'un déploiement avec accélération GPU.

## 10.2 Protocole d'évaluation commun

Toutes les phases comparatives (benchmark, ablation, calibration,
validation SGCC) partagent le même squelette de protocole, implémenté une
seule fois (`prepare_split_sequences()`, Chapitre 5.2) et réutilisé :

1. Split temporel par compteur : `--val-frac 0.15 --test-frac 0.15` par
   défaut (soit ≈70/15/15).
2. Ajustement de tout prétraitement (scaler) sur TRAIN uniquement.
3. Sélection d'hyperparamètres/seuil sur VALIDATION uniquement.
4. Rapport des métriques finales sur TEST uniquement, jamais vu avant
   cette étape.
5. Graine aléatoire fixée (`seed=42`) pour la reproductibilité des splits
   et de l'initialisation des modèles.

## 10.3 Le modèle « gelé » comme référence commune

À partir de la Phase 3 (robustesse), les phases suivantes (robustesse,
calibration, une partie de l'ablation sur données réelles) réutilisent
délibérément le **même modèle entraîné et figé**
(`outputs/early_stopping_final`, chargé sans réentraînement) plutôt que
d'entraîner un nouveau modèle par phase. Ce choix a une justification
méthodologique précise : il isole la question posée par chaque phase (« ce
modèle EST-IL robuste au bruit ? », « ce modèle EST-IL bien calibré ? »)
de la question, différente, de savoir si un nouvel entraînement changerait
la réponse. Toute conclusion de ces phases s'applique donc explicitement
au modèle gelé étudié, pas à « l'architecture Transformer Autoencoder » en
général — une nuance rappelée dans les rapports de chaque phase.

## 10.4 Suite de métriques

L'ensemble des phases comparatives rapporte systématiquement : exactitude,
précision, rappel, F1-score, ROC-AUC, PR-AUC, coefficient de corrélation de
Matthews (MCC), exactitude équilibrée, spécificité, taux de faux positifs
et taux de faux négatifs — un choix délibérément plus large que la seule
exactitude, justifié par le déséquilibre de classes sévère (Chapitre 6.4).
Les intervalles de confiance bootstrap (95%, 1000 itérations) et le test de
McNemar apparié complètent cette suite pour toute comparaison entre modèles
(Chapitre 5.5).

## 10.5 Orchestration et reproductibilité

Chaque phase expose un point d'entrée en ligne de commande unique
(`python -m benchmark.run_benchmark`, `python -m ablation.runner`, etc.),
avec des options `--quick` (sous-échantillon rapide pour développement) et
`--fresh` (réinitialisation complète). Les orchestrateurs d'expériences
longues (ablation à 38 runs, robustesse) sont **résumables** : une
interruption (par exemple le crash documenté à l'expérience 14/38 de
l'étude d'ablation, Chapitre 12) permet une reprise à partir du dernier
point de contrôle plutôt qu'un redémarrage complet — une propriété
d'ingénierie qui s'est révélée directement utile en pratique, pas
seulement théorique.

## 10.6 Suites de tests dédiées

Chaque package de phase possède sa propre suite de tests automatisés
vérifiant, au minimum, l'absence de fuite de données et la cohérence des
métriques calculées :

| Phase | Suite de tests | Résultat |
|---|---|---|
| Benchmark | `benchmark/tests/test_benchmark.py` | 9/9 ✓ |
| Ablation | `ablation/tests/test_ablation.py` | 8/8 ✓ |
| Robustesse | `robustness/tests/test_robustness.py` | 14/14 ✓ |
| Calibration | `calibration/tests/test_calibration.py` | 11/11 ✓ (incl. tests de non-fuite et de reproductibilité) |
| Données réelles | `realdata/tests/test_realdata.py` | 8/8 ✓ |
| Production | `production/tests/*.py` | 46/46 ✓ |

## 10.7 De l'expérience au rapport

Chaque phase suit le même schéma de sortie, facilitant la lecture croisée
entre phases : un fichier de résultats bruts (`results.json` ou
équivalent), des tableaux comparatifs exportés en CSV/Markdown/LaTeX/Excel,
un jeu de figures publication-ready, et un rapport de synthèse Markdown/PDF
generé automatiquement par un module `report.py` dédié — schéma repris et
étendu par la Phase 7 (Chapitre 16).
