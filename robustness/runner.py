"""
robustness/runner.py — resumable orchestrator for robustness experiments 1-11.

Frozen production model + frozen scaler + frozen threshold; only the TEST
split's features are perturbed. Every experiment is independently runnable
and cached (results/<id>.json). Experiment 12 (adversarial) is in
adversarial_runner.py; reliability/stress are separate scripts (see README).

Usage:
  .\.venv\Scripts\python.exe -m robustness.runner                 # all, resume
  .\.venv\Scripts\python.exe -m robustness.runner --only E01_gauss_0.05
  .\.venv\Scripts\python.exe -m robustness.runner --fresh
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from robustness.common import load_detector, load_test_split, evaluate, degradation
from robustness import perturbations as P
from robustness.experiments.matrix import (
    GAUSSIAN_SIGMAS, MISSING_FRACS, IMPUTATIONS, PACKET_LOSS_FRACS,
    DRIFT_LEVELS, CONCEPT_DRIFT_LEVELS, JITTER_PROBS, UNKNOWN_ATTACK_KINDS, OOD_LEVELS,
)

RES = Path(__file__).resolve().parent / "results"
SEED = 42


def _save(exp_id, group, label, params, result, clean_metrics):
    deg = degradation({"metrics": clean_metrics}, result, "f1")
    payload = {
        "id": exp_id, "group": group, "label": label, "params": params,
        "metrics": result["metrics"], "ci": result["ci"], "degradation_f1": deg,
    }
    (RES / f"{exp_id}.json").write_text(json.dumps(payload, indent=2))
    return payload


def run_all(only=None, fresh=False):
    RES.mkdir(parents=True, exist_ok=True)
    det = load_detector()
    model = det.model
    threshold = det.threshold_tracker._global
    te_s, te_l, cols, frame, te_end = load_test_split()

    def cached(exp_id):
        p = RES / f"{exp_id}.json"
        return None if fresh else (json.loads(p.read_text()) if p.exists() else None)

    def maybe_run(exp_id, group, label, params, fn):
        if only and exp_id != only:
            return
        c = cached(exp_id)
        if c:
            print(f"  [cached] {exp_id:<28} F1={c['metrics']['f1']:.3f} "
                  f"drop={c['degradation_f1']['pct_drop']:+.1f}%")
            return c
        seqs, labels = fn()
        result = evaluate(model, seqs, labels, threshold)
        payload = _save(exp_id, group, label, params, result, clean["metrics"])
        print(f"  [ok]     {exp_id:<28} F1={payload['metrics']['f1']:.3f} "
              f"drop={payload['degradation_f1']['pct_drop']:+.1f}%")
        return payload

    print("=" * 66)
    print("  ROBUSTNESS EXPERIMENTS 1-11 (frozen production model, TEST split)")
    print("=" * 66)

    # E00 — clean baseline (always needed as the reference)
    c0 = cached("E00_clean")
    if c0 is None:
        clean = evaluate(model, te_s, te_l, threshold)
        _save("E00_clean", "baseline", "Clean test set", {}, clean, clean["metrics"])
        print(f"  [ok]     E00_clean                    F1={clean['metrics']['f1']:.3f}  (reference)")
    else:
        clean = {"metrics": c0["metrics"]}
        print(f"  [cached] E00_clean                    F1={clean['metrics']['f1']:.3f}  (reference)")

    # E01 — Gaussian noise
    for s in GAUSSIAN_SIGMAS:
        maybe_run(f"E01_gauss_{s}", "noise", f"Gaussian sigma={s}", {"sigma": s},
                  lambda s=s: (P.gaussian_noise(te_s, s, SEED), te_l))

    # E02 — sensor noise
    for kind in ("offset", "drift", "quantization", "spike"):
        maybe_run(f"E02_sensor_{kind}", "sensor_noise", f"Sensor noise: {kind}", {"kind": kind},
                  lambda kind=kind: (P.sensor_noise(te_s, cols, kind, 0.3, SEED), te_l))

    # E03 — missing values x imputation
    for f in MISSING_FRACS:
        for imp in IMPUTATIONS:
            maybe_run(f"E03_missing_{f}_{imp}", "missing", f"Missing {f*100:.0f}% ({imp})",
                      {"frac": f, "impute": imp},
                      lambda f=f, imp=imp: (P.missing_values(te_s, f, imp, SEED), te_l))

    # E04 — sensor failure
    for mode in ("random_single", "critical", "multiple"):
        maybe_run(f"E04_failure_{mode}", "sensor_failure", f"Sensor failure: {mode}", {"mode": mode},
                  lambda mode=mode: (P.sensor_failure(te_s, cols, mode, SEED), te_l))

    # E05 — feature corruption scan (ranking over ALL features, one result file)
    if not only or only == "E05_feature_scan":
        c = cached("E05_feature_scan")
        if c:
            print(f"  [cached] E05_feature_scan            (ranking of {len(c['ranking'])} features)")
        else:
            ranking = []
            for j, name in enumerate(cols):
                seqs = P.corrupt_feature(te_s, j, SEED)
                r = evaluate(model, seqs, te_l, threshold, n_boot=0)
                ranking.append({"feature": name, "f1": round(r["metrics"]["f1"], 4),
                                "auc": round(r["metrics"]["roc_auc"], 4)})
            ranking.sort(key=lambda x: x["f1"])   # most damaging corruption first
            payload = {"id": "E05_feature_scan", "group": "feature_corruption",
                      "clean_f1": clean["metrics"]["f1"], "ranking": ranking}
            (RES / "E05_feature_scan.json").write_text(json.dumps(payload, indent=2))
            print(f"  [ok]     E05_feature_scan            most-damaging: {ranking[0]['feature']} "
                  f"(F1->{ranking[0]['f1']:.3f})")

    # E06 — packet loss
    for f in PACKET_LOSS_FRACS:
        maybe_run(f"E06_packetloss_{f}", "packet_loss", f"Packet loss {f*100:.0f}%", {"frac": f},
                  lambda f=f: (P.packet_loss(te_s, f, SEED), te_l))

    # E07 — timestamp jitter
    for p in JITTER_PROBS:
        maybe_run(f"E07_jitter_{p}", "jitter", f"Timestamp jitter p={p}", {"prob": p},
                  lambda p=p: (P.timestamp_jitter(te_s, p, SEED), te_l))

    # E08 — data drift
    for d in DRIFT_LEVELS:
        maybe_run(f"E08_drift_{d}", "drift", f"Data drift level={d}", {"level": d},
                  lambda d=d: (P.data_drift(te_s, d, SEED), te_l))

    # E09 — concept drift (attack signature dampened toward normal)
    for lv in CONCEPT_DRIFT_LEVELS:
        maybe_run(f"E09_conceptdrift_{lv}", "concept_drift", f"Concept drift level={lv}", {"level": lv},
                  lambda lv=lv: (P.concept_drift(te_s, te_l, lv, SEED), te_l))

    # E10 — unknown / zero-day-proxy attacks (synthetic subset, own labels)
    for kind in UNKNOWN_ATTACK_KINDS:
        exp_id = f"E10_unknown_{kind}"
        if only and exp_id != only:
            continue
        c = cached(exp_id)
        if c:
            print(f"  [cached] {exp_id:<28} detect_rate={c['metrics']['recall']:.3f}")
            continue
        atk_seqs, atk_lab = P.synth_unknown_attack(te_s, te_l, cols, kind, SEED)
        normal_seqs = te_s[te_l == 0][:len(atk_seqs)]
        seqs = np.concatenate([atk_seqs, normal_seqs])
        labels = np.concatenate([atk_lab, np.zeros(len(normal_seqs), int)])
        result = evaluate(model, seqs, labels, threshold, n_boot=100)
        payload = _save(exp_id, "unknown_attack", f"Unknown attack: {kind}", {"kind": kind},
                        result, clean["metrics"])
        print(f"  [ok]     {exp_id:<28} detect_rate={payload['metrics']['recall']:.3f} "
              f"fpr={payload['metrics']['fpr']:.3f}")

    # E11 — out-of-distribution samples
    for lv in OOD_LEVELS:
        exp_id = f"E11_ood_{lv}"
        if only and exp_id != only:
            continue
        c = cached(exp_id)
        if c:
            print(f"  [cached] {exp_id:<28} flagged={c['flagged_frac']:.3f}")
            continue
        ood = P.ood_samples(te_s, lv, SEED)
        from robustness.common import recon_scores
        scores = recon_scores(model, ood)
        flagged = float((scores >= threshold).mean())
        payload = {"id": exp_id, "group": "ood", "level": lv,
                  "flagged_frac": round(flagged, 4),
                  "mean_score": round(float(scores.mean()), 6),
                  "clean_mean_normal_score": round(float(recon_scores(model, te_s[te_l == 0]).mean()), 6)}
        (RES / f"{exp_id}.json").write_text(json.dumps(payload, indent=2))
        print(f"  [ok]     {exp_id:<28} flagged={flagged:.3f} (OOD score should be >> normal)")

    print("=" * 66)
    print(f"  Done. Results in {RES}")
    print("  Next: python -m robustness.report")
    print("=" * 66)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", type=str, default=None)
    ap.add_argument("--fresh", action="store_true")
    args = ap.parse_args()
    run_all(only=args.only, fresh=args.fresh)


if __name__ == "__main__":
    main()
