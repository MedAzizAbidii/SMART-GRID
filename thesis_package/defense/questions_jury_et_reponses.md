# Questions du jury attendues et réponses suggérées

Classées par thème. Chaque réponse cite un chiffre précis — à connaître par
cœur, pas à improviser le jour J.

## Sur le compromis performance / non-supervision

**Q. Pourquoi ne pas simplement utiliser XGBoost, qui obtient un F1 de
0,986 contre 0,582 pour votre modèle ?**
> R. XGBoost nécessite des exemples étiquetés de chaque type d'attaque à
> l'entraînement — il reconnaît des signatures connues. Mon modèle,
> entraîné uniquement sur du comportement normal, vise la détection
> d'attaques dont le type n'a jamais été vu. Sur ce critère précis (aucun
> label requis), mon modèle est le meilleur des méthodes testées,
> significativement (test de McNemar, p<10⁻⁹ contre chaque alternative
> non supervisée). Une architecture hybride combinant les deux est une
> piste future concrète (Chapitre 19.3), non implémentée ici.

**Q. Votre modèle est-il vraiment utile s'il perd autant face aux
méthodes supervisées ?**
> R. Sur données réelles SGCC également, un modèle supervisé (Random
> Forest, AUC 0,745) reste en tête. Je ne prétends pas que mon modèle est
> le meilleur choix absolu — je démontre qu'il est le meilleur choix
> *dans le cadre non supervisé*, le seul robuste par construction aux
> attaques inconnues. La valeur du projet est d'avoir mesuré et assumé ce
> compromis plutôt que de le taire.

## Sur l'attention/le Transformer

**Q. Si l'attention n'aide pas, pourquoi avoir utilisé un Transformer ?**
> R. Deux raisons : premièrement, ce résultat n'était pas connu au moment
> de choisir l'architecture — il a été découvert PAR l'étude d'ablation
> (Phase 2), ce qui est la preuve que la méthodologie fonctionne.
> Deuxièmement, mon investigation (Phase 2.5) montre que l'inefficacité de
> l'attention est due à une absence de structure temporelle dans MES
> données (fenêtres de 8 lectures, test de permutation Δ=-0,0004), pas à
> un défaut de l'architecture — sur des données à motifs temporels plus
> riches (attaques coordonnées multi-étapes), l'attention pourrait
> apporter un gain différent.

**Q. Comment avez-vous vérifié que ce n'était pas un simple bruit
statistique ?**
> R. Par 4 preuves convergentes et indépendantes : test de permutation
> temporelle (Δ AUC=-0,0004), comparaison arbre sur dernier pas de temps vs
> séquence complète (F1 quasi identiques, 0,973 vs 0,972), entropie de
> l'attention mesurée à 0,961/1,0 (quasi uniforme), et confirmation sur un
> second jeu de données réel indépendant (SGCC, ΔAUC=+0,011 en retirant
> l'attention).

## Sur la robustesse et la calibration

**Q. Un système qui sature à 100% de faux positifs à 0,25 écart-type de
dérive n'est-il pas dangereusement fragile ?**
> R. Oui, mesuré et assumé sans détour — c'est la dimension la plus faible
> du score de robustesse (24,7/100). Mais j'ai identifié la cause
> (calibrateur périmé, pas le modèle) et démontré le correctif : une simple
> recalibration périodique restaure 98,3% du taux de faux positifs, sans
> toucher aux poids. C'est un problème de maintenance opérationnelle,
> résolu, pas un défaut irréparable.

**Q. Pourquoi FGSM devient-il PLUS détectable à mesure que le budget
d'attaque augmente ?**
> R. FGSM applique un seul grand pas dans la direction du gradient ; la
> surface de perte de reconstruction n'étant pas convexe, un pas trop
> grand dépasse la région où l'approximation linéaire du gradient est
> valide, et l'échantillon perturbé finit statistiquement plus éloigné de
> la normalité qu'un échantillon non perturbé. PGD, qui procède par petits
> pas itératifs (10 pas), reste dans cette région et parvient à une
> évasion réelle (taux de détection 0,164 à ε=0,1). C'est un résultat
> classique en apprentissage adversarial, pas une anomalie de mon
> implémentation.

## Sur la blockchain

**Q. Pourquoi une Preuve d'Autorité locale et pas Ethereum/Hyperledger
comme demandé dans le sujet ?**
> R. Assumé comme écart au sujet initial (Chapitre 18.1). Le choix PoA
> répond au besoin fonctionnel réel — traçabilité inviolable pour un
> opérateur de réseau unique, où le problème de confiance décentralisée
> entre parties inconnues que résout Ethereum ne se pose pas de la même
> façon. Le coût (0,027ms/enregistrement) est très inférieur à ce
> qu'impliquerait une blockchain publique. L'ancrage périodique du
> hachage de tête de chaîne sur une blockchain publique via un Smart
> Contract minimal est une extension proposée (Chapitre 19.1), non
> réalisée.

**Q. Que se passe-t-il si les 4 autorités sont compromises simultanément ?**
> R. Le modèle de menace du registre PoA local suppose un attaquant externe
> ou un opérateur isolé malveillant, pas une collusion des 4 autorités
> désignées elles-mêmes — c'est une limite assumée de ce modèle de
> confiance, cohérente avec le choix délibéré de ne pas répliquer un
> consensus décentralisé de type blockchain publique pour ce cas d'usage.

## Sur la performance et le passage à l'échelle

**Q. Pourquoi la concurrence dégrade-t-elle le débit au lieu de
l'améliorer ?**
> R. `/api/detect` est déclaré `async def` mais appelle le modèle de façon
> synchrone et bloquante, sans le déporter sur un exécuteur. Sur un seul
> worker, cela gèle la boucle d'événements pendant toute la durée de
> l'inférence (~275ms) — les requêtes concurrentes ne s'exécutent pas en
> parallèle, elles font la queue. Mesuré précisément : 5,04 req/s à 10
> requêtes simultanées contre 2,37 req/s à 1000. Le correctif est identifié
> et documenté (Chapitre 16.8) mais non appliqué, cette phase étant
> contrainte à la mesure uniquement.

**Q. La blockchain n'a-t-elle jamais été testée sous Docker : n'est-ce pas
un problème ?**
> R. C'est la limite la plus honnête du projet, assumée explicitement
> (score 55/100, le plus bas du tableau de préparation à la production).
> La configuration a été revue statiquement (chemins, syntaxe, imports)
> mais jamais construite faute de Docker sur la machine de développement.
> C'est une action de suivi concrète et documentée (`deployment_guide.md`),
> pas une zone d'ombre non identifiée.

## Sur la méthodologie générale

**Q. N'auriez-vous pas dû simplement rapporter les meilleurs résultats
plutôt que documenter tous ces échecs ?**
> R. Non — c'est précisément l'inverse qui a produit les résultats les plus
> utiles de ce projet. Le résultat « l'attention n'aide pas », s'il avait
> été tû, n'aurait jamais mené à l'investigation qui explique pourquoi
> (Phase 2.5). Le résultat « le système sature sous dérive », s'il avait
> été minimisé, n'aurait jamais mené au résultat de recalibration à 98,3%
> de récupération, qui est le résultat le plus actionnable du mémoire.
> Documenter les échecs a été le moteur de découverte du projet, pas
> seulement une exigence de transparence.
