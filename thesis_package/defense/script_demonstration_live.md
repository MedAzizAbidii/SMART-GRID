# Script de démonstration live (3-5 minutes)

## Préparation avant la soutenance (à faire la veille)

1. Vérifier que le serveur démarre proprement :
   `cd smartgrid_simulation && ./.venv/Scripts/python.exe api_server.py`
2. Attendre le message `Uvicorn running on http://0.0.0.0:8000`.
3. Ouvrir `http://127.0.0.1:8000/dashboard` dans le navigateur, vérifier
   visuellement que le tableau de bord s'affiche correctement (pas de
   `{{ }}` bruts visibles — si c'est le cas, rafraîchir avec Ctrl+Shift+R).
4. Vérifier `http://127.0.0.1:8000/health` retourne `{"status":"alive"}`.
5. **Avoir un plan B** : capture d'écran/vidéo courte du tableau de bord en
   fonctionnement, en cas de problème réseau/matériel le jour J.

## Déroulé de la démonstration

**Étape 1 — Vue d'ensemble (30s)**
> « Voici le tableau de bord en fonctionnement réel, connecté au backend
> que je viens de décrire. » Montrer la topologie réseau animée, les 4
> zones, les statistiques en haut (AUC du modèle, nombre de blocs PoA).

**Étape 2 — Déclencher une démonstration d'attaque (1 min)**
> Cliquer sur le bouton « ▶ Démo ». « Ce scénario simule successivement une
> injection de fausses données, un déni de service et une fraude
> énergétique sur différentes zones. » Observer le panneau d'alertes se
> remplir en temps réel, et la topologie réseau afficher le compteur en
> anomalie avec l'indicateur visuel rouge.

**Étape 3 — Ouvrir le détail d'une anomalie (1 min)**
> Cliquer sur une alerte. « Voici le détail : le type d'attaque classifié,
> le score de confiance, et les appareils IoT du foyer affectés — modélisés
> jusqu'au niveau des appareils individuels pour ce compteur. »

**Étape 4 — Montrer l'explicabilité (1 min)**
> Basculer sur l'onglet XAI. « Voici les contributions par feature calculées
> par integrated gradients — la méthode d'explicabilité utilisée en temps
> réel, plus rapide que SHAP pour ce chemin critique. » Mentionner
> brièvement, si une question est anticipée : « L'attention, elle, s'est
> révélée peu informative sur ce système — expliqué en détail dans le
> mémoire, Chapitre 12. »

**Étape 5 — Vérifier la blockchain (30s)**
> Basculer sur les statistiques. « Le nombre de blocs PoA a augmenté depuis
> le début de la démonstration — chaque anomalie confirmée a été notariée. »
> Optionnel : `curl http://127.0.0.1:8000/api/blockchain/status` dans un
> terminal, montrer `"valid": true`.

**Étape 6 — Le widget de santé opérationnelle (30s)**
> Cliquer sur le widget « ⚙ Système » en bas à droite. « Ce widget,
> ajouté lors du durcissement de production, sonde l'état de santé du
> système en continu — modèle chargé, blockchain valide, ressources
> système. »

**Étape 7 — Télécharger le rapport (30s)**
> Cliquer sur « 📋 Rapport » puis « ⬇ Télécharger JSON ». « Le tableau de
> bord permet d'exporter un rapport de performance à tout moment. »

## Si quelque chose ne fonctionne pas

- **Le serveur ne répond pas** : ne pas paniquer, passer directement au
  plan B (capture/vidéo), en disant simplement « Je vais montrer une
  capture de cette fonctionnalité en fonctionnement, réalisée lors des
  tests. »
- **Le tableau de bord affiche des `{{ }}` bruts** : c'est un mode
  éditeur déclenché par une extension de navigateur externe (documenté
  dans le projet) — rafraîchir la page (Ctrl+Shift+R) résout le problème
  en quelques secondes ; ne pas s'attarder dessus si cela arrive.
- **Une question porte sur la latence perçue lors de la démo** : « La
  latence mesurée en isolation est de 275ms par lecture ; ce que vous
  observez ici est cohérent avec cette mesure — voir Chapitre 16 pour le
  détail du profilage. »
