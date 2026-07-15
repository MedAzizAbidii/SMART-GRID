"""
benchmark/models.py — one common interface for every benchmarked model.

Contract (BaselineModel):
    fit(train_seqs, train_labels)   # train_seqs: (n, seq_len, features)
    score(seqs) -> np.ndarray       # higher = more anomalous, one per sequence
    feature_importance() -> None | np.ndarray

Three model families share this interface so the runner treats them identically:
  * Unsupervised anomaly (IsolationForest, One-Class SVM): fit on TRAIN-NORMAL
    flattened vectors; score = negative decision_function.
  * Supervised (RandomForest, XGBoost, LightGBM): fit on flattened TRAIN with
    labels; score = P(attack).
  * Sequence reconstruction (LSTM-AE, Transformer-AE): fit on TRAIN-NORMAL
    sequences; score = mean reconstruction error.

Every model gets the SAME leak-free sequences from the runner. Flattening
(seq_len*features) is the identical input for the non-sequence models.
"""
from __future__ import annotations

import numpy as np


def _flatten(seqs: np.ndarray) -> np.ndarray:
    """(n, seq_len, feat) -> (n, seq_len*feat) for non-sequence models."""
    return seqs.reshape(len(seqs), -1)


class BaselineModel:
    name = "base"
    kind = "base"          # unsupervised | supervised | reconstruction

    def fit(self, train_seqs: np.ndarray, train_labels: np.ndarray) -> None:
        raise NotImplementedError

    def score(self, seqs: np.ndarray) -> np.ndarray:
        raise NotImplementedError

    def feature_importance(self):
        return None

    def size_bytes(self) -> int:
        import io, pickle
        buf = io.BytesIO()
        try:
            pickle.dump(getattr(self, "_model", self), buf)
            return buf.tell()
        except Exception:
            return 0


# ── Unsupervised anomaly detectors ────────────────────────────────────────────

class IsolationForestModel(BaselineModel):
    name, kind = "Isolation Forest", "unsupervised"

    def __init__(self, seed=42):
        from sklearn.ensemble import IsolationForest
        self._model = IsolationForest(n_estimators=200, contamination="auto",
                                      random_state=seed, n_jobs=-1)

    def fit(self, train_seqs, train_labels):
        # fit on NORMAL only (standard one-class protocol)
        X = _flatten(train_seqs[train_labels == 0])
        self._model.fit(X)

    def score(self, seqs):
        # decision_function: higher = more normal -> negate for "anomaly score"
        return -self._model.decision_function(_flatten(seqs))


class OneClassSVMModel(BaselineModel):
    name, kind = "One-Class SVM", "unsupervised"

    def __init__(self, seed=42):
        from sklearn.linear_model import SGDOneClassSVM
        # SGD variant scales far better than kernel SVC on large N
        self._model = SGDOneClassSVM(nu=0.05, random_state=seed)

    def fit(self, train_seqs, train_labels):
        from sklearn.preprocessing import StandardScaler
        self._sc = StandardScaler()
        X = self._sc.fit_transform(_flatten(train_seqs[train_labels == 0]))
        self._model.fit(X)

    def score(self, seqs):
        X = self._sc.transform(_flatten(seqs))
        return -self._model.decision_function(X)


# ── Supervised classifiers ────────────────────────────────────────────────────

class _SupervisedProba(BaselineModel):
    kind = "supervised"

    def fit(self, train_seqs, train_labels):
        X = _flatten(train_seqs)
        y = np.asarray(train_labels).astype(int)
        self._model.fit(X, y)

    def score(self, seqs):
        p = self._model.predict_proba(_flatten(seqs))
        return p[:, 1]

    def feature_importance(self):
        return getattr(self._model, "feature_importances_", None)


class RandomForestModel(_SupervisedProba):
    name = "Random Forest"

    def __init__(self, seed=42):
        from sklearn.ensemble import RandomForestClassifier
        self._model = RandomForestClassifier(
            n_estimators=200, class_weight="balanced", random_state=seed, n_jobs=-1)


class XGBoostModel(_SupervisedProba):
    name = "XGBoost"

    def __init__(self, seed=42):
        import xgboost as xgb
        self._model = xgb.XGBClassifier(
            n_estimators=300, max_depth=6, learning_rate=0.1,
            subsample=0.9, colsample_bytree=0.9, eval_metric="logloss",
            random_state=seed, n_jobs=-1, tree_method="hist")

    def fit(self, train_seqs, train_labels):
        y = np.asarray(train_labels).astype(int)
        # scale_pos_weight handles imbalance
        pos = max(int(y.sum()), 1); neg = len(y) - pos
        self._model.set_params(scale_pos_weight=max(neg / pos, 1.0))
        self._model.fit(_flatten(train_seqs), y)


class LightGBMModel(_SupervisedProba):
    name = "LightGBM"

    def __init__(self, seed=42):
        import lightgbm as lgb
        self._model = lgb.LGBMClassifier(
            n_estimators=300, max_depth=-1, learning_rate=0.05,
            class_weight="balanced", random_state=seed, n_jobs=-1, verbose=-1)


# ── Sequence reconstruction models ────────────────────────────────────────────

class _ReconAE(BaselineModel):
    kind = "reconstruction"

    def __init__(self, cfg, seed=42):
        import torch
        torch.manual_seed(seed)
        self.cfg = cfg
        self.device = "cpu"
        self._torch = torch

    def _build(self, seq_len, feat):
        raise NotImplementedError

    def fit(self, train_seqs, train_labels):
        torch = self._torch
        import torch.nn as nn
        from torch.utils.data import DataLoader, TensorDataset
        seq_len, feat = train_seqs.shape[1], train_seqs.shape[2]
        self.model = self._build(seq_len, feat).to(self.device)
        normal = train_seqs[train_labels == 0]
        opt = torch.optim.AdamW(self.model.parameters(), lr=self.cfg.get("lr", 5e-4), weight_decay=1e-4)
        crit = nn.MSELoss()
        loader = DataLoader(TensorDataset(torch.tensor(normal, dtype=torch.float32)),
                            batch_size=self.cfg.get("batch_size", 128), shuffle=True)
        epochs = self.cfg.get("pretrain_epochs", 20)
        for _ in range(epochs):
            self.model.train()
            for (xb,) in loader:
                opt.zero_grad()
                out = self._forward(xb.to(self.device))
                loss = crit(out, xb.to(self.device))
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
                opt.step()

    def _forward(self, x):
        raise NotImplementedError

    def score(self, seqs):
        torch = self._torch
        self.model.eval()
        out = np.empty(len(seqs), "float32")
        with torch.no_grad():
            for i in range(0, len(seqs), 256):
                xb = torch.tensor(seqs[i:i+256], dtype=torch.float32, device=self.device)
                rec = self._forward(xb)
                out[i:i+256] = ((rec - xb) ** 2).mean(dim=(1, 2)).cpu().numpy()
        return out

    def size_bytes(self):
        return sum(p.numel() * p.element_size() for p in self.model.parameters())


class LSTMAutoencoderModel(_ReconAE):
    name = "LSTM Autoencoder"

    def _build(self, seq_len, feat):
        import torch.nn as nn
        hid = self.cfg.get("model_dim", 128) // 2
        self.seq_len = seq_len
        class LSTMAE(nn.Module):
            def __init__(s):
                super().__init__()
                s.enc = nn.LSTM(feat, hid, batch_first=True)
                s.dec = nn.LSTM(hid, hid, batch_first=True)
                s.out = nn.Linear(hid, feat)
            def forward(s, x):
                _, (h, _) = s.enc(x)
                rep = h[-1].unsqueeze(1).repeat(1, x.size(1), 1)
                d, _ = s.dec(rep)
                return s.out(d)
        return LSTMAE()

    def _forward(self, x):
        return self.model(x)


class TransformerAutoencoderModel(_ReconAE):
    name = "Transformer Autoencoder (proposed)"

    def _build(self, seq_len, feat):
        # reuse the EXACT production architecture
        from ml_pipeline.realtime_detector import TransformerAutoencoder
        return TransformerAutoencoder(
            input_dim=feat, model_dim=self.cfg.get("model_dim", 128),
            num_heads=self.cfg.get("heads", 4), num_layers=self.cfg.get("layers", 3),
            feedforward_dim=self.cfg.get("ff_dim", 256))

    def _forward(self, x):
        rec, _ = self.model(x)
        return rec


REGISTRY = {
    "isolation_forest": IsolationForestModel,
    "one_class_svm": OneClassSVMModel,
    "random_forest": RandomForestModel,
    "xgboost": XGBoostModel,
    "lightgbm": LightGBMModel,
    "lstm_autoencoder": LSTMAutoencoderModel,
    "transformer_autoencoder": TransformerAutoencoderModel,
}


def build(name: str, cfg: dict, seed: int) -> BaselineModel:
    cls = REGISTRY[name]
    if issubclass(cls, _ReconAE):
        return cls(cfg.get("deep", {}), seed=seed)
    return cls(seed=seed)
