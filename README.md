# Smart Grid SCADA — Détection d'Anomalies IA + Blockchain

**PFE 2026 — Aziz Abidi**

Système de détection d'anomalies en temps réel sur un réseau intelligent (Smart Grid), basé sur un Transformer Autoencoder, une blockchain Proof-of-Authority, et un tableau de bord React 3D.

---

## Architecture

```
smartgrid_simulation/
│
├── api_server.py          # FastAPI backend (port 8000)
├── config.py              # Configuration centralisée
├── requirements.txt       # Dépendances Python
│
├── ml_pipeline/           # Pipeline ML
│   ├── realtime_detector.py     # Détecteur temps réel (2 Hz)
│   ├── transformer_autoencoder.py # Modèle PyTorch (dim=128, 3 couches, 4 têtes)
│   ├── transformer_model.py
│   ├── model_registry.py        # Registre des versions (champion v2)
│   ├── xai.py                   # Explainabilité SHAP
│   └── ...
│
├── blockchain/
│   └── poa_ledger.py      # Blockchain Proof-of-Authority (4 validateurs)
│
├── frontend/              # Code source React (Vite)
│   ├── src/
│   │   ├── App.jsx        # Composant principal
│   │   ├── canvasEngine.js # Moteur Canvas 3D (proj, box3d, gears, etc.)
│   │   ├── api.js         # Client FastAPI
│   │   └── index.css      # Tokens de thème dark/light + composants
│   └── vite.config.js     # Build → dashboard/, proxy /api → :8000
│
├── dashboard/             # Build React (servi par FastAPI)
│   ├── index.html
│   └── assets/            # JS/CSS hashés
│
└── outputs/               # Modèles entraînés, résultats
    └── test_run_now/      # Modèle champion v2
```

---

## Lancer le projet

### 1. Backend (FastAPI)
```bash
cd smartgrid_simulation
.venv\Scripts\uvicorn api_server:app --port 8000 --reload
```

### 2. Dashboard
Ouvrir **http://localhost:8000** ou **http://localhost:8000/network**

### 3. Dev frontend (avec hot-reload)
```bash
cd smartgrid_simulation/frontend
npm install
npm run dev          # http://localhost:3000 (proxy /api → :8000)
```

### 4. Re-build le dashboard après modifications
```bash
cd smartgrid_simulation/frontend
npm run build        # écrit dans dashboard/
```

---

## Modèle ML — Performances

| Métrique  | Valeur  |
|-----------|---------|
| AUC-ROC   | 97.95%  |
| Précision | 99.84%  |
| Rappel    | 75.43%  |
| F1-Score  | 85.93%  |
| Seuil     | 0.00035 |

**Architecture** : Transformer Autoencoder — dim=128, 3 couches, 4 têtes d'attention, séquence=12

---

## API Endpoints principaux

| Route                    | Description                              |
|--------------------------|------------------------------------------|
| `GET /`                  | Dashboard React (index.html)             |
| `GET /network`           | Alias dashboard                          |
| `POST /api/detect`       | Détection anomalie (lecture unique)      |
| `POST /api/detect/batch` | Détection batch (jusqu'à 100 lectures)   |
| `GET /api/model/status`  | Statut modèle + métriques                |
| `GET /api/blockchain/status` | Statut blockchain PoA               |
| `GET /api/model/registry`| Registre des versions                    |

---

## Types d'attaques détectées

| Type  | Couleur | Description                        |
|-------|---------|------------------------------------|
| FDIA  | 🔴 Rouge | Injection de fausses données       |
| DoS   | 🟠 Orange | Déni de service, coupure           |
| Fraud | 🟣 Violet | Vol d'énergie, dérivation          |
| Fault | 🟡 Jaune | Défaut matériel, surchauffe        |

---

## Zones du réseau

| Zone | Label       | Couleur   |
|------|-------------|-----------|
| A    | Résidentiel | 🔵 Bleu   |
| B    | Commercial  | 🟢 Vert   |
| C    | Industriel  | 🟣 Violet |
| D    | Mixte       | 🟡 Jaune  |
