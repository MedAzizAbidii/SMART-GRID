"""
robustness/adversarial.py — Experiment 12: adversarial robustness.

Why FGSM/PGD ARE mathematically applicable here, with the correct adaptation:
The production model is a reconstruction-based (autoencoder) anomaly detector,
not a classifier with a cross-entropy loss, so classic FGSM/PGD (which attack
a classification loss to flip a predicted label) do not apply verbatim. The
correct, standard adaptation for autoencoder-based anomaly detectors is an
EVASION attack on the reconstruction loss itself: a white-box adversary with
gradient access crafts a bounded L_inf perturbation on an ATTACK sequence that
MINIMIZES reconstruction error, so the sequence's anomaly score falls below
the detection threshold (the attack becomes invisible to the detector). This
is the direct analogue of "FGSM" (one gradient step) and "PGD" (iterated,
projected gradient steps) for this architecture, using the reconstruction
loss L(x) = ||f(x) - x||^2 as the objective the attacker DESCENDS instead of
ascends (an untargeted classifier attacker ascends the loss to cause a
misclassification; here the attacker descends the anomaly SCORE to cause a
missed detection — the operationally meaningful failure mode for a security
system).

Threat model / honesty note: the perturbation is applied in SCALED FEATURE
SPACE (post-StandardScaler), which assumes the attacker can manipulate the
processed feature vector directly. A real attacker manipulates raw physical
sensor readings, which then pass through fixed feature engineering + scaling
— some engineered features (rolling means/std, zone aggregates) are not
freely invertible to a raw perturbation of equal magnitude. This experiment
therefore measures a WORST-CASE, feature-space upper bound on evasion
susceptibility, not a proven raw-signal attack; we report this explicitly.
"""
from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn


def fgsm_evade(model, seqs: np.ndarray, epsilon: float) -> np.ndarray:
    """One-step gradient descent on reconstruction loss (sign method)."""
    model.eval()
    x = torch.tensor(seqs, dtype=torch.float32, requires_grad=True)
    recon, _ = model(x)
    loss = nn.functional.mse_loss(recon, x)
    loss.backward()
    with torch.no_grad():
        x_adv = x - epsilon * x.grad.sign()      # DESCEND the reconstruction loss
    return x_adv.detach().numpy().astype("float32")


def pgd_evade(model, seqs: np.ndarray, epsilon: float, alpha: float, steps: int) -> np.ndarray:
    """Iterated, L_inf-projected gradient descent on reconstruction loss."""
    model.eval()
    x0 = torch.tensor(seqs, dtype=torch.float32)
    x = x0.clone().detach()
    for _ in range(steps):
        x.requires_grad_(True)
        recon, _ = model(x)
        loss = nn.functional.mse_loss(recon, x)
        grad = torch.autograd.grad(loss, x)[0]
        with torch.no_grad():
            x = x - alpha * grad.sign()
            delta = torch.clamp(x - x0, -epsilon, epsilon)
            x = (x0 + delta).detach()
    return x.numpy().astype("float32")
