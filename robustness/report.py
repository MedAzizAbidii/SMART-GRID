"""
robustness/report.py — tables, publication figures, and the composite Final
Robustness Score, assembled from robustness/results/*.json.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
RES, PLOTS, REPORTS = HERE / "results", HERE / "plots", HERE / "reports"
_PAL = ["#2C6FA6", "#C4892A", "#2E9E68", "#C1443A", "#7A5BA6", "#1F9E9E"]
plt.rcParams.update({"figure.dpi": 140, "font.size": 9, "axes.grid": True,
                     "grid.alpha": 0.3, "axes.spines.top": False, "axes.spines.right": False})


def _load(prefix):
    out = []
    for f in sorted(RES.glob(f"{prefix}*.json")):
        try:
            out.append(json.loads(f.read_text()))
        except Exception:
            pass
    return out


def load_all():
    clean = json.loads((RES / "E00_clean.json").read_text())
    gauss = _load("E01_gauss_")
    sensor = _load("E02_sensor_")
    missing = _load("E03_missing_")
    failure = _load("E04_failure_")
    feat_scan = json.loads((RES / "E05_feature_scan.json").read_text()) if (RES / "E05_feature_scan.json").exists() else None
    packet = _load("E06_packetloss_")
    jitter = _load("E07_jitter_")
    drift = _load("E08_drift_")
    concept = _load("E09_conceptdrift_")
    unknown = _load("E10_unknown_")
    ood = _load("E11_ood_")
    adv = json.loads((RES / "E12_adversarial.json").read_text()) if (RES / "E12_adversarial.json").exists() else None
    reliab = sorted(RES.glob("reliability_*.json"))
    reliab = json.loads(reliab[-1].read_text()) if reliab else None
    stress = json.loads((RES / "stress_results.json").read_text()) if (RES / "stress_results.json").exists() else None
    return dict(clean=clean, gauss=gauss, sensor=sensor, missing=missing, failure=failure,
               feat_scan=feat_scan, packet=packet, jitter=jitter, drift=drift, concept=concept,
               unknown=unknown, ood=ood, adv=adv, reliability=reliab, stress=stress)


# ── figures ───────────────────────────────────────────────────────────────────

def fig_noise_curve(gauss, clean_f1, out):
    xs = [g["params"]["sigma"] for g in gauss]
    ys = [g["metrics"]["f1"] for g in gauss]
    fig, ax = plt.subplots(figsize=(6, 4.5))
    ax.plot(xs, ys, "o-", color=_PAL[3])
    ax.axhline(clean_f1, color="k", ls="--", lw=1, label=f"clean F1={clean_f1:.3f}")
    ax.set_xlabel("Gaussian noise σ (feature units)"); ax.set_ylabel("F1 (test)")
    ax.set_title("Noise sensitivity"); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(out); plt.close(fig)


def fig_missing_curve(missing, out):
    fig, ax = plt.subplots(figsize=(7, 4.5))
    imps = sorted(set(m["params"]["impute"] for m in missing))
    for i, imp in enumerate(imps):
        rows = sorted([m for m in missing if m["params"]["impute"] == imp],
                     key=lambda m: m["params"]["frac"])
        ax.plot([r["params"]["frac"] for r in rows], [r["metrics"]["f1"] for r in rows],
                "o-", color=_PAL[i % len(_PAL)], label=imp)
    ax.set_xlabel("missing fraction"); ax.set_ylabel("F1")
    ax.set_title("Missing-data robustness by imputation strategy"); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(out); plt.close(fig)


def fig_drift_curve(drift, concept, out):
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    d = sorted(drift, key=lambda x: x["params"]["level"])
    axes[0].plot([x["params"]["level"] for x in d], [x["metrics"]["f1"] for x in d], "o-", color=_PAL[0])
    axes[0].set_xlabel("drift level (std units)"); axes[0].set_ylabel("F1"); axes[0].set_title("Data drift")
    c = sorted(concept, key=lambda x: x["params"]["level"])
    axes[1].plot([x["params"]["level"] for x in c], [x["metrics"]["recall"] for x in c], "o-", color=_PAL[2])
    axes[1].set_xlabel("concept-drift level (0=orig attack, 1=disguised)")
    axes[1].set_ylabel("detection rate (recall)"); axes[1].set_title("Concept drift adaptation")
    fig.tight_layout(); fig.savefig(out); plt.close(fig)


def fig_feature_heatmap(feat_scan, out, top=20):
    if not feat_scan:
        return False
    rk = feat_scan["ranking"][:top]
    fig, ax = plt.subplots(figsize=(7, 0.3 * len(rk) + 1.5))
    vals = [r["f1"] for r in rk]
    ax.barh(range(len(rk)), vals, color=[_PAL[3] if v < feat_scan["clean_f1"] * 0.7 else _PAL[0] for v in vals])
    ax.axvline(feat_scan["clean_f1"], color="k", ls="--", lw=1, label="clean F1")
    ax.set_yticks(range(len(rk))); ax.set_yticklabels([r["feature"] for r in rk], fontsize=7)
    ax.set_xlabel("F1 after corrupting this feature alone")
    ax.set_title(f"Top {top} most fragile features"); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(out); plt.close(fig)
    return True


def fig_adversarial(adv, out):
    if not adv:
        return False
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    for name, color in (("fgsm", _PAL[3]), ("pgd", _PAL[0])):
        rows = adv[name]
        ax.plot([r["epsilon"] for r in rows], [r["detect_rate"] for r in rows],
                "o-", color=color, label=name.upper())
    ax.set_xlabel("L∞ perturbation budget ε (feature-space)")
    ax.set_ylabel("detection rate on attack sequences")
    ax.set_title("Adversarial evasion robustness"); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(out); plt.close(fig)
    return True


def fig_reliability(reliab, out):
    if not reliab or not reliab.get("samples"):
        return False
    s = reliab["samples"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    axes[0].plot([x["t_s"] for x in s], [x["rss_mb"] for x in s], color=_PAL[0])
    axes[0].set_xlabel("time (s)"); axes[0].set_ylabel("RSS memory (MB)"); axes[0].set_title("Memory over time")
    axes[1].plot([x["t_s"] for x in s], [x["latency_ms"] for x in s], color=_PAL[3], lw=0.7)
    axes[1].set_xlabel("time (s)"); axes[1].set_ylabel("latency (ms)"); axes[1].set_title("Latency over time")
    fig.tight_layout(); fig.savefig(out); plt.close(fig)
    return True


def fig_stress(stress, out):
    if not stress:
        return False
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    ns = [r["target"] for r in stress]
    axes[0].plot(ns, [r["throughput_seq_per_s"] for r in stress], "o-", color=_PAL[0])
    axes[0].set_xscale("log"); axes[0].set_xlabel("N sequences"); axes[0].set_ylabel("throughput (seq/s)")
    axes[0].set_title("Throughput scaling")
    axes[1].plot(ns, [r["rss_delta_mb"] for r in stress], "o-", color=_PAL[2])
    axes[1].set_xscale("log"); axes[1].set_xlabel("N sequences"); axes[1].set_ylabel("memory delta (MB)")
    axes[1].set_title("Memory scaling")
    fig.tight_layout(); fig.savefig(out); plt.close(fig)
    return True


# ── final robustness score ────────────────────────────────────────────────────

def compute_scores(data):
    clean_f1 = data["clean"]["metrics"]["f1"]
    clean_recall = data["clean"]["metrics"]["recall"]

    def avg_retention(items, baseline, key=lambda x: x["metrics"]["f1"]):
        """Mean retention ratio (perturbed/baseline), CAPPED at 100% per item —
        a metric that improves under perturbation means 'fully retained', not
        a bonus that should inflate the composite score above what a perfect
        no-degradation result would score."""
        if not items or baseline <= 0:
            return None
        vals = [min(1.0, max(0.0, key(x) / baseline)) for x in items]
        return float(np.mean(vals)) * 100

    scores = {
        "noise_robustness": avg_retention(data["gauss"], clean_f1),
        "missing_data_robustness": avg_retention(data["missing"], clean_f1),
        "sensor_fault_robustness": avg_retention(data["sensor"] + data["failure"], clean_f1),
        "drift_robustness": avg_retention(data["drift"], clean_f1),
        # correct baseline: recall vs CLEAN RECALL, not clean F1 (unit match)
        "concept_drift_adaptation": avg_retention(
            data["concept"], clean_recall, key=lambda x: x["metrics"]["recall"]),
        "unknown_attack_detection": (min(100.0, float(np.mean([u["metrics"]["recall"] for u in data["unknown"]])) * 100)
                                     if data["unknown"] else None),
        "ood_detection": (min(100.0, float(np.mean([o["flagged_frac"] for o in data["ood"]])) * 100)
                          if data["ood"] else None),
        "adversarial_robustness": (min(100.0, float(np.mean([r["detect_rate"] for r in data["adv"]["pgd"]])) * 100)
                                   if data.get("adv") else None),
        "reliability": (100.0 - min(100.0, (data["reliability"]["crash_rate"] * 100))
                        if data.get("reliability") else None),
        "scalability": (100.0 if data.get("stress") and all(r["completed"] for r in data["stress"]) else
                        (50.0 if data.get("stress") else None)),
    }
    valid = [v for v in scores.values() if v is not None]
    scores["overall_robustness_score"] = round(float(np.mean(valid)), 1) if valid else None
    return {k: (round(v, 1) if v is not None else None) for k, v in scores.items()}


def export_tables(data):
    RES.mkdir(exist_ok=True)
    rows = []
    for group_name, items in (("gaussian_noise", data["gauss"]), ("sensor_noise", data["sensor"]),
                              ("missing_values", data["missing"]), ("sensor_failure", data["failure"]),
                              ("packet_loss", data["packet"]), ("timestamp_jitter", data["jitter"]),
                              ("data_drift", data["drift"]), ("concept_drift", data["concept"])):
        for it in items:
            rows.append({"experiment": group_name, "label": it["label"],
                        "f1": it["metrics"]["f1"], "roc_auc": it["metrics"]["roc_auc"],
                        "pct_drop": it["degradation_f1"]["pct_drop"]})
    df = pd.DataFrame(rows)
    df.to_csv(RES / "robustness_summary.csv", index=False)
    try:
        df.to_excel(RES / "robustness_summary.xlsx", index=False)
    except Exception:
        pass
    df.round(4).to_latex(RES / "robustness_summary.tex", index=False,
                         caption="Robustness degradation summary (held-out test).",
                         label="tab:robustness")
    return df


def markdown_report(data, scores, df, figs):
    REPORTS.mkdir(exist_ok=True, parents=True)
    import shutil
    rep_figs = []
    for f in figs:
        dst = REPORTS / f.name; shutil.copy2(f, dst); rep_figs.append(dst)
    L = []; A = L.append
    A("# Robustness, Generalization & Resilience Report\n")
    A(f"*Generated {datetime.now():%Y-%m-%d %H:%M} · frozen production model · "
      f"leak-free held-out test split*\n")
    A("## Scope note\n")
    A("Reliability was executed as a **short, fully-instrumented smoke test** "
      "(not a literal 24/48/72h run — infeasible inside an interactive session); "
      "the identical script accepts `--seconds 86400/172800/259200` to run the "
      "literal soak unattended. Stress testing measures **engineering throughput/"
      "memory scaling** via chunked synthetic-load generation (never materializing "
      "the full N in memory) — it is a scale test, not a claim of N realistic "
      "grid readings. Both distinctions are load-bearing for correct interpretation.\n")
    A(f"Clean baseline (held-out test, frozen model/threshold): **F1={data['clean']['metrics']['f1']:.4f}**, "
      f"AUC={data['clean']['metrics']['roc_auc']:.4f}.\n")

    A("## Final Robustness Scores (0-100, higher=better)\n")
    A("| Dimension | Score |\n|---|---|")
    for k, v in scores.items():
        A(f"| {k.replace('_',' ').title()} | {v if v is not None else 'n/a'} |")
    A("")

    A("## 1-2. Noise & sensor-fault robustness\n")
    A(f"Average performance retention under Gaussian noise: "
      f"**{scores['noise_robustness']}%** of clean F1. Sensor faults (offset/drift/"
      f"quantization/spike/outage): **{scores['sensor_fault_robustness']}%** retention.\n")

    A("## 3. Missing values\n")
    A("See `robustness_summary.csv` for the full frac×imputation grid; "
      f"overall retention **{scores['missing_data_robustness']}%**.\n")

    A("## 5. Feature sensitivity ranking\n")
    if data["feat_scan"]:
        top3 = data["feat_scan"]["ranking"][:3]
        A("Most fragile features (lowest F1 when corrupted alone): " +
          ", ".join(f"`{t['feature']}` (F1→{t['f1']:.3f})" for t in top3) + ".\n")

    A("## 6-7. Packet loss & timestamp jitter\n")
    A(f"Packet loss retention included in the summary table; timestamp jitter "
      "tests bounded temporal perturbation (adjacent-timestep swaps), distinct "
      "from the full time-shuffle used in the Phase 2.5 investigation.\n")

    A("## 8-9. Distribution drift & concept drift\n")
    A(f"Drift robustness: **{scores['drift_robustness']}%**. Concept-drift "
      f"adaptation (recall as attacks are disguised toward normal): "
      f"**{scores['concept_drift_adaptation']}%** — this measures a FROZEN "
      "model's resilience with no retraining, the realistic single-deployment case.\n")

    A("## 10-11. Unknown attacks & OOD\n")
    if data["unknown"]:
        A("Zero-day-proxy detection rate per synthetic pattern:\n")
        for u in data["unknown"]:
            A(f"- {u['label']}: recall={u['metrics']['recall']:.3f}, FPR={u['metrics']['fpr']:.3f}")
    if data["ood"]:
        A("\nOut-of-distribution flagging rate (should approach 1.0):\n")
        for o in data["ood"]:
            A(f"- level={o['level']}: flagged={o['flagged_frac']:.3f} "
              f"(mean score {o['mean_score']:.5f} vs normal {o['clean_mean_normal_score']:.5f})")
    A("")

    A("## 12. Adversarial robustness\n")
    if data.get("adv"):
        A("See `robustness/adversarial.py` for the full threat-model discussion. "
          "Detection rate on attack sequences under increasing L∞ evasion budget:\n")
        A("| ε | FGSM detect-rate | PGD detect-rate |\n|---|---|---|")
        for f, p in zip(data["adv"]["fgsm"], data["adv"]["pgd"]):
            A(f"| {f['epsilon']} | {f['detect_rate']:.3f} | {p['detect_rate']:.3f} |")
    A("")

    A("## Reliability\n")
    if data.get("reliability"):
        r = data["reliability"]
        A(f"Measured over {r['duration_s']:.0f}s: {r['n_calls']} inference calls, "
          f"{r['errors']} errors (crash rate {r['crash_rate']:.4f}), memory growth "
          f"{r['mem_growth_mb']:+.2f}MB ({r['mem_growth_rate_mb_per_hour']:+.3f} MB/h "
          f"extrapolated), p99 latency {r['latency_p99_ms']}ms.\n")

    A("## Stress test\n")
    if data.get("stress"):
        for r in data["stress"]:
            A(f"- N={r['target']:,}: processed={r['processed']:,}, "
              f"throughput={r['throughput_seq_per_s']:,.0f} seq/s, "
              f"latency={r['latency_ms_per_seq_mean']}ms/seq, "
              f"memory+{r['rss_delta_mb']}MB, [{r['stop_reason']}]")
    A("")

    A("## Figures\n")
    for f in rep_figs:
        A(f"![{f.stem}]({f.name})")
    A("")
    A("## Limitations\n")
    A("- All perturbations applied in scaled feature space of a single "
      "synthetic dataset; real sensor fault modes may differ in magnitude/shape.\n"
      "- Adversarial results are a feature-space worst-case bound (see caveat above).\n"
      "- Reliability/stress figures at extreme scope (72h, 10M) are extrapolated "
      "from short, real, instrumented measurements — re-run the provided scripts "
      "at full scope for literal evidence.\n")

    path = REPORTS / "robustness_report.md"
    path.write_text("\n".join(L), encoding="utf-8")
    return path, rep_figs


def pdf_report(rep_figs, scores):
    try:
        from matplotlib.backends.backend_pdf import PdfPages
    except Exception:
        return None
    pdf = REPORTS / "robustness_report.pdf"
    with PdfPages(pdf) as pp:
        fig, ax = plt.subplots(figsize=(11, 8.5)); ax.axis("off")
        ax.text(0.5, 0.93, "Robustness & Resilience Report", ha="center", fontsize=16, weight="bold")
        rows = [[k.replace("_", " ").title(), str(v)] for k, v in scores.items()]
        t = ax.table(cellText=rows, colLabels=["Dimension", "Score"], loc="center", cellLoc="center")
        t.auto_set_font_size(False); t.set_fontsize(9); t.scale(1, 1.5)
        pp.savefig(fig); plt.close(fig)
        for f in rep_figs:
            try:
                img = plt.imread(str(f)); fig, ax = plt.subplots(figsize=(11, 8.5))
                ax.axis("off"); ax.imshow(img); ax.set_title(f.stem, fontsize=10)
                pp.savefig(fig); plt.close(fig)
            except Exception:
                pass
    return pdf


def main():
    PLOTS.mkdir(parents=True, exist_ok=True)
    data = load_all()
    figs = []
    fig_noise_curve(data["gauss"], data["clean"]["metrics"]["f1"], PLOTS / "noise_curve.png"); figs.append(PLOTS / "noise_curve.png")
    fig_missing_curve(data["missing"], PLOTS / "missing_curve.png"); figs.append(PLOTS / "missing_curve.png")
    fig_drift_curve(data["drift"], data["concept"], PLOTS / "drift_curves.png"); figs.append(PLOTS / "drift_curves.png")
    if fig_feature_heatmap(data["feat_scan"], PLOTS / "feature_sensitivity.png"):
        figs.append(PLOTS / "feature_sensitivity.png")
    if fig_adversarial(data.get("adv"), PLOTS / "adversarial.png"):
        figs.append(PLOTS / "adversarial.png")
    if fig_reliability(data.get("reliability"), PLOTS / "reliability.png"):
        figs.append(PLOTS / "reliability.png")
    if fig_stress(data.get("stress"), PLOTS / "stress.png"):
        figs.append(PLOTS / "stress.png")

    df = export_tables(data)
    scores = compute_scores(data)
    md, rep_figs = markdown_report(data, scores, df, figs)
    pdf = pdf_report(rep_figs, scores)

    print("=" * 60)
    print(f"  Report: {md}" + (f" + {pdf.name}" if pdf else ""))
    print(f"  Tables: {RES}/robustness_summary.(csv,xlsx,tex)")
    print(f"  Overall Robustness Score: {scores['overall_robustness_score']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
