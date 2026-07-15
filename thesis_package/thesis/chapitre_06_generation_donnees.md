# Chapitre 6 — Génération du jeu de données

## 6.1 Pourquoi un simulateur plutôt que des données réelles seules

L'accès à des données réelles de compteurs intelligents étiquetées pour la
cybersécurité (attaques confirmées, et non simple fraude après audit) est
extrêmement rare publiquement. Ce projet adopte donc une stratégie à deux
niveaux, assumée et documentée : un simulateur réaliste
(`data_generation/generate_realistic_dataset.py`) pour l'ensemble des
phases de recherche (benchmark, ablation, robustesse, calibration), et une
validation externe sur un jeu de données réel de fraude énergétique (SGCC,
Chapitre 14) pour tester la généralisation des constats obtenus sur
synthétique.

## 6.2 Modélisation du contexte physique et social

Le simulateur (`RealisticDatasetGenerator`) modélise le réseau de
distribution algérien (Sonelgaz) avec un souci de réalisme contextuel
directement intégré au code, plutôt qu'ajouté après coup :

- **Climat** : températures hivernales de 8-12°C et estivales de 38-45°C
  dans le nord de l'Algérie, influençant la consommation de chauffage/
  climatisation.
- **Cycles sociaux** : décalage de consommation lié au Ramadan (pics
  suhoor/iftar), creux de consommation commerciale le vendredi entre 12h et
  14h (prière).
- **Saisonnalité** : dominance de la climatisation en été (juin-août),
  multipliant la consommation résidentielle par 2 à 3 par rapport aux
  autres saisons.
- **Bruit multi-niveaux** : bruit de compteur, bruit de processus, gigue de
  communication — superposés plutôt qu'un bruit gaussien unique.
- **Production solaire** : 25% des compteurs résidentiels/commerciaux sont
  équipés d'installations solaires de toiture (1,5 à 4,0 kW), dont la
  production est soustraite de la consommation nette selon l'heure, le
  mois et la couverture nuageuse.

## 6.3 Zones et types de consommateurs

Quatre zones géographiques, chacune avec un profil dominant :

| Zone | Ville | Profil | Compteurs |
|---|---|---|---|
| A | Alger | résidentiel dense | 12 |
| B | Oran | commercial | 13 |
| C | Constantine | mixte | 12 |
| D | Annaba | industriel léger | 13 |

Cinq types de consommateurs : résidentiel (55%), commercial (25%),
industriel (13%), mosquée (4%, profil à pic marqué le vendredi et pendant
le Ramadan), hôpital (4%, profil quasi plat sur 24h, cohérent avec une
activité continue).

## 6.4 Taux d'attaque réaliste : un choix délibéré

Le simulateur injecte des attaques à un taux d'environ **1,5%** des
lectures — un choix explicitement comparé, dans la documentation du code,
à un taux naïf de 48% qui serait irréaliste et faciliterait artificiellement
la tâche de détection. Ce choix a une conséquence méthodologique directe et
assumée : à ce taux réaliste, le déséquilibre de classes est sévère (le
« paradoxe de l'exactitude » — une accuracy de 96% peut correspondre à un
détecteur qui ne détecte presque rien), ce qui justifie l'usage systématique
du F1-score, du ROC-AUC et du PR-AUC plutôt que de la seule exactitude
dans l'ensemble de ce mémoire.

## 6.5 Les cinq types d'attaques simulées

| Attaque | Mécanisme d'injection | Signal caractéristique |
|---|---|---|
| **FDIA_voltage** | Falsification du capteur de tension (+5 à +12%) | Tension anormalement haute, masquant une surcharge réelle au SCADA |
| **FDIA_subtle** | Inflation coordonnée et discrète (4-9%) de tous les compteurs d'une même zone simultanément | Indétectable sans contexte temporel/inter-compteurs — conçue pour tester la robustesse au-delà d'un seuil univarié |
| **DoS** | Rejeu de la dernière lecture connue (données figées) | Absence de variation naturelle dans le flux |
| **Fraude énergétique** | Consommation ×1,8-3,5, facteur de puissance forcé à 0,45-0,70 (signature d'un contournement de câblage) | Sous-déclaration ou bypass physique du compteur |
| **Défaut d'équipement (Fault)** | Creux de tension ×0,72-0,88, pic de courant ×1,4-2,2 | Signature électrique d'une panne matérielle, à distinguer d'une attaque |

La coexistence de « Fraude/attaque » et « Défaut d'équipement » dans le même
jeu de données est délibérée : un système de détection opérationnel doit
pouvoir distinguer une anomalie malveillante d'une panne bénigne, une
distinction non triviale que le module `classify_attack_type` du pipeline
d'inférence adresse explicitement (Chapitre 7).

## 6.6 Le cas FDIA_subtle : conçu pour être difficile

L'attaque `FDIA_subtle` mérite une mention séparée : elle est conçue
spécifiquement pour rester à l'intérieur de la plage de variation normale
d'un compteur pris isolément (falsification de 4-9% seulement, contre 5-12%
pour la variante `FDIA_voltage`), en misant sur la cohérence artificielle
de plusieurs compteurs d'une même zone plutôt que sur l'amplitude du
signal. Cette conception a une importance directe pour l'évaluation de la
Phase 3 (Chapitre 13) : c'est précisément ce type de signal — cohérent
inter-compteurs mais discret individuellement — qui teste la capacité du
modèle à exploiter l'agrégat de zone (`ZoneAggregator`, Chapitre 7.4)
plutôt qu'une seule lecture univariée.

## 6.7 De la génération à l'entraînement

Les jeux de données produits par le simulateur alimentent directement le
pipeline d'entraînement (Chapitre 7) via le format CSV standard
(`donnees_smart_meters.csv`) partagé par toutes les phases scientifiques,
garantissant que le prétraitement, le split et l'évaluation restent
identiques quelle que soit la phase qui consomme les données.
