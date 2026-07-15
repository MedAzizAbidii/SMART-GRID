# Résumé du projet et résumé technique

## Résumé du projet (pour un public non technique — jury mixte, page de garde)

Les réseaux électriques intelligents (Smart Grids) modernisent la
distribution d'électricité, mais exposent le réseau à de nouvelles
attaques : falsification de données, coupures de communication provoquées,
fraude énergétique. Ce projet construit et valide scientifiquement un
système qui détecte automatiquement ces anomalies à partir des lectures de
compteurs intelligents, explique sa décision à un opérateur humain, et
enregistre chaque détection confirmée sur un registre infalsifiable
inspiré des technologies blockchain.

Plutôt que de se limiter à faire fonctionner un prototype, ce travail a
suivi une démarche scientifique complète en 8 étapes : correction d'un
biais de mesure classique, comparaison à des méthodes concurrentes,
compréhension fine de ce qui contribue réellement à la performance,
test de résistance à des conditions dégradées, validation sur des données
réelles indépendantes, puis mise en conditions de production et mesure de
performance sous charge. Chaque étape a produit des résultats mesurés et
rapportés honnêtement — y compris lorsque ces résultats contredisaient
l'hypothèse de départ, comme la découverte que le mécanisme d'intelligence
artificielle le plus sophistiqué du modèle (l'attention) n'apportait
finalement aucun bénéfice mesurable sur ce type de données.

Le sujet initial visait un triptyque Intelligence Artificielle + Blockchain
+ Application Mobile. Ce projet réalise et documente rigoureusement les
deux premiers piliers ; l'application mobile reste à développer, un
point assumé sans détour plutôt que dissimulé.

## Résumé technique (pour la première page du mémoire / abstract)

**Architecture** : pipeline de détection d'anomalies temps réel basé sur un
autoencodeur Transformer (dim=128, 4 têtes d'attention, 3 couches,
seq_len=8), déployé en configuration d'ensemble à deux modèles (optimisé
rappel + optimisé précision). Explicabilité intégrée via attention,
integrated gradients (temps réel) et SHAP (analyse hors-ligne). Notarisation
des détections confirmées sur un registre Proof-of-Authority local (SHA-256,
4 autorités, rotation round-robin). Backend FastAPI avec authentification
JWT/RBAC à 4 rôles, limitation de débit, logging structuré sur 5 flux JSON,
monitoring Prometheus.

**Validation scientifique** : protocole d'évaluation sans fuite de données
(split temporel par compteur, scaler ajusté sur train uniquement) —
correction mesurée d'un biais de F1 0,91→0,64. Benchmark contre 6 baselines
(F1 proposé=0,582, significativement supérieur aux méthodes non supervisées
concurrentes, McNemar p<10⁻⁹, significativement inférieur aux méthodes
supervisées). Étude d'ablation à 38 configurations révélant que le
mécanisme d'attention n'améliore pas la performance (confirmé sur données
réelles indépendantes, SGCC, 42 372 consommateurs, AUC=0,655). Score de
robustesse composite 63,8/100 (fragilité identifiée sous dérive de
distribution, corrigée à 98,3% par recalibration). Score de préparation à
la production ~80/100. Score de performance opérationnelle 62,2/100
(goulot d'étranglement de concurrence précisément localisé : appel
bloquant synchrone dans un gestionnaire asynchrone).

**Limitations assumées** : application mobile et Smart Contracts non
réalisés ; conteneurisation Docker non vérifiée par une construction
réelle ; modèle de production actuel antérieur à la correction du
protocole de fuite de données.
