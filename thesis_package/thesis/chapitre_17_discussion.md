# Chapitre 17 — Discussion

## 17.1 Répondre aux questions de recherche du Chapitre 2

**Q1 (fuite de données).** Oui, un protocole naïf surestime la
performance de façon substantielle et quantifiée : F1 0,91 (validation,
biaisé) contre 0,64 (test retenu, honnête) — un écart qui, s'il n'avait pas
été détecté et corrigé au tout début du projet (Phase 0), aurait vicié
l'ensemble des résultats scientifiques ultérieurs.

**Q2 (positionnement du Transformer AE).** Le modèle proposé perd
nettement face aux méthodes supervisées (XGBoost F1=0,986 contre 0,582)
mais **gagne significativement** face aux autres méthodes ne nécessitant
aucun label (LSTM AE, OCSVM, Isolation Forest) — la comparaison
opérationnellement pertinente pour la détection d'attaques inconnues.

**Q3 (l'attention aide-t-elle ?).** Non, mesuré de façon convergente sur
deux jeux de données indépendants (synthétique, Chapitre 12 ; réel SGCC,
Chapitre 14) et expliqué par une cause identifiée (absence de structure
temporelle exploitable dans les fenêtres de 8 lectures) plutôt que
simplement constaté.

**Q4 (robustesse).** Le système est fiable en fonctionnement stable (100/100
en fiabilité, aucune fuite mémoire) mais fragile face à la dérive de
distribution (24,7/100) et aux données manquantes (22,3/100) — ses deux
points de rupture les plus sérieux.

**Q5 (calibration).** Les scores sont bien calibrés en régime stable
(ECE=0,024) mais la calibration se dégrade sous dérive exactement comme la
détection elle-même — et se répare, de façon spectaculaire (98,3% de
récupération du FPR), par une simple recalibration périodique.

**Q6 (synthétique → réel).** Trois constats qualitatifs survivent
(l'attention n'aide pas, Transformer≈LSTM, les arbres supervisés gagnent) ;
la performance absolue, elle, ne survit pas (~0,99 → ~0,75) — le
synthétique était plus facile, un avertissement méthodologique à
généraliser au-delà de ce projet.

**Q7 (performance en production).** Le système ne scale pas horizontalement
en l'état à cause d'un unique appel bloquant dans un gestionnaire
asynchrone — un problème précisément localisé et directement corrigible
(Chapitre 16.8), pas un problème architectural diffus.

## 17.2 Le fil conducteur : la mesure révèle ce que l'intuition ne prédit pas

Trois résultats de ce mémoire auraient pu être manqués sans mesure
systématique, et illustrent la valeur de la démarche scientifique suivie
plutôt que d'une simple implémentation :
1. L'attention, censée être un atout architectural, s'avère neutre voire
   contre-productive sur ce type de données (Chapitre 12).
2. Les attaques « déguisées » pour échapper à la détection deviennent, sur
   ce système, PLUS détectables, pas moins (Chapitre 13.3).
3. Le plafond de sécurité (limite de débit) et le plafond de capacité brute
   du système sont numériquement proches, mais pour des raisons totalement
   indépendantes, révélées uniquement par le profilage (Chapitre 16.5).

## 17.3 Le compromis label-free vs performance : un choix, pas un renoncement

Le Chapitre 11.5 a énoncé le compromis central du projet sans détour. Ce
chapitre en tire une conséquence pratique pour un déploiement réel : les
deux familles de modèles (supervisée et non supervisée) ne sont pas
mutuellement exclusives. Un déploiement pourrait raisonnablement combiner
un modèle supervisé pour les types d'attaques connus (performance
maximale) et le Transformer Autoencoder proposé comme filet de sécurité
pour tout signal ne correspondant à aucune signature connue — une
architecture hybride non implémentée dans ce projet mais directement
suggérée par les résultats des Chapitres 11 et 14.

## 17.4 Le compromis performance vs scalabilité horizontale

Le Chapitre 16 révèle un compromis distinct : la latence unitaire de
l'ensemble à deux modèles (~275ms) est acceptable pour un usage isolé, mais
devient le facteur limitant de la scalabilité horizontale une fois la
sérialisation de concurrence corrigée (Chapitre 16.8) — à ce moment-là, la
question redevient : le gain de précision de l'ensemble à deux modèles
justifie-t-il de doubler le coût de calcul par rapport à un seul modèle ?
Cette question n'a pas été évaluée quantitativement dans ce projet et
constitue une piste directe pour le Chapitre 19.

## 17.5 Sur l'honnêteté scientifique comme méthode, pas comme posture

Ce mémoire a fait le choix, à chaque phase, de rapporter les résultats
défavorables (attention neutre, performance très inférieure aux modèles
supervisés, plafond de concurrence non anticipé, blockchain jamais
construite via Docker) avec la même rigueur que les résultats favorables.
Ce choix n'est pas une simple posture de transparence académique : il a eu
une conséquence directe sur la trajectoire du projet lui-même — c'est
précisément parce que le résultat « l'attention n'aide pas » (Chapitre
12.3) n'a pas été écarté que la phase d'investigation dédiée (Chapitre
12.4) a pu être menée, et c'est parce que la dégradation sous dérive
(Chapitre 13.2) n'a pas été minimisée que la phase de calibration
(Chapitre 13.6) a pu produire son résultat le plus actionnable (recalibration
= 98,3% de récupération). L'honnêteté scientifique, dans ce projet, a
fonctionné comme un moteur de découverte, pas seulement comme une exigence
de présentation.
