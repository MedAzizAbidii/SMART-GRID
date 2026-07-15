# Contributions scientifiques et d'ingénierie

## Contributions scientifiques

1. **Diagnostic quantifié et correction d'une fuite de données classique**
   dans un pipeline de détection d'anomalies en séries temporelles —
   protocole de split temporel par compteur (`prepare_split_sequences()`)
   avec preuve chiffrée de l'impact du biais (F1 0,91→0,64).
2. **Étude d'ablation systématique à 38 configurations** isolant les
   contributions relatives de l'architecture, de la capacité, de
   l'entraînement, du seuil, des features et du temps d'exécution — avec
   classement quantifié des composants par ordre d'impact.
3. **Investigation causale, et non simplement descriptive, de
   l'inefficacité de l'attention** sur ce type de données : 4 preuves
   convergentes (permutation temporelle, comparaison dernier-pas-de-temps
   vs séquence complète, entropie de l'attention, séparabilité par
   feature unique), confirmées indépendamment sur un second jeu de
   données réel.
4. **Quantification du lien entre dérive de distribution et calibration** :
   démonstration que 98,3% d'une dégradation de robustesse
   (initialement attribuable au modèle) est en réalité un problème de
   calibration du seuil, réparable sans réentraînement.
5. **Validation croisée synthétique→réel** sur un jeu de données public
   indépendant (SGCC), distinguant explicitement les constats qui
   survivent au passage au réel de ceux qui ne survivent pas.

## Contributions d'ingénierie

1. **Pipeline de détection temps réel** avec explicabilité intégrée
   (integrated gradients en ligne, SHAP hors-ligne), gestion d'un tampon
   glissant par compteur et agrégation contextuelle inter-compteurs
   (`ZoneAggregator`).
2. **Registre blockchain Proof-of-Authority natif**, sans dépendance à une
   plateforme externe, avec validation d'intégrité complète
   (chaînage, signatures, racine de transactions).
3. **Durcissement de production complet** : authentification JWT/RBAC,
   limitation de débit à budgets différenciés, logging structuré corrélé
   par requête, monitoring Prometheus, audit de sécurité ayant corrigé 17
   CVE et 6 bugs réels (dont un défaut de routeur détecté par la propre
   suite de tests du projet).
4. **Suite de profilage de performance de bout en bout** (latence, débit,
   concurrence de 1 à 1000 requêtes, endurance) ayant révélé et localisé
   précisément un défaut architectural de scalabilité (appel bloquant
   dans un gestionnaire asynchrone) invisible à la seule revue de code.
5. **Infrastructure de recherche reproductible** : chaque phase
   scientifique est un module Python autonome et testé automatiquement
   (46 à 14 tests selon le module), réutilisant un socle commun
   (`prepare_split_sequences`, métriques partagées) pour garantir la
   comparabilité des résultats entre phases.

## Ce qui distingue ce travail d'un projet de développement classique

La majorité des contributions ci-dessus ne sont pas des fonctionnalités
ajoutées mais des **résultats de mesure** — y compris des résultats
défavorables à l'hypothèse initiale (l'attention n'aide pas, le modèle
proposé perd face aux baselines supervisées, le système ne scale pas
horizontalement en l'état). Le choix constant de rapporter ces résultats
avec la même rigueur que les résultats favorables, et de les investiguer
plutôt que de les taire, constitue en soi une contribution méthodologique
transversale au projet.
