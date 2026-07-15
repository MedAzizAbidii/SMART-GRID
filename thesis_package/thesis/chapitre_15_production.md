# Chapitre 15 — Ingénierie de production

## 15.1 Objectif de cette phase

Après cinq phases scientifiques (Chapitres 11-14) portant sur la validité
du modèle, cette phase (Phase 6) transforme le système en une plateforme
opérable, sans toucher à un seul poids de modèle ni à un seul résultat
scientifique déjà validé. Le principe directeur, énoncé dans le code lui
même : *« transformer le système (scientifiquement figé) en une plateforme
de qualité industrielle — sans toucher au moindre poids de modèle, jeu de
données, ou résultat scientifique »*.

## 15.2 Authentification et autorisation

JWT (HS256) avec 4 rôles hiérarchiques (`viewer < analyst < grid_operator <
administrator`, Chapitre 4.9). Décision de conception assumée
explicitement : les points de terminaison en lecture seule, dont
`/api/detect`, restent **volontairement non authentifiés**, pour ne pas
casser le fonctionnement du tableau de bord existant qui les sonde déjà
sans jeton — un compromis documenté, pas un oubli.

## 15.3 Audit de sécurité et vulnérabilités corrigées

Un audit `pip-audit` a révélé **18 CVE** connues sur 6 dépendances. 17 ont
été corrigées par mise à jour (`starlette`, `cryptography`, `pillow`,
`setuptools`) ; 1 résiduelle acceptée (`ecdsa`, attaque temporelle Minerva,
sans correctif amont — acceptée car le système signe ses JWT en HS256/HMAC,
pas en ECDSA). Deux CVE nommément identifiées dans `starlette` méritent
mention : une possibilité de déni de service par absence de limite de
taille sur le parsing de formulaire (exploitable directement via le nouvel
endpoint de connexion), et une vulnérabilité SSRF de `StaticFiles` sous
Windows via chemins UNC.

**Six bugs réels, distincts des CVE de dépendances, ont été identifiés et
corrigés** durant cette phase (et non de simples fonctionnalités
ajoutées) :
1. Combinaison CORS wildcard + `allow_credentials=True` — invalide et
   non sécurisée.
2. Les 17 CVE ci-dessus.
3. Incompatibilité `passlib`/`bcrypt` (plantage sur bcrypt≥4.1) — corrigée
   par appel direct à `bcrypt`.
4. Mots de passe par défaut en clair stockés à côté de leurs hachages —
   supprimés.
5. Un singleton de routeur au niveau module (`build_health_router`)
   accumulant des routes dupliquées à chaque appel — **détecté par la
   propre suite de tests du projet** (2 tests en échec), un exemple concret
   de la valeur des tests automatisés au-delà de la simple couverture de
   code.
6. Absence de limite de débit spécifique à la connexion (le budget général
   de 120/minute autorisait 120 tentatives de mot de passe/minute) — un
   budget séparé de 10/minute a été ajouté.

## 15.4 Score de préparation à la production

| Dimension | Score /100 |
|---|---|
| Gestion de configuration | 90 |
| Durcissement API | 85 |
| Authentification & autorisation | 80 |
| Logging | 90 |
| Monitoring | 85 |
| Récupération d'erreur | 75 |
| Tests | 90 (46/46 tests, 90% de couverture) |
| Sécurité | 80 |
| **Conteneurisation** | **55 (le plus faible)** |
| Documentation | 90 |
| **Global** | **~80/100** |

## 15.5 La limite la plus honnête de cette phase

La conteneurisation Docker (3 services : dashboard/backend/inférence,
Chapitre 4.8) a été **conçue et revue statiquement** (existence de chaque
chemin `COPY`, validation syntaxique YAML, correspondance des imports) mais
**jamais construite ni exécutée réellement**, faute de Docker installé sur
la machine de développement utilisée pour ce projet. Ce point est
explicitement le score le plus bas du tableau ci-dessus (55/100) et doit
être vérifié (`docker compose up --build`) sur une machine dotée de Docker
avant tout déploiement réel — une action de suivi concrète, pas une
formule de prudence générique.

## 15.6 Observabilité

Cinq flux de logs JSON structurés et séparés (cycle de vie, prédictions,
attaques, opérations blockchain, erreurs système), corrélés par un
identifiant de requête. Endpoints `/health`, `/health/ready`,
`/health/detailed`, `/metrics` (Prometheus). **Point révélé seulement par
le profilage de la phase suivante (Chapitre 16)** : `/health/detailed`
contient un appel bloquant `psutil.cpu_percent(interval=0.1)` non déporté
sur un exécuteur, gelant la boucle d'événements ~100ms à chaque appel — une
limite non visible lors de la revue de code initiale de cette phase, et
découverte uniquement par la mesure systématique.

## 15.7 Intégration additive, pas intrusive

Le widget de santé du tableau de bord (Chapitre 4.7) illustre le principe
de conception suivi pour cette phase : ajouter des capacités opérationnelles
**sans modifier** le bundle applicatif existant (dashboard React-like), en
JavaScript vanille totalement autonome, pour un risque de régression nul
sur les fonctionnalités déjà validées.
