# Plan et script de présentation de soutenance (~20 minutes)

Format indicatif : 20 minutes de présentation + 10-15 minutes de questions.
Adapter le minutage exact aux consignes de l'établissement.

---

## Diapositive 1 — Titre (30s)

**Contenu** : Titre du projet, nom, encadrant, établissement, date.

**Script** : « Bonjour, je vais présenter mon Projet de Fin d'Études :
Détection d'anomalies dans les Smart Grids par IA et Blockchain,
Application Mobile sécurisée. »

## Diapositive 2 — Contexte et problème (1 min 30)

**Contenu** : Smart Grid = numérisation du réseau électrique + nouvelle
surface d'attaque (FDIA, DoS, fraude, défauts). Diagramme : aucun requis,
texte + éventuellement une image de compteur intelligent.

**Script** : « Les réseaux électriques intelligents apportent des gains
réels de mesure et d'automatisation, mais exposent le réseau à des attaques
inédites : falsification de données de capteurs, déni de service, fraude
énergétique. Mon projet répond à deux besoins : détecter ces anomalies en
temps réel, et prouver que la détection n'a pas été falsifiée après coup. »

## Diapositive 3 — Objectifs et périmètre (1 min)

**Contenu** : Le triangle IA + Blockchain + Mobile. **Être direct sur le
périmètre réalisé dès cette diapositive** — ne pas attendre la fin pour
l'annoncer.

**Script** : « Le sujet posait trois piliers : Intelligence Artificielle,
Blockchain, et Application Mobile sécurisée. Ce projet réalise et valide
scientifiquement les deux premiers piliers de façon complète. L'application
mobile n'a pas été développée — j'y reviendrai avec les raisons de
priorisation et le chemin de complétion proposé. »

## Diapositive 4 — Architecture globale (1 min 30)

**Contenu** : Figure `diagrams/rendered/00_overall_architecture.png`.

**Script** : « Voici l'architecture globale : un simulateur génère des
lectures de compteurs réalistes, un pipeline IA les analyse, les anomalies
confirmées sont notariées sur un registre blockchain, le tout exposé via
une API sécurisée vers un tableau de bord. »

## Diapositive 5 — Démarche scientifique en 8 phases (1 min)

**Contenu** : Liste des 8 phases (Fuite de données → Benchmark → Ablation →
Investigation → Robustesse → Calibration → Données réelles → Production →
Performance). Insister sur le **séquencement**.

**Script** : « Plutôt qu'un développement monolithique, ce projet a
procédé par 8 phases scientifiques séquentielles, chacune posant une
question précise et y répondant par la mesure — c'est cette démarche,
autant que le système, que je vais illustrer. »

## Diapositive 6 — Le piège de la fuite de données (1 min 30)

**Contenu** : F1 validation 0,91 vs test 0,64.

**Script** : « Premier résultat : un audit initial a révélé que le seuil de
décision était sélectionné sur les mêmes données que celles rapportées
comme résultat final — un jeu de test qui n'en était pas un. Après
correction — split temporel strict par compteur — le F1 honnête est de
0,64, contre 0,91 en apparence. C'est ce chiffre corrigé que je retiens
pour toute la suite. »

## Diapositive 7 — Benchmark comparatif (2 min)

**Contenu** : Tableau simplifié (XGBoost 0,986 / Transformer AE 0,582 /
Isolation Forest 0,082), avec la distinction supervisé/non supervisé mise
en évidence visuellement (couleur).

**Script** : « Face à des modèles supervisés qui connaissent les
signatures d'attaques, mon modèle non supervisé est nettement moins bon.
Mais la comparaison pertinente est différente : parmi les méthodes ne
nécessitant AUCUN label d'attaque — donc capables en principe de détecter
une attaque inédite — mon modèle est le meilleur, significativement, selon
un test de McNemar. C'est le compromis assumé de ce projet : moins de
performance brute, contre la capacité visée de détecter l'inconnu. »

## Diapositive 8 — Le résultat qui a surpris : l'attention n'aide pas (2 min)

**Contenu** : Figure `investigation/plots/attention_analysis.png` ou le
tableau d'ablation simplifié.

**Script** : « Résultat le plus surprenant : retirer le mécanisme
d'attention du Transformer améliore légèrement la performance. Plutôt que
d'ignorer ce résultat gênant pour mon hypothèse de départ, je l'ai
investigué : un test de permutation temporelle montre que le modèle
n'exploite quasiment pas l'ordre des observations dans le temps — donc
l'attention, conçue précisément pour cela, n'a rien à exploiter sur ces
données. Ce résultat s'est confirmé sur un second jeu de données réel,
indépendant. »

## Diapositive 9 — Robustesse et calibration (2 min)

**Contenu** : Score composite 63,8/100 ; le tableau dérive/recalibration
(FPR 3,6%→100%→5,2%).

**Script** : « Le système résiste bien au fonctionnement normal — aucune
fuite mémoire, zéro erreur sur 29 000 appels — mais un simple décalage de
distribution de 0,25 écart-type sature les fausses alertes à 100%.
Heureusement, une simple recalibration périodique, sans toucher au modèle,
récupère 98% de cette dégradation — c'est le résultat le plus directement
exploitable de mon projet. »

## Diapositive 10 — Validation sur données réelles (1 min 30)

**Contenu** : Tableau SGCC simplifié, mention Zheng et al. 2018.

**Script** : « Pour valider au-delà du simulateur, j'ai testé sur SGCC, un
jeu de données réel de fraude énergétique chinois de plus de 42 000
consommateurs. Les constats qualitatifs — l'attention n'aide pas, les
arbres supervisés gagnent — se confirment. La performance absolue, elle,
chute du synthétique au réel : un avertissement à garder en tête. »

## Diapositive 11 — Blockchain et sécurité (1 min 30)

**Contenu** : Figure `diagrams/rendered/06_blockchain_architecture.png`.

**Script** : « Chaque anomalie confirmée est notariée sur un registre à
Preuve d'Autorité — 4 autorités désignées, chaînage SHA-256, coût mesuré
de 0,027 milliseconde par enregistrement. Un audit de sécurité a par
ailleurs identifié et corrigé 6 vulnérabilités réelles, dont 17 CVE de
dépendances. »

## Diapositive 12 — Démonstration live (3-5 min)

Voir `script_demonstration_live.md`.

## Diapositive 13 — Ce que le profilage a révélé (1 min 30)

**Contenu** : Figure `perf/reports/figures/03_concurrency_throughput.png`.

**Script** : « Dernière phase : profiler la performance sous charge. Le
constat le plus important : la capacité ne s'améliore pas avec la
concurrence, elle se dégrade — de 5 à 2,4 requêtes par seconde de 10 à
1000 clients simultanés. La cause est précisément identifiée : un appel
bloquant dans un gestionnaire censé être asynchrone, qui sérialise tout
sur un seul worker. C'est un problème localisé et directement corrigible,
pas un défaut d'architecture diffus. »

## Diapositive 14 — Limitations assumées (1 min)

**Contenu** : Liste courte : mobile absent, Solidity absent, Docker jamais
construit réellement, modèle de production non ré-entraîné sous le
protocole sans fuite.

**Script** : « Pour être direct sur les limites : l'application mobile et
les Smart Contracts ne sont pas réalisés ; la conteneurisation Docker n'a
jamais été testée par une construction réelle faute de Docker disponible ;
et le modèle actuellement en production est antérieur à la correction du
protocole de fuite de données — un point à corriger avant tout usage réel. »

## Diapositive 15 — Conclusion et travaux futurs (1 min)

**Script** : « Ce projet démontre que la valeur d'un système de sécurité
ne vient pas de l'affirmation qu'il est parfait, mais de la rigueur avec
laquelle ses limites ont été mesurées plutôt que supposées. Merci de votre
attention, je suis prêt à répondre à vos questions. »
