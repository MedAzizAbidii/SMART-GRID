# Chapitre 20 — Conclusion

## 20.1 Ce qui a été démontré

Ce mémoire documente la conception, la validation scientifique rigoureuse
et le durcissement opérationnel d'une plateforme de détection d'anomalies
pour réseaux électriques intelligents, combinant un pipeline
d'apprentissage automatique explicable (Transformer Autoencoder, attention,
SHAP, integrated gradients) et un registre blockchain à Preuve d'Autorité
pour la notarisation inviolable des détections confirmées. Au-delà du
système lui-même, la contribution la plus durable de ce travail est sa
**démarche** : huit phases séquentielles, chacune posant une question
précise et y répondant par une mesure reproductible plutôt que par une
affirmation — de l'élimination d'un biais méthodologique classique (fuite
de données, Phase 0) jusqu'au profilage de performance sous charge réelle
(Phase 7).

## 20.2 Les résultats qui comptent

Trois résultats résument, à eux seuls, l'apport scientifique du projet :

1. **Le mécanisme d'attention du Transformer n'apporte pas de gain mesurable
   sur ce type de données** — confirmé indépendamment sur données
   synthétiques (Chapitre 12) et sur données réelles SGCC (Chapitre 14), et
   expliqué par une cause identifiée (absence de structure temporelle
   exploitable) plutôt que simplement constaté. Un résultat qui aurait pu
   être tû, et qui ne l'a pas été.
2. **La recalibration seule récupère 98,3% de la dégradation causée par la
   dérive de distribution**, sans toucher aux poids du modèle
   (Chapitre 13.7) — le résultat le plus directement actionnable pour un
   opérateur réel.
3. **Un appel bloquant synchrone dans un gestionnaire asynchrone empêche
   toute mise à l'échelle horizontale**, un problème précisément localisé
   par le profilage systématique (Chapitre 16.4) plutôt que diagnostiqué de
   façon impressionniste.

## 20.3 Ce qui reste à faire

Le sujet initial posait un triangle IA + Blockchain + Application Mobile.
Ce mémoire livre une réalisation complète et scientifiquement validée des
deux premiers piliers ; le troisième (application mobile, notifications
Firebase, ancrage sur blockchain publique via Smart Contract) reste à
réaliser, un écart énoncé sans détour au Chapitre 1 et détaillé au
Chapitre 18, avec un chemin de complétion concret proposé au Chapitre 19.

## 20.4 Mot de fin

La valeur de ce travail ne réside pas dans l'affirmation que le système
proposé est le meilleur possible — le Chapitre 11 montre clairement qu'un
modèle supervisé plus simple le surpasse sur signatures connues — mais dans
la rigueur avec laquelle chaque affirmation de performance, de robustesse
ou de comportement a été mesurée, contestée, et le cas échéant révisée. Un
système de sécurité dont on connaît précisément les limites, parce
qu'elles ont été mesurées et non supposées, est plus digne de confiance
qu'un système présenté sans réserve — c'est le principe qui a guidé
l'ensemble de ce projet, du premier audit de fuite de données au dernier
rapport de performance.
