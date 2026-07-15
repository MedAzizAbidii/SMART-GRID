# Chapitre 4 — Architecture du système

## 4.1 Vue d'ensemble

L'architecture globale (Figure 4.1,
`thesis_package/diagrams/rendered/00_overall_architecture.png`) organise le
système en cinq blocs fonctionnels : génération de données, pipeline IA,
blockchain, backend (API), et interface (tableau de bord). Deux blocs
prévus par le sujet initial — application mobile et Smart Contract Solidity
— apparaissent en pointillés sur ce diagramme pour matérialiser
explicitement le périmètre non réalisé (Chapitre 18), plutôt que d'être
omis silencieusement.

Le flux principal traverse ces blocs de façon strictement séquentielle pour
chaque lecture de compteur : génération/réception → prétraitement →
inférence → explicabilité → décision → (si anomalie confirmée)
notarisation blockchain → journalisation → exposition via l'API vers le
tableau de bord.

## 4.2 Génération de données (simulateur)

Le simulateur (`data_generation/generate_realistic_dataset.py`, Figure 4.2,
`01_simulator_architecture.png`) modélise 50 compteurs répartis sur 4 zones
géographiques inspirées du réseau algérien (Alger, Oran, Constantine,
Annaba), avec 5 types de consommateurs (résidentiel 55%, commercial 25%,
industriel 13%, mosquée 4%, hôpital 4%) et des effets contextuels réalistes
(climat saisonnier, cycle Ramadan, creux de la prière du vendredi,
génération solaire pour 25% des compteurs éligibles). Cinq types
d'attaques sont injectés à un taux réaliste de ~1,5% des lectures (détail
au Chapitre 6).

## 4.3 Flux de données

Le diagramme de flux de données (Figure 4.3, `02_data_flow.png`) détaille
la transformation d'une lecture individuelle : validation Pydantic →
tampon glissant par compteur → ingénierie de features (moyennes/écarts
mobiles, agrégats de zone, encodages cycliques heure/jour) → normalisation
(ajustée sur l'ensemble d'entraînement uniquement, Chapitre 5) → tenseur de
séquence → passe avant du modèle → score de reconstruction → calibration →
comparaison au seuil adaptatif → décision, avec branchement conditionnel
vers la notarisation blockchain.

## 4.4 Pipeline IA

Le pipeline IA complet (Figure 4.4, `03_ai_pipeline.png`) distingue la
préparation des données (split temporel, normalisation, fenêtrage) du
modèle proprement dit (encodeur-décodeur Transformer, Chapitre 7) et de la
couche d'explicabilité (attention, integrated gradients, SHAP hors-ligne,
Chapitre 8). Le détecteur de production est un `EnsembleDetector`
combinant deux instances du même type de modèle : une optimisée pour le
rappel (« v2 »), une pour la précision (« v3 ») — l'alarme est déclenchée
par v2, la confiance est graduée par l'accord ou non de v3.

## 4.5 Pipelines d'entraînement et d'inférence

Les Figures 4.5 (`04_training_pipeline.png`) et 4.6
(`05_inference_pipeline.png`) séparent délibérément le cycle de vie
hors-ligne (entraînement, sélection de seuil, évaluation sur test retenu)
du cycle de vie temps réel (une requête HTTP → décision en quelques
centaines de millisecondes). Cette séparation reflète une décision de
conception importante : le pipeline d'entraînement applique un split
temporel strict par compteur (`prepare_split_sequences()`, détaillé au
Chapitre 5) pour éliminer la fuite de données, tandis que le pipeline
d'inférence traite un flux continu sans notion de split — les deux
pipelines partagent le même code de prétraitement mais des rôles
temporels distincts.

## 4.6 Intégration blockchain

Le registre à Preuve d'Autorité (Figure 4.7, `06_blockchain_architecture.png`,
détaillé au Chapitre 9) notarise chaque anomalie confirmée (non dédupliquée)
sous forme d'un bloc signé par l'une des 4 autorités désignées, selon une
rotation round-robin. Le chaînage SHA-256 des blocs permet une validation
d'intégrité de complexité linéaire en le nombre total d'enregistrements
notariés — une caractéristique dont le coût, négligeable aujourd'hui, est
quantifié à l'échelle par le profilage du Chapitre 16.

## 4.7 Architecture du tableau de bord

Le tableau de bord (Figure 4.8, `07_dashboard_architecture.png`) est une
page unique auto-contenue utilisant un moteur de templating maison
(`support.js`, « dc-runtime ») s'appuyant sur React chargé depuis un CDN.
Un widget de santé opérationnelle, ajouté lors du durcissement de
production (Chapitre 15), sonde `/health/detailed` toutes les 5 secondes de
façon totalement indépendante du reste de l'application — un choix de
conception délibéré pour ajouter une fonctionnalité opérationnelle sans
risque de régression sur le bundle applicatif existant.

## 4.8 Architecture de déploiement

La topologie de déploiement à 3 conteneurs (Figure 4.9,
`08_deployment_architecture.png`) sépare le tableau de bord (nginx), le
backend (FastAPI) et l'inférence (microservice optionnel) — cette
séparation permet en principe de mettre à l'échelle l'inférence
indépendamment du reste, bien que cette topologie **n'ait pas été
vérifiée par une construction Docker réelle** (absence de Docker sur la
machine de développement, Chapitre 15.4), une limite assumée explicitement.

## 4.9 Architecture de sécurité

L'architecture de sécurité (Figure 4.10, `09_security_architecture.png`)
superpose limitation de débit (120 requêtes/minute, 10/minute sur
l'authentification), authentification JWT et autorisation par rôle à 4
niveaux hiérarchiques (`viewer < analyst < grid_operator < administrator`).
Un compromis documenté explicitement : les points de terminaison en lecture
seule (dont `/api/detect`) restent volontairement non authentifiés pour ne
pas casser le fonctionnement existant du tableau de bord — un choix de
conception assumé, pas un oubli (Chapitre 15.2).

## 4.10 Architecture de monitoring

L'architecture de monitoring et de journalisation (Figure 4.11,
`10_monitoring_architecture.png`) répartit les événements sur 5 flux JSON
rotatifs distincts (cycle de vie applicatif, prédictions, attaques
confirmées, opérations blockchain, erreurs système), corrélés par un
identifiant de requête (`request_id`). Le profilage du Chapitre 16 a
identifié un constat concret sur cette architecture : l'endpoint
`/health/detailed` bloque la boucle d'événements pendant ~100ms à chaque
appel (appel synchrone `psutil.cpu_percent(interval=0.1)`), sondé toutes les
5 secondes par le widget de tableau de bord — un exemple direct de la valeur
du profilage systématique pour révéler des interactions non anticipées
entre composants conçus indépendamment.
