"""
robustness/adversarial_runner.py — Experiment 12: adversarial evasion (FGSM/PGD).

Attacks the reconstruction loss of the frozen production model to evade
detection on ATTACK-labelled test sequences (see adversarial.py for the full
threat-model discussion and honesty caveats). Sweeps L_inf budgets to produce
a robustness curve: detection rate vs perturbation budget.

Usage:
  .\.venv\Scripts\python.exe -m robustness.adversarial_runner
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from robustness.common import load_detector, load_test_split, recon_scores
from robustness.adversarial import fgsm_evade, pgd_evade

RES = Path(__file__).resolve().parent / "results"
EPSILONS = [0.0, 0.05, 0.1, 0.25, 0.5, 1.0]


def main():
    RES.mkdir(parents=True, exist_ok=True)
    det = load_detector()
    model = det.model
    threshold = det.threshold_tracker._global
    te_s, te_l, cols, frame, te_end = load_test_split()
    atk = te_s[te_l == 1]
    if len(atk) == 0:
        print("No attack sequences in test split — skipping adversarial experiment.")
        return
    print("=" * 62)
    print(f"  ADVERSARIAL EVASION (FGSM / PGD) on {len(atk)} attack sequences")
    print("  Threat model: white-box, L_inf-bounded, FEATURE-SPACE perturbation")
    print("  (see robustness/adversarial.py docstring for the honesty caveat)")
    print("=" * 62)

    results = {"fgsm": [], "pgd": []}
    for eps in EPSILONS:
        if eps == 0.0:
            adv = atk
        else:
            adv = fgsm_evade(model, atk, eps)
        scores = recon_scores(model, adv)
        detect_rate = float((scores >= threshold).mean())
        results["fgsm"].append({"epsilon": eps, "detect_rate": round(detect_rate, 4),
                                "mean_score": round(float(scores.mean()), 6)})
        print(f"  FGSM  eps={eps:<5} detect_rate={detect_rate:.3f}  mean_score={scores.mean():.6f}")

    for eps in EPSILONS:
        if eps == 0.0:
            adv = atk
        else:
            adv = pgd_evade(model, atk, eps, alpha=eps / 4, steps=10)
        scores = recon_scores(model, adv)
        detect_rate = float((scores >= threshold).mean())
        results["pgd"].append({"epsilon": eps, "detect_rate": round(detect_rate, 4),
                               "mean_score": round(float(scores.mean()), 6)})
        print(f"  PGD   eps={eps:<5} detect_rate={detect_rate:.3f}  mean_score={scores.mean():.6f}")

    (RES / "E12_adversarial.json").write_text(json.dumps(results, indent=2))
    print(f"\n  saved: {RES / 'E12_adversarial.json'}")


if __name__ == "__main__":
    main()
