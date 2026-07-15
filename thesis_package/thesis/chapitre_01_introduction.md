# Chapitre 1 — Introduction

## 1.1 Contexte

Les réseaux électriques intelligents (*Smart Grids*) transforment la
distribution d'électricité en intégrant des capteurs numériques, des
compteurs communicants et des systèmes de contrôle automatisés au sein
d'une infrastructure historiquement analogique. Cette numérisation apporte
des gains réels — mesure fine de la consommation, détection automatisée des
pannes, équilibrage dynamique de la charge — mais expose simultanément le
réseau à une surface d'attaque nouvelle : falsification de données de
capteurs (FDIA — *False Data Injection Attack*), déni de service sur les
canaux de communication, fraude énergétique par manipulation des compteurs,
et défauts d'équipement pouvant être confondus avec des attaques ou
inversement.

Le contexte algérien, sur lequel ce travail s'appuie pour la simulation des
données (réseau Sonelgaz, climat nord-africain, cycles de consommation liés
au Ramadan et à la prière du vendredi), illustre un cas où la modernisation
du réseau électrique doit composer avec des contraintes opérationnelles et
climatiques spécifiques, tout en anticipant les mêmes menaces de
cybersécurité que les réseaux intelligents plus matures.

## 1.2 Objectifs du projet

Le sujet de ce Projet de Fin d'Études — *« Détection d'anomalies dans les
Smart Grids par IA et Blockchain : Application Mobile sécurisée »* — pose
un triangle d'exigences : (1) une intelligence artificielle capable de
détecter des anomalies et attaques sur les données de compteurs
intelligents, (2) une blockchain assurant la traçabilité et
l'inviolabilité des preuves de détection, et (3) une application mobile
sécurisée permettant l'accès à ces informations en situation de mobilité.

Ce projet a été conduit comme une démarche scientifique séquencée en
phases, plutôt que comme un développement monolithique : élimination
rigoureuse des biais méthodologiques (fuite de données), benchmark
comparatif contre des baselines fortes, étude d'ablation pour identifier ce
qui contribue réellement à la performance, évaluation de robustesse et de
calibration, validation sur données réelles indépendantes, durcissement
pour un usage en production, et profilage de performance systématique.
Cette démarche, documentée intégralement dans ce mémoire, est le principal
apport méthodologique du travail — au moins autant que le système
lui-même.

## 1.3 Périmètre réalisé et périmètre restant

Une clarification volontairement énoncée dès l'introduction, et non reléguée
au chapitre des limitations : le sujet complet exige la triade IA +
Blockchain + Application Mobile. **Ce mémoire documente un système complet
et rigoureusement validé pour les deux premiers piliers (IA et Blockchain)**,
opérant sur une blockchain à Preuve d'Autorité (*Proof-of-Authority*)
implémentée nativement, sans dépendance à une plateforme Ethereum ou
Hyperledger externe. **L'application mobile (Flutter/React Native) et les
Smart Contracts Solidity sur une blockchain publique/permissionnée externe
ne sont pas réalisés** à ce stade — ce point est développé au Chapitre 18
(Limitations) avec les raisons techniques et de priorisation qui ont guidé
ce choix, ainsi que le chemin de complétion proposé au Chapitre 19.

Cette transparence dès l'introduction est délibérée : un des fils
conducteurs de ce travail, visible à travers toutes les phases
scientifiques (Chapitres 10 à 14), est de rapporter les résultats
honnêtement — y compris quand ils sont défavorables à l'hypothèse initiale
(par exemple, le mécanisme d'attention du Transformer qui n'apporte pas de
gain mesurable, Chapitre 12) — plutôt que de présenter une image
idéalisée du système.

## 1.4 Contributions

Ce travail apporte quatre types de contributions, détaillées dans les
chapitres correspondants :

1. **Scientifique** — un protocole d'évaluation sans fuite de données
   (*data leakage*) pour la détection d'anomalies en séries temporelles
   multivariées (split temporel par compteur, Chapitre 5), une étude
   d'ablation systématique à 38 configurations expliquant *pourquoi*
   l'architecture Transformer fonctionne ou non sur ce type de données
   (Chapitre 12), et une validation croisée synthétique→réel sur le jeu de
   données public SGCC (Chapitre 14).
2. **Technique** — un pipeline d'IA temps réel avec explicabilité intégrée
   (attention + SHAP + integrated gradients, Chapitre 8), un registre
   blockchain à Preuve d'Autorité pour la notarisation des détections
   (Chapitre 9), et une architecture de production durcie (authentification
   JWT/RBAC, logging structuré, monitoring, Chapitre 15).
3. **Méthodologique** — une démarche de profilage de performance complète
   (latence, débit, concurrence, endurance) ayant révélé des constats
   architecturaux concrets et actionnables (Chapitre 16).
4. **Réflexive** — une auto-critique structurée des limites scientifiques et
   d'ingénierie du système, argumentée par des preuves mesurées plutôt que
   par des impressions (Chapitres 17 et 18).

## 1.5 Organisation du mémoire

Le mémoire suit la chronologie réelle du projet, qui a procédé par phases
scientifiques successives, chacune conditionnant la suivante :

- **Chapitres 2-3** posent le problème et situent le travail par rapport à
  l'état de l'art.
- **Chapitre 4** présente l'architecture globale du système.
- **Chapitres 5-9** couvrent la méthodologie, la génération de données, le
  pipeline d'apprentissage, l'explicabilité et l'intégration blockchain.
- **Chapitre 10** décrit le protocole expérimental commun à toutes les
  phases d'évaluation.
- **Chapitres 11-14** présentent les résultats de benchmark, d'ablation, de
  robustesse et de validation sur données réelles.
- **Chapitres 15-16** couvrent l'ingénierie de production et l'évaluation
  de performance.
- **Chapitres 17-20** discutent les résultats, énoncent les limitations,
  proposent des travaux futurs et concluent.

Les diagrammes d'architecture et UML référencés tout au long du mémoire se
trouvent dans `thesis_package/diagrams/` et `thesis_package/uml/`.
