# Guide d'installation

> Version condensée pour GitHub. Pour la version complète orientée
> exploitation/production, voir `production/docs/installation_guide.md`.

## Prérequis

- Windows 10/11 (l'environnement de développement de référence) ou
  Linux/macOS (non testé explicitement dans ce projet, mais le code ne
  contient pas de dépendance spécifique à Windows hors des scripts de
  gestion de processus).
- Python 3.10 (version utilisée pour tous les tests et validations de ce
  projet — d'autres versions 3.10.x devraient fonctionner, non garanti
  pour 3.11+/3.9-).
- ~2 Go d'espace disque (dépendances PyTorch incluses).
- Aucun GPU requis — le modèle tourne sur CPU (confirmé par le profilage
  de performance, Phase 7 : `torch.cuda.is_available()` est `False` même
  en présence d'un GPU NVIDIA sur la machine de référence).

## Installation

```bash
cd smartgrid_simulation
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements.txt
```

Sur Linux/macOS, remplacer `./.venv/Scripts/python.exe` par
`./.venv/bin/python`.

## Vérification de l'installation

```bash
./.venv/Scripts/python.exe -c "import torch, fastapi, sklearn; print('OK')"
```

## Modèle pré-entraîné

Les artefacts du modèle champion (`outputs/early_stopping_final/`,
`outputs/test_run_now/`) doivent être présents pour que l'inférence
fonctionne. **Point de vigilance documenté** (voir
`thesis_package/thesis/chapitre_05_methodologie.md`) : ces artefacts sont
antérieurs à la correction du protocole de fuite de données (Phase 0) —
pour un modèle suivant le protocole sans fuite, ré-entraîner via :

```bash
./.venv/Scripts/python.exe run_transformer_autoencoder.py \
    --val-frac 0.15 --test-frac 0.15
```

(sans l'option `--legacy`).

## Configuration de production (optionnelle)

Pour un déploiement durci (authentification, limitation de débit,
logging structuré) plutôt qu'un usage de développement :

```bash
cp .env.example .env
# Éditer .env : générer une vraie SGRID_JWT_SECRET_KEY, définir
# SGRID_ENVIRONMENT=production, configurer SGRID_CORS_ALLOWED_ORIGINS
```

Voir `production/docs/configuration_guide.md` pour la liste complète des
variables d'environnement.

## Installation via Docker (non vérifiée par une construction réelle)

Une topologie à 3 conteneurs est fournie (`production/docker/`) mais
**n'a jamais été construite avec Docker réellement installé** sur la
machine de développement de ce projet — validée uniquement par revue
statique (chemins, syntaxe YAML, imports). Voir
`production/docs/deployment_guide.md` pour les commandes exactes
(`docker compose up --build`) et **tester avant tout usage réel**.

## Problèmes connus

- **Windows, port déjà utilisé** : `pkill -f api_server` ne fonctionne PAS
  sous Windows ; utiliser PowerShell :
  `Get-NetTCPConnection -LocalPort 8000 | Stop-Process -Id $_.OwningProcess -Force`
- **Train/serve skew** : si vous régénérez les données du simulateur avec
  des paramètres différents (nombre de types de consommateurs, tension
  nominale) du modèle déjà entraîné, RÉ-ENTRAÎNER le modèle — un
  mésappariement entre le format d'entraînement et les données servies a
  été une cause réelle de faux positifs massifs documentée en cours de
  projet.
