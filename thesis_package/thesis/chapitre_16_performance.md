# Chapitre 16 — Évaluation de la performance

## 16.1 Objectif et cadre méthodologique particulier

Cette phase (Phase 7) diffère des précédentes par sa contrainte : mesurer
la performance opérationnelle (latence, débit, concurrence, endurance)
**sans modifier** le modèle, l'API, l'authentification ou le pipeline de
détection — une contrainte de « mesure uniquement » stricte. Un point
méthodologique mérite d'être noté explicitement ici car il illustre le
principe de rigueur du Chapitre 5 appliqué à une situation imprévue : lors
du développement de cette phase, une action envisagée (élever
temporairement la limite de débit sur une instance secondaire jetable pour
isoler la capacité brute du système) a été **bloquée par un mécanisme de
sécurité automatisé**, au motif qu'il s'agissait d'un affaiblissement de
contrôle de sécurité non explicitement demandé. Le protocole de mesure a
été entièrement revu en conséquence : toutes les mesures HTTP ont été
effectuées contre l'instance de production réelle et non modifiée, en
respectant son budget réel de 120 requêtes/minute, et la capacité brute du
pipeline IA/blockchain a été mesurée **en-processus** (appels directs au
code, sans passer par HTTP ni par la limite de débit).

## 16.2 Latence

| Sous-système | Latence mesurée |
|---|---|
| Génération (simulateur) | 0,035 ms (moyenne) |
| Inférence IA (ensemble complet) | **275,3 ms (moyenne)**, p95=301,1ms, p99=319,9ms |
| Notarisation blockchain (1 enregistrement) | 0,027 ms |
| `GET /health` | 1,4 ms |
| `GET /health/detailed` | **109,6 ms** (voir §16.4) |
| Démarrage à froid (chargement modèle) | ~2698 ms |
| Démarrage complet de l'application | ~4010 ms |

## 16.3 La limite de débit déployée : un plafond de sécurité, pas de capacité

Un test de rafale contrôlé confirme que la limite de débit de production
(120 requêtes/minute) rejette effectivement les requêtes en excès (429
Too Many Requests) — un plafond volontaire, ~3,6× inférieur à la capacité
brute du pipeline mono-thread mesurée en-processus (voir §16.5).

## 16.4 Débit et le constat architectural le plus important de cette phase

Débit en flux continu, mono-thread, en-processus : **3,5 lectures/sec**
(ingestion complète : prétraitement + passe avant ensemble + XAI).

**Test de concurrence (1 à 1000 requêtes simultanées, en-processus, pool de
threads borné à 64)** : le débit ne s'améliore PAS avec la concurrence — il
**se dégrade** :

| Concurrence | Débit mesuré (req/s) |
|---|---|
| 1 | 3,60 |
| 10 | **5,04 (pic)** |
| 50 | 3,88 |
| 250 | 2,69 |
| 1000 | **2,37 (pire que la ligne de base à 1)** |

**Cause identifiée** : `api_server.py` définit `/api/detect` comme
`async def` mais appelle `_ml_detector.ingest()` **de façon synchrone et
directe**, sans `await asyncio.to_thread(...)` ni `run_in_executor`. Sur un
seul worker uvicorn (la configuration par défaut de ce déploiement), cet
appel bloquant gèle la boucle d'événements pendant toute sa durée — les
requêtes concurrentes ne s'exécutent donc pas en parallèle, elles se
sérialisent. Un test de sanité à faible volume, effectué en HTTP réel
contre le serveur de production non modifié, confirme ce comportement :
à 10 requêtes concurrentes, la latence p99 atteint **2987 ms**, soit
approximativement 10 × la latence d'une requête isolée — la signature
exacte d'une sérialisation complète.

## 16.5 Rapport entre plafond de sécurité et capacité réelle

Le plafond de 120 requêtes/minute (2 req/s) et la capacité brute
mono-thread (3,5 req/s) sont du même ordre de grandeur — mais pour des
raisons indépendantes : le premier est un choix de sécurité délibéré, la
seconde est une conséquence architecturale non intentionnelle. Cette
coïncidence n'a été mise en évidence QUE par la mesure ; elle n'aurait pas
pu être déduite de la seule lecture du code de configuration.

## 16.6 Endurance (soak test réduit)

Fenêtre de 5 minutes (réduite depuis un test d'endurance de production qui
durerait typiquement plusieurs jours — limite explicitement assumée, pas
présentée comme équivalente) : aucune croissance mémoire anormale observée
sur le processus de charge en-processus (+3,5 Mo sur 300s, 778 lectures
traitées). **Limite de mesure honnêtement rapportée** : la détection du
PID du serveur de production a échoué durant ce test (processus incorrect
identifié, rapportant une mémoire quasi nulle) — ce point de données est
explicitement écarté de l'analyse plutôt que présenté comme une preuve de
stabilité du serveur réel.

## 16.7 Score de performance global

**62,2/100** — le score le plus bas de toutes les phases du projet, tirant
vers le bas les dimensions « Concurrence/scalabilité horizontale » (30/100)
et « Efficacité des ressources sous charge » (45/100), tandis que la
latence unitaire (75/100), le démarrage (80/100) et la stabilité mémoire
(75/100) restent satisfaisants.

## 16.8 Recommandations directement actionnables

1. Déporter `_ml_detector.ingest()` sur un exécuteur
   (`asyncio.to_thread`) ou déployer plusieurs workers uvicorn.
2. Déporter ou rendre non bloquant l'appel `psutil.cpu_percent(interval=0.1)`
   dans `/health/detailed`.
3. Mettre en cache ou maintenir incrémentalement le résultat de
   `ledger.validate()` plutôt que de rehacher la chaîne complète à chaque
   appel de santé (coût croissant avec la durée de vie opérationnelle,
   Chapitre 9.5).
4. Si un débit soutenu supérieur à ~4 lectures/sec est requis en production,
   évaluer si les deux modèles de l'ensemble doivent tourner sur chaque
   lecture, ou si la mise à l'échelle horizontale (topologie Docker à 3
   services déjà conçue en Phase 6) est le levier le plus approprié plutôt
   que l'optimisation du chemin mono-instance.

## 16.9 Figures et rapports associés

`perf/reports/phase7_performance_report.{md,pdf}`,
`perf/reports/tables/phase7_performance_report.xlsx`, 7 figures dans
`perf/reports/figures/` (histogramme de latence, courbes de concurrence,
chronologie des ressources, coût de mise à l'échelle de la blockchain,
comparaison plafond/capacité).
