# Démarrage rapide

## 1. Lancer le serveur

```bash
cd smartgrid_simulation
./.venv/Scripts/python.exe api_server.py
```

Attendre le message `Uvicorn running on http://0.0.0.0:8000`.

## 2. Ouvrir le tableau de bord

Naviguer vers **http://127.0.0.1:8000/dashboard**.

Vous devriez voir : une topologie réseau animée (4 zones, générateurs,
compteurs), un panneau d'alertes (vide au départ), et un widget « ⚙
Système » en bas à droite (statut de santé opérationnelle).

## 3. Lancer une démonstration

Cliquer sur le bouton **▶ Démo** en haut du tableau de bord — un scénario
de 5 étapes simule successivement plusieurs types d'attaques sur
différentes zones, avec notarisation blockchain automatique des
détections confirmées.

## 4. Vérifier l'API directement

```bash
curl http://127.0.0.1:8000/health
# {"status":"alive","uptime_seconds":...}

curl http://127.0.0.1:8000/api/blockchain/status
# {"available":true,"valid":true,"blocks":...}

curl -X POST http://127.0.0.1:8000/api/detect \
  -H "Content-Type: application/json" \
  -d '{"meter_id":"SM_0001","consommation_kw":2.3,"tension_v":228,"courant_a":10.1,"zone":"Zone A","type":"residentiel"}'
```

*(Une seule lecture ne suffit pas à obtenir une vraie détection : le
modèle a besoin de `seq_len=8` lectures consécutives par compteur avant de
sortir du statut « insufficient_data » — envoyer 8 requêtes successives
avec le même `meter_id` et des horodatages croissants pour observer une
réponse de détection complète.)*

## 5. Consulter la documentation OpenAPI interactive

**http://127.0.0.1:8000/docs** — tous les endpoints, schémas de requête/
réponse, testables directement depuis le navigateur.

## 6. Authentification (fonctionnalités protégées)

Les endpoints en lecture (dont `/api/detect`) sont volontairement ouverts.
Pour les endpoints protégés (`/api/model/reload`, `/api/simulate/attack`,
gestion de la grille) :

```bash
curl -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"...","password":"..."}'
# → {"access_token": "...", "token_type": "bearer"}
```

Voir `production/docs/operator_manual.md` pour les comptes par défaut
(mots de passe à changer avant tout usage réel, voir
`production/security/users.json`).

## Pour aller plus loin

- Comprendre l'architecture : `thesis_package/diagrams/rendered/`
- Comprendre les résultats scientifiques : `thesis_package/thesis/`
- Contribuer au code : [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)
- Déployer en production : `production/docs/deployment_guide.md`
