# Guide développeur

## Principe d'organisation du dépôt

Chaque phase scientifique ou d'ingénierie est un **package Python
autonome et testé**, réutilisant un socle commun plutôt que de dupliquer
la logique :

| Package | Rôle | Réutilise |
|---|---|---|
| `ml_pipeline/` | Modèle, prétraitement, XAI, détecteur temps réel | — (socle) |
| `blockchain/` | Registre Proof-of-Authority | — (socle) |
| `data_generation/` | Simulateur Smart Grid | — (socle) |
| `benchmark/` | Comparaison de 7 modèles | `ml_pipeline.prepare_split_sequences` |
| `ablation/` | Étude d'ablation à 38 configs | `benchmark.metrics` |
| `investigation/` | Diagnostic attention/temporalité | modèle figé + split |
| `robustness/` | Tests de robustesse/résilience | modèle figé (frozen) |
| `calibration/` | Calibration et recalibration | `robustness.perturbations`, `ablation.model` |
| `realdata/` | Validation SGCC | `benchmark.metrics`, `ablation.model`, `calibration.methods` |
| `production/` | Durcissement production | `api_server.py` (intégration additive) |
| `perf/` | Profilage de performance | `production/*` (mesure uniquement) |

**Règle à respecter en cas de modification** : si vous changez la logique
de split train/val/test, vous la changez pour TOUTES les phases en amont
(elles importent `prepare_split_sequences`, elles ne la réimplémentent
pas) — ne jamais dupliquer cette fonction dans un nouveau package.

## Lancer les tests avant toute contribution

```bash
# Suite complète de production
./.venv/Scripts/python.exe -m pytest production/tests/ -q

# Suite d'une phase scientifique spécifique
./.venv/Scripts/python.exe -m pytest benchmark/tests/ -q
```

Chaque nouveau package de phase doit inclure des tests vérifiant
explicitement l'absence de fuite de données (voir
`benchmark/tests/test_benchmark.py::test_split_disjoint` comme modèle) si
il introduit une nouvelle logique de split ou d'évaluation.

## Conventions de code observées

- **Docstrings orientées "pourquoi", pas "quoi"** : le code de ce projet
  documente systématiquement la raison d'un choix non évident (voir par
  exemple les docstrings de `_reading_to_raw()` dans `api_server.py`,
  qui expliquent un bug historique et sa correction) plutôt que de
  paraphraser ce que fait le code.
- **Reproductibilité** : toute expérience comparative fixe `seed=42` et
  documente ses hyperparamètres dans un fichier de config versionné
  (`benchmark/config.json`, `ablation/configs/`).
- **Rapports honnêtes** : chaque module `report.py` génère un rapport qui
  cite les chiffres mesurés, y compris défavorables — ne pas filtrer ou
  arrondir les résultats négatifs lors de l'ajout d'une nouvelle phase.

## Ajouter une nouvelle phase scientifique

1. Créer `nouvelle_phase/` avec `__init__.py`, `common.py` (chargement du
   modèle/split, en import depuis les packages existants — pas de
   duplication), `runner.py` (orchestrateur, idéalement résumable si
   l'expérience est longue), `report.py`, `tests/`.
2. Importer `prepare_split_sequences` depuis `ml_pipeline` ou le module
   qui l'expose déjà, jamais la réécrire.
3. Écrire au moins un test vérifiant l'absence de fuite si la phase
   introduit un nouveau découpage des données.
4. Générer un rapport Markdown a minima (CSV/Excel/PDF selon besoin) dans
   `nouvelle_phase/reports/`.

## Modifier le pipeline de production (`production/`)

Le Chapitre 15 (`thesis_package/thesis/chapitre_15_production.md`)
documente 6 bugs réels trouvés et corrigés durant cette phase — lire ce
chapitre avant de modifier `production/middleware.py`,
`production/security/`, ou `production/monitoring/health.py`, pour éviter
de réintroduire un défaut déjà corrigé (en particulier : ne pas
réintroduire un singleton de routeur au niveau module dans
`build_health_router`, cause du bug #5).

## Modifier le pipeline d'inférence temps réel (`ml_pipeline/`)

Avant toute modification de `realtime_detector.py`, lire le Chapitre 7.5
(`chapitre_07_pipeline_ml.md`) qui documente 3 bugs de production réels
liés à des interactions subtiles entre le prétraitement d'entraînement et
d'inférence (mise à zéro des one-hot de compteur, calcul du
`zone_consumption_mean`, détection de fuseau horaire) — des erreurs
faciles à réintroduire par une modification apparemment anodine.

## Avant de proposer un changement de seuil ou de calibration

Lire le Chapitre 13 (`chapitre_13_robustesse.md`) : la stratégie de seuil
est le levier le plus impactant identifié par l'étude d'ablation (ΔF1
+0,288), et sa dégradation sous dérive de distribution est le point de
rupture le plus sérieux du système. Toute modification de
`MeterThresholdTracker` ou de la logique de calibration doit être
re-testée contre le scénario de dérive documenté dans
`robustness/reports/` avant fusion.
