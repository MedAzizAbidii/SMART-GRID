"""
ablation/experiments.py — the ablation matrix.

BASE reproduces the proposed architecture (at a fast, fixed budget so relative
effects are comparable and the whole study runs in minutes — ablation measures
DELTAS, not absolute SOTA numbers). Every experiment changes exactly ONE field.
`retrain=False` experiments reuse the baseline's trained model (threshold
strategies, XAI runtime) — no component of the model changes, only the decision
rule or post-hoc explanation.
"""
from __future__ import annotations

# Fast, fixed training budget shared by every retrained variant.
BASE = {
    "encoder": "transformer", "use_bottleneck": True, "use_positional": True,
    "use_attention": True, "model_dim": 64, "latent_dim": 16, "heads": 4,
    "layers": 2, "dropout": 0.1, "activation": "gelu", "ff_dim": 256,
    "loss": "mse", "optimizer": "adamw", "lr": 5e-4, "batch_size": 128,
    "pretrain_epochs": 5, "finetune_epochs": 1, "seq_len": 8,
    "threshold": "f1", "feature_k": None, "scale": True,
}


def _exp(eid, group, component, label, changes, retrain=True):
    cfg = dict(BASE); cfg.update(changes)
    return {"id": eid, "group": group, "component": component, "label": label,
            "cfg": cfg, "retrain": retrain, "changes": changes}


def all_experiments():
    E = []
    A = E.append
    # 1 — baseline
    A(_exp("E01_baseline", "baseline", "Full proposed model",
           "Transformer + Autoencoder (baseline)", {}))
    # 2 — remove Transformer
    A(_exp("E02_dense_encoder", "architecture", "Transformer encoder",
           "Dense encoder (no Transformer)", {"encoder": "dense"}))
    # 3 — remove bottleneck
    A(_exp("E03_no_bottleneck", "architecture", "Autoencoder bottleneck",
           "No latent bottleneck", {"use_bottleneck": False}))
    # 4 — remove positional encoding
    A(_exp("E04_no_positional", "architecture", "Positional encoding",
           "No positional encoding", {"use_positional": False}))
    # 5 — remove attention
    A(_exp("E05_no_attention", "architecture", "Self-attention",
           "Attention -> token-wise FFN", {"use_attention": False}))
    # 6 — latent dim
    for d in (8, 32):
        A(_exp(f"E06_latent_{d}", "capacity", "Latent dim",
               f"Latent dim = {d}", {"latent_dim": d}))
    # 7 — reconstruction loss
    for ls in ("mae", "huber"):
        A(_exp(f"E07_loss_{ls}", "training", "Reconstruction loss",
               f"Loss = {ls.upper()}", {"loss": ls}))
    # 8 — threshold strategy (NO retrain)
    for th in ("p95", "p99", "mad", "adaptive"):
        A(_exp(f"E08_thr_{th}", "threshold", "Threshold strategy",
               f"Threshold = {th}", {"threshold": th}, retrain=False))
    # 9 — feature selection
    for k in (20, 40):
        A(_exp(f"E09_featsel_{k}", "features", "Feature selection",
               f"Top-{k} features (variance)", {"feature_k": k}))
    # 10 — normalization
    A(_exp("E10_no_norm", "features", "Normalization",
           "No normalization (raw features)", {"scale": False}))
    # 11 — sequence length
    for s in (16, 32):
        A(_exp(f"E11_seq_{s}", "capacity", "Sequence length",
               f"Sequence length = {s}", {"seq_len": s}))
    # 12 — embedding size
    for d in (32, 128):
        A(_exp(f"E12_dim_{d}", "capacity", "Embedding size",
               f"Embedding dim = {d}", {"model_dim": d}))
    # 13 — attention heads
    for h in (1, 2, 8):
        A(_exp(f"E13_heads_{h}", "capacity", "Attention heads",
               f"Heads = {h}", {"heads": h}))
    # 14 — transformer layers
    for n in (1, 4):
        A(_exp(f"E14_layers_{n}", "capacity", "Transformer layers",
               f"Layers = {n}", {"layers": n}))
    # 15 — learning rate
    for lr in (1e-3, 1e-4):
        A(_exp(f"E15_lr_{lr:g}", "training", "Learning rate",
               f"LR = {lr:g}", {"lr": lr}))
    # 16 — optimizer
    for opt in ("adam", "rmsprop", "sgd"):
        A(_exp(f"E16_opt_{opt}", "training", "Optimizer",
               f"Optimizer = {opt}", {"optimizer": opt}))
    # 17 — dropout
    for dr in (0.0, 0.3):
        A(_exp(f"E17_drop_{dr}", "training", "Dropout",
               f"Dropout = {dr}", {"dropout": dr}))
    # 18 — batch size
    for b in (64, 256):
        A(_exp(f"E18_batch_{b}", "training", "Batch size",
               f"Batch size = {b}", {"batch_size": b}))
    # 19 — activation
    for a in ("relu", "leaky_relu", "elu"):
        A(_exp(f"E19_act_{a}", "training", "Activation",
               f"Activation = {a}", {"activation": a}))
    # 20 — without XAI (runtime only; NO retrain, no score change)
    A(_exp("E20_no_xai", "runtime", "XAI (Integrated Gradients)",
           "Without XAI attribution", {}, retrain=False))
    return E
