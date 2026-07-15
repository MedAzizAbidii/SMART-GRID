"""
realdata/calibrate.py — apply the Phase-4 winning calibrator (Platt on raw
score) to the proposed model's SGCC consumer scores. Fit on VAL consumers,
evaluate ECE / MCE(robust) / Brier + reliability diagram on TEST consumers.
Reuses calibration.methods (Phase 4) — no duplication.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from realdata.prepare import build, consumer_split_masks
from realdata.common import train_recon, window_scores, consumer_scores, SEED
from realdata.benchmark import RECON_CFG
from calibration.methods import (PlattRaw, reliability_bins,
                                 expected_calibration_error,
                                 max_calibration_error_robust, brier_score)

HERE = Path(__file__).resolve().parent
RES, PLOTS = HERE / "results", HERE / "plots"
_PAL = {"acc": "#2C6FA6"}
plt.rcParams.update({"figure.dpi": 140, "font.size": 9})


def main():
    RES.mkdir(parents=True, exist_ok=True); PLOTS.mkdir(parents=True, exist_ok=True)
    d = build()
    masks = consumer_split_masks(d["cons_split"])
    flags = d["cons_flags"]

    # proposed model's consumer scores (retrain deterministically)
    wins = d["wins_scaled"]; widx = d["widx"]; win_split = d["win_split"]; tr_idx = d["train_norm_win_idx"]
    model = train_recon(wins[tr_idx], dict(RECON_CFG), seed=SEED)
    scored_mask = np.isin(win_split, ["val", "test"])
    ws = window_scores(model, wins[scored_mask])
    full = np.full(len(widx), np.nan); full[scored_mask] = ws
    cons_sc = consumer_scores(full, widx, int(d["n_consumers"]), agg="mean")

    va_m, te_m = masks["val"], masks["test"]
    va_s, va_y = cons_sc[va_m], flags[va_m]
    te_s, te_y = cons_sc[te_m], flags[te_m]
    vg = ~np.isnan(va_s); tg = ~np.isnan(te_s)
    va_s, va_y = va_s[vg], va_y[vg]; te_s, te_y = te_s[tg], te_y[tg]

    cal = PlattRaw().fit(va_s, va_y)
    p_te = cal.predict_proba(te_s)

    metrics = {
        "ece": round(expected_calibration_error(p_te, te_y), 4),
        "mce_robust": round(max_calibration_error_robust(p_te, te_y, min_count=10), 4),
        "brier": round(brier_score(p_te, te_y), 4),
        "platt_a": cal.a, "platt_b": cal.b,
    }
    print("=" * 60)
    print("  SGCC CALIBRATION (Platt-on-raw, Phase-4 winner)")
    print("=" * 60)
    print(f"  TEST consumers: {len(te_y)} (theft={int(te_y.sum())})")
    print(f"  ECE={metrics['ece']} MCE(robust)={metrics['mce_robust']} Brier={metrics['brier']}")

    mids, conf, acc, count = reliability_bins(p_te, te_y)
    valid = count > 0
    fig, ax = plt.subplots(figsize=(5.5, 5))
    ax.plot([0, 1], [0, 1], "k--", lw=1, alpha=0.4)
    ax.plot(conf[valid], acc[valid], "o-", color=_PAL["acc"])
    ax.set_xlabel("predicted probability"); ax.set_ylabel("observed theft fraction")
    ax.set_title(f"SGCC calibration (Platt-on-raw)\nECE={metrics['ece']} Brier={metrics['brier']}")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    fig.tight_layout(); fig.savefig(PLOTS / "sgcc_calibration.png"); plt.close(fig)

    (RES / "calibration_results.json").write_text(json.dumps(metrics, indent=2, default=float))
    print(f"  Saved: {RES / 'calibration_results.json'}, plots/sgcc_calibration.png")
    print("=" * 60)


if __name__ == "__main__":
    main()
