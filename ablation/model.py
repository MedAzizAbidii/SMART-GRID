"""
ablation/model.py — a single CONFIGURABLE autoencoder whose every design
decision can be toggled, so each ablation removes exactly one component while
holding the rest fixed. The full configuration reproduces the production
Transformer-Autoencoder; flipping one flag yields the ablated variant.

Toggles (one changed per experiment):
  encoder      : "transformer" | "dense"   (Exp 2: remove Transformer)
  use_bottleneck bool                       (Exp 3: remove latent reconstruction)
  use_positional bool                       (Exp 4: remove positional encoding)
  use_attention  bool                       (Exp 5: attention -> token-wise FFN)
  latent_dim, model_dim, heads, layers, dropout, activation
                                            (Exp 6,12,13,14,17,19)
The production weights are NOT touched; this is a parallel, self-contained model
used only inside the ablation runner.
"""
from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F

from ml_pipeline.realtime_detector import PositionalEncoding

_ACT = {"gelu": F.gelu, "relu": F.relu, "leaky_relu": F.leaky_relu, "elu": F.elu}


class _TokenwiseMLP(nn.Module):
    """Per-timestep MLP stack: NO cross-timestep mixing. Used for the
    'dense encoder' and 'no attention' ablations — it isolates whether the
    cross-time attention actually contributes."""
    def __init__(self, dim, layers, dropout, act):
        super().__init__()
        self.act = _ACT[act]
        blocks = []
        for _ in range(layers):
            blocks.append(nn.ModuleList([
                nn.Linear(dim, dim * 2), nn.Linear(dim * 2, dim),
                nn.LayerNorm(dim), nn.Dropout(dropout)]))
        self.blocks = nn.ModuleList(blocks)

    def forward(self, x):
        for lin1, lin2, norm, drop in self.blocks:
            h = lin2(drop(self.act(lin1(x))))
            x = norm(x + h)
        return x


class AblationAE(nn.Module):
    def __init__(self, input_dim: int, cfg: dict):
        super().__init__()
        c = cfg
        self.model_dim = c.get("model_dim", 64)
        act = c.get("activation", "gelu")
        self.use_positional = c.get("use_positional", True)
        self.use_bottleneck = c.get("use_bottleneck", True)
        encoder = c.get("encoder", "transformer")
        use_attention = c.get("use_attention", True)
        layers = c.get("layers", 2)
        heads = c.get("heads", 4)
        dropout = c.get("dropout", 0.1)
        latent = c.get("latent_dim", max(8, self.model_dim // 4))

        self.input_projection = nn.Linear(input_dim, self.model_dim)
        self.pos = PositionalEncoding(self.model_dim, dropout=dropout) if self.use_positional else None

        if encoder == "transformer" and use_attention:
            act_fn = act if act in ("relu", "gelu") else _ACT[act]
            layer = nn.TransformerEncoderLayer(
                d_model=self.model_dim, nhead=heads,
                dim_feedforward=c.get("ff_dim", self.model_dim * 4),
                dropout=dropout, batch_first=True, activation=act_fn)
            self.encoder = nn.TransformerEncoder(layer, num_layers=layers)
        else:
            # dense encoder OR attention removed -> token-wise MLP (no time mixing)
            self.encoder = _TokenwiseMLP(self.model_dim, layers, dropout, act)

        if self.use_bottleneck:
            self.down = nn.Linear(self.model_dim, latent)
            self.up = nn.Linear(latent, self.model_dim)
            self._bneck_act = _ACT[act]
        self.output_projection = nn.Linear(self.model_dim, input_dim)

    def forward(self, x):
        h = self.input_projection(x)
        if self.pos is not None:
            h = self.pos(h)
        h = self.encoder(h)
        if self.use_bottleneck:
            h = self.up(self._bneck_act(self.down(h)))
        return self.output_projection(h)


def build_model(input_dim: int, cfg: dict) -> AblationAE:
    return AblationAE(input_dim, cfg)


def make_optimizer(name: str, params, lr: float):
    name = name.lower()
    if name == "adam":
        return torch.optim.Adam(params, lr=lr)
    if name == "rmsprop":
        return torch.optim.RMSprop(params, lr=lr)
    if name == "sgd":
        return torch.optim.SGD(params, lr=lr, momentum=0.9)
    return torch.optim.AdamW(params, lr=lr, weight_decay=1e-4)   # default


def make_loss(name: str):
    name = name.lower()
    if name == "mae":
        return nn.L1Loss()
    if name == "huber":
        return nn.HuberLoss(delta=1.0)
    return nn.MSELoss()   # default
