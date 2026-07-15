"""
adversarial_test.py — Adversarial robustness evaluation.

Tests whether the model can detect FDIA attacks that are crafted to
stay within 2 standard deviations of zone_consumption_mean, making
them invisible to simple statistical threshold detectors.

This is the specific vulnerability identified in the expert review:
  zone_consumption_mean has XAI contribution 21.2 (4x any other feature).
  An attacker who knows this can craft injections that bypass detection.

Four adversarial scenarios tested:
  1. Naive FDIA          — large obvious spike (baseline, should detect)
  2. Stealthy FDIA       — injection within 2-sigma of normal zone mean
  3. Slow-ramp FDIA      — gradual escalation over 20 readings (temporal blind spot)
  4. Coordinated FDIA    — simultaneous injection on all zone meters (normalises zone mean)

Output:
  outputs/adversarial/adversarial_results.csv
  outputs/adversarial/adversarial_detection_chart.png
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
OUT_DIR = ROOT / "outputs" / "adversarial"
OUT_DIR.mkdir(parents=True, exist_ok=True)

STYLE = {
    "bg": "#0F172A", "grid": "#1E293B", "text": "#F8FAFC",
    "detected":   "#4ADE80",   # green
    "missed":     "#F87171",   # red
    "accent":     "#38BDF8",
    "warn":       "#F59E0B",
}


def _style_ax(ax, fig):
    fig.patch.set_facecolor(STYLE["bg"])
    ax.set_facecolor(STYLE["grid"])
    ax.tick_params(colors=STYLE["text"], labelsize=9)
    ax.xaxis.label.set_color(STYLE["text"])
    ax.yaxis.label.set_color(STYLE["text"])
    ax.title.set_color(STYLE["text"])
    for spine in ax.spines.values():
        spine.set_edgecolor("#334155")
    ax.grid(True, color="#334155", alpha=0.5, linewidth=0.5)


def load_detector():
    from ml_pipeline.realtime_detector import get_detector
    det = get_detector()
    if det is None:
        print("[ERROR] Could not load detector. Run from smartgrid_simulation/")
        sys.exit(1)
    return det


def make_normal_reading(meter_id: str, idx: int,
                        zone_mean_kw: float = 6.0) -> dict:
    """Produce a plausible normal reading for a Zone A residential meter."""
    np.random.seed(idx)
    hour = (idx * 2) % 24  # 2-min interval → cycles through day
    # Residential: morning/evening peaks
    if 6 <= hour <= 9 or 17 <= hour <= 22:
        base_kw = 2.5 + np.random.normal(0, 0.3)
    elif 23 <= hour or hour <= 5:
        base_kw = 0.6 + np.random.normal(0, 0.1)
    else:
        base_kw = 1.4 + np.random.normal(0, 0.2)
    base_kw = max(0.1, base_kw)
    tension_v = 220.0 + np.random.normal(0, 1.5)
    courant_a = (base_kw * 1000) / max(tension_v, 1.0)
    return {
        "meter_id":        meter_id,
        "timestamp":       f"2026-06-15 {hour:02d}:{(idx*2)%60:02d}:00",
        "consommation_kw": round(base_kw, 3),
        "tension_v":       round(tension_v, 3),
        "courant_a":       round(courant_a, 3),
        "power_factor":    round(0.93 + np.random.normal(0, 0.01), 4),
        "zone":            "Zone A",
        "type":            "residentiel",
        "zone_consumption_mean": round(zone_mean_kw + np.random.normal(0, 0.5), 3),
    }


def warm_up_buffer(detector, meter_id: str, n: int = 10) -> None:
    """Send n normal readings to fill the rolling buffer."""
    for i in range(n):
        r = make_normal_reading(meter_id, i)
        detector.ingest(r)


# ── Scenario builders ─────────────────────────────────────────────────────────

def scenario_naive_fdia(detector, meter_id: str) -> list[dict]:
    """Large obvious voltage spike — should always be detected."""
    warm_up_buffer(detector, meter_id)
    results = []
    for i in range(20):
        r = make_normal_reading(meter_id, 100 + i)
        # Multiply voltage by 1.25 — obvious 25% spike
        r["tension_v"]       = round(r["tension_v"] * 1.25, 3)
        r["consommation_kw"] = round(r["consommation_kw"] * 1.30, 3)
        r["courant_a"]       = round(r["courant_a"] * 1.20, 3)
        res = detector.ingest(r)
        results.append({
            "scenario": "Naive FDIA (25% voltage spike)",
            "step": i, "is_anomaly": res.get("is_anomaly", False),
            "score": res.get("anomaly_score", 0),
            "threshold": res.get("threshold", 0),
        })
    return results


def scenario_stealthy_fdia(detector, meter_id: str,
                           zone_std: float = 1.2) -> list[dict]:
    """
    Injection within 2-sigma of zone_consumption_mean.
    Attack vector: keep zone mean undisturbed while falsifying voltage/current.
    This is the exact weakness identified in the expert review.
    """
    warm_up_buffer(detector, meter_id)
    results = []
    for i in range(20):
        r = make_normal_reading(meter_id, 200 + i, zone_mean_kw=6.0)
        # Stealthy: falsify voltage by +6% (within normal tolerance)
        # but keep consumption close to normal zone mean
        r["tension_v"] = round(r["tension_v"] * 1.06, 3)   # +6% — subtle
        # Zone mean injection: small enough to stay within 2-sigma
        fdia_delta = np.random.uniform(0.5, 1.8)            # < 2 * 1.2 = 2.4 sigma
        r["consommation_kw"] = round(r["consommation_kw"] + fdia_delta, 3)
        r["zone_consumption_mean"] = round(
            r["zone_consumption_mean"] + fdia_delta * 0.08,  # spread across zone → small impact
            3
        )
        r["courant_a"] = round((r["consommation_kw"] * 1000) / max(r["tension_v"], 1.0), 3)
        res = detector.ingest(r)
        results.append({
            "scenario": "Stealthy FDIA (within 2-sigma zone mean)",
            "step": i, "is_anomaly": res.get("is_anomaly", False),
            "score": res.get("anomaly_score", 0),
            "threshold": res.get("threshold", 0),
            "fdia_delta_kw": round(fdia_delta, 3),
        })
    return results


def scenario_slow_ramp_fdia(detector, meter_id: str) -> list[dict]:
    """
    Gradual escalation over 20 readings (40 minutes at 2-min interval).
    Each step injects +3% more consumption.
    Tests whether temporal pattern detection catches slow attacks.
    """
    warm_up_buffer(detector, meter_id)
    results = []
    for i in range(20):
        r = make_normal_reading(meter_id, 300 + i)
        ramp = 1.0 + i * 0.03   # 0% at step 0, 57% at step 19
        r["consommation_kw"] = round(r["consommation_kw"] * ramp, 3)
        r["courant_a"]       = round(r["courant_a"] * ramp, 3)
        r["zone_consumption_mean"] = round(
            r["zone_consumption_mean"] + (ramp - 1.0) * r["consommation_kw"] * 0.05, 3
        )
        res = detector.ingest(r)
        results.append({
            "scenario": "Slow-ramp FDIA (+3%/step over 20 steps)",
            "step": i, "is_anomaly": res.get("is_anomaly", False),
            "score": res.get("anomaly_score", 0),
            "threshold": res.get("threshold", 0),
            "ramp_factor": round(ramp, 3),
        })
    return results


def scenario_coordinated_fdia(detector_factory, zone_meters: list[str]) -> list[dict]:
    """
    Simultaneous injection on ALL meters in a zone.
    Zone mean rises together — model sees zone_consumption_mean as 'normal'
    because every meter is falsified by the same amount.
    This is the most sophisticated FDIA variant.
    """
    # Need fresh detectors for each meter to avoid cross-contamination
    detectors = {mid: detector_factory() for mid in zone_meters}
    for mid, det in detectors.items():
        warm_up_buffer(det, mid)

    results = []
    for i in range(20):
        # All meters get +20% injection simultaneously
        injection_factor = 1.20
        for mid, det in detectors.items():
            r = make_normal_reading(mid, 400 + i)
            r["consommation_kw"] = round(r["consommation_kw"] * injection_factor, 3)
            r["courant_a"]       = round(r["courant_a"] * injection_factor, 3)
            # Zone mean also rises by same factor → looks normal to zone-based features
            r["zone_consumption_mean"] = round(
                r["zone_consumption_mean"] * injection_factor, 3
            )
            res = det.ingest(r)
            results.append({
                "scenario": "Coordinated FDIA (all zone meters +20%)",
                "step": i, "meter_id": mid,
                "is_anomaly": res.get("is_anomaly", False),
                "score": res.get("anomaly_score", 0),
                "threshold": res.get("threshold", 0),
            })
    return results


# ── Result analysis ───────────────────────────────────────────────────────────

def detection_rate(rows: list[dict]) -> float:
    valid = [r for r in rows if r.get("score", 0) > 0]
    if not valid:
        return 0.0
    return sum(r["is_anomaly"] for r in valid) / len(valid)


def plot_adversarial_results(all_results: dict[str, list[dict]], out_path: Path):
    scenarios = list(all_results.keys())
    n = len(scenarios)
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.flatten()
    _style_ax(axes[0], fig)

    for ax, (scenario_name, rows) in zip(axes, all_results.items()):
        _style_ax(ax, fig)
        valid_rows = [r for r in rows if r.get("score", 0) > 0]
        if not valid_rows:
            ax.text(0.5, 0.5, "No data", ha="center", transform=ax.transAxes,
                    color=STYLE["text"])
            continue

        steps  = [r["step"] for r in valid_rows]
        scores = [r.get("score", 0) for r in valid_rows]
        thresholds = [r.get("threshold", 0) for r in valid_rows]
        detected   = [r["is_anomaly"] for r in valid_rows]
        det_rate   = sum(detected) / len(detected) if detected else 0

        ax.plot(steps, scores,     color=STYLE["accent"], lw=2, label="Anomaly score")
        ax.plot(steps, thresholds, color=STYLE["warn"],   lw=1.5, ls="--", label="Threshold")

        # Mark detections
        for step, score, is_det in zip(steps, scores, detected):
            color = STYLE["detected"] if is_det else STYLE["missed"]
            ax.scatter(step, score, color=color, zorder=5, s=40)

        ax.set_xlabel("Step")
        ax.set_ylabel("Anomaly Score (MSE)")
        short_name = scenario_name[:45] + "..." if len(scenario_name) > 45 else scenario_name
        ax.set_title(f"{short_name}\nDetection rate: {det_rate:.0%}")

        # Legend with dots
        from matplotlib.lines import Line2D
        legend_elems = [
            Line2D([0], [0], color=STYLE["accent"], lw=2, label="Score"),
            Line2D([0], [0], color=STYLE["warn"], lw=1.5, ls="--", label="Threshold"),
            Line2D([0], [0], marker="o", color=STYLE["detected"], ls="", label="Detected"),
            Line2D([0], [0], marker="o", color=STYLE["missed"],   ls="", label="Missed"),
        ]
        leg = ax.legend(handles=legend_elems, fontsize=8,
                        framealpha=0.3, facecolor=STYLE["grid"])
        for t in leg.get_texts():
            t.set_color(STYLE["text"])

    fig.suptitle("Adversarial FDIA Robustness Test\n"
                 "Green dots = detected, Red dots = missed  |  "
                 "Lower detection rate on subtle attacks = model weakness",
                 color=STYLE["text"], fontsize=12)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=STYLE["bg"])
    plt.close(fig)
    print(f"  Saved: {out_path}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    from ml_pipeline.realtime_detector import get_detector, _load_single, EnsembleDetector

    print("=" * 60)
    print("  Adversarial FDIA Robustness Test")
    print("=" * 60)

    det = load_detector()

    # For coordinated scenario: need one detector per meter
    base = Path(__file__).resolve().parent
    def fresh_detector():
        return _load_single(base, "outputs/early_stopping_final") or \
               _load_single(base, "outputs/test_run_now")

    all_results: dict[str, list[dict]] = {}

    print("\n[1/4] Naive FDIA (obvious 25% spike) ...")
    rows1 = scenario_naive_fdia(det, "SM_0001")
    all_results["Naive FDIA (25% voltage spike)"] = rows1
    dr1 = detection_rate(rows1)
    print(f"  Detection rate: {dr1:.0%}  ({'PASS' if dr1 >= 0.7 else 'FAIL'})")

    print("\n[2/4] Stealthy FDIA (within 2-sigma zone mean) ...")
    rows2 = scenario_stealthy_fdia(det, "SM_0002")
    all_results["Stealthy FDIA (within 2-sigma zone mean)"] = rows2
    dr2 = detection_rate(rows2)
    print(f"  Detection rate: {dr2:.0%}  ({'PASS' if dr2 >= 0.5 else 'WEAK -- adversarially vulnerable'})")

    print("\n[3/4] Slow-ramp FDIA (+3%/step over 20 steps) ...")
    rows3 = scenario_slow_ramp_fdia(det, "SM_0003")
    all_results["Slow-ramp FDIA (+3%/step over 20 steps)"] = rows3
    dr3 = detection_rate(rows3)
    print(f"  Detection rate: {dr3:.0%}  ({'PASS' if dr3 >= 0.5 else 'WEAK -- slow escalation missed'})")

    print("\n[4/4] Coordinated FDIA (all zone meters +20% simultaneously) ...")
    zone_a_meters = [f"SM_{i:04d}" for i in range(1, 13)][:4]  # first 4 to save time
    rows4 = scenario_coordinated_fdia(fresh_detector, zone_a_meters)
    all_results["Coordinated FDIA (all zone meters +20%)"] = rows4
    dr4 = detection_rate(rows4)
    print(f"  Detection rate: {dr4:.0%}  ({'PASS' if dr4 >= 0.5 else 'WEAK -- zone-mean camouflage effective'})")

    # Save CSV
    flat_rows = []
    for scenario_name, rows in all_results.items():
        for r in rows:
            flat_rows.append({**r, "scenario": scenario_name})
    df = pd.DataFrame(flat_rows)
    csv_path = OUT_DIR / "adversarial_results.csv"
    df.to_csv(csv_path, index=False)
    print(f"\n  Results saved: {csv_path}")

    # Plot
    chart_path = OUT_DIR / "adversarial_detection_chart.png"
    plot_adversarial_results(all_results, chart_path)

    print("\n" + "=" * 60)
    print("  ADVERSARIAL ROBUSTNESS SUMMARY")
    print("=" * 60)
    scenarios_summary = [
        ("Naive FDIA      (25% spike)", dr1, 0.70),
        ("Stealthy FDIA   (2-sigma)",   dr2, 0.50),
        ("Slow-ramp FDIA  (+3%/step)",  dr3, 0.50),
        ("Coordinated FDIA(zone-wide)", dr4, 0.50),
    ]
    for name, dr, threshold in scenarios_summary:
        status = "[PASS]" if dr >= threshold else "[FAIL]"
        bar = "#" * int(dr * 20) + "." * (20 - int(dr * 20))
        print(f"  {status} {name}: |{bar}| {dr:.0%}")

    low_dr = [dr for _, dr, t in scenarios_summary if dr < t]
    if low_dr:
        print("\n  RECOMMENDATION: Model is adversarially vulnerable.")
        print("  -> Add zone_consumption_std feature to break zone-mean camouflage")
        print("  -> Add temporal diff features (consommation_kw_diff over 10+ steps)")
        print("  -> Consider adversarial training with coordinated FDIA examples")
    else:
        print("\n  Model shows adequate adversarial robustness.")
    print("=" * 60)


if __name__ == "__main__":
    main()
