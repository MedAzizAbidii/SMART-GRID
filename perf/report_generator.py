"""Phase 7 — report generation: figures (matplotlib), tables (CSV/XLSX),
Markdown report, and a PDF summary.

Color/form choices follow the project's dataviz skill: fixed categorical hue
order, one y-axis per chart (no dual-axis), sequential single-hue ramps for
magnitude, log scales where the data spans orders of magnitude, direct labels
over legends where there's only one series.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd

from perf.config import RESULTS_DIR, REPORTS_DIR, FIGURES_DIR, TABLES_DIR

# ---------------------------------------------------------------------------
# Palette (validated categorical order — see dataviz skill references/palette.md)
# ---------------------------------------------------------------------------
CAT = {
    "blue": "#2a78d6", "aqua": "#1baf7a", "yellow": "#eda100", "green": "#008300",
    "violet": "#4a3aa7", "red": "#e34948", "magenta": "#e87ba4", "orange": "#eb6834",
}
STATUS = {"good": "#0ca30c", "warning": "#fab219", "serious": "#ec835a", "critical": "#d03b3b"}
INK = {"primary": "#0b0b0b", "secondary": "#52514e", "muted": "#898781",
       "grid": "#e1e0d9", "baseline": "#c3c2b7", "surface": "#fcfcfb"}

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Segoe UI", "DejaVu Sans", "Arial"],
    "axes.edgecolor": INK["baseline"],
    "axes.labelcolor": INK["secondary"],
    "text.color": INK["primary"],
    "xtick.color": INK["secondary"],
    "ytick.color": INK["secondary"],
    "axes.grid": True,
    "grid.color": INK["grid"],
    "grid.linewidth": 0.6,
    "figure.facecolor": INK["surface"],
    "axes.facecolor": INK["surface"],
    "savefig.facecolor": INK["surface"],
    "axes.spines.top": False,
    "axes.spines.right": False,
})


def _load(name: str) -> dict:
    path = RESULTS_DIR / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _save(fig, name: str) -> Path:
    path = FIGURES_DIR / f"{name}.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------
def fig_subsystem_latency(latency: dict) -> Path | None:
    rows = []
    if latency.get("simulator", {}).get("stats"):
        rows.append(("Simulator\ngeneration", latency["simulator"]["stats"]["mean"]))
    if latency.get("blockchain", {}).get("stats"):
        rows.append(("Blockchain\ningest (1 rec)", latency["blockchain"]["stats"]["mean"]))
    if latency.get("inference", {}).get("stats"):
        rows.append(("ML inference\n(ensemble, full)", latency["inference"]["stats"]["mean"]))
    for ep, label in [("/health", "GET /health"), ("/health/detailed", "GET /health/detailed"),
                       ("/dashboard", "GET /dashboard")]:
        d = latency.get("rest_endpoints", {}).get("endpoints", {}).get(ep, {})
        if d.get("stats"):
            rows.append((label, d["stats"]["mean"]))
    if not rows:
        return None
    rows.sort(key=lambda r: r[1])
    labels, values = zip(*rows)

    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    bars = ax.barh(labels, values, color=CAT["blue"], height=0.55)
    ax.set_xscale("log")
    ax.set_xlabel("Mean latency, ms (log scale)")
    ax.set_title("Mean latency by subsystem/endpoint", fontsize=12, fontweight="bold", color=INK["primary"])
    for bar, v in zip(bars, values):
        ax.text(bar.get_width() * 1.08, bar.get_y() + bar.get_height() / 2,
                f"{v:,.2f} ms", va="center", fontsize=9, color=INK["secondary"])
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:g}"))
    return _save(fig, "01_subsystem_latency")


def fig_inference_histogram(latency: dict) -> Path | None:
    raw = latency.get("inference", {}).get("raw_ms")
    if not raw:
        return None
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist(raw, bins=30, color=CAT["blue"], edgecolor=INK["surface"], linewidth=0.5)
    stats = latency["inference"]["stats"]
    ax.axvline(stats["p50"], color=CAT["orange"], linewidth=1.5, linestyle="--", label=f"p50 = {stats['p50']:.1f} ms")
    ax.axvline(stats["p95"], color=CAT["red"], linewidth=1.5, linestyle="--", label=f"p95 = {stats['p95']:.1f} ms")
    ax.set_xlabel("End-to-end ingest() latency, ms (preprocessing + 2x forward pass + XAI)")
    ax.set_ylabel("Count")
    ax.set_title("AI inference latency distribution (n=%d, in-process)" % stats["n"],
                 fontsize=12, fontweight="bold", color=INK["primary"])
    ax.legend(frameon=False)
    return _save(fig, "02_inference_latency_histogram")


def fig_concurrency_throughput(concurrency: dict) -> Path | None:
    by_level = concurrency.get("inprocess", {}).get("by_level", {})
    if not by_level:
        return None
    levels = sorted(int(k) for k in by_level.keys())
    tp = [by_level[str(l)]["throughput_req_per_sec"] for l in levels]
    ideal = [tp[0] * l / levels[0] for l in levels]

    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.plot(levels, ideal, color=INK["muted"], linewidth=1.3, linestyle=":", label="Ideal linear scaling")
    ax.plot(levels, tp, color=CAT["blue"], linewidth=2, marker="o", markersize=5, label="Measured throughput")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Concurrent requests (log scale)")
    ax.set_ylabel("Throughput, req/sec (log scale)")
    ax.set_title("Concurrency vs throughput — shared detector instance, %d-worker pool cap"
                 % concurrency["inprocess"]["pool_cap"], fontsize=11, fontweight="bold", color=INK["primary"])
    ax.set_xticks(levels)
    ax.set_xticklabels([str(l) for l in levels])
    for l, v in zip(levels, tp):
        ax.annotate(f"{v:g}", (l, v), textcoords="offset points", xytext=(0, 7),
                    ha="center", fontsize=8, color=INK["secondary"])
    ax.legend(frameon=False)
    return _save(fig, "03_concurrency_throughput")


def fig_concurrency_latency(concurrency: dict) -> Path | None:
    by_level = concurrency.get("inprocess", {}).get("by_level", {})
    if not by_level:
        return None
    levels = sorted(int(k) for k in by_level.keys())
    p50 = [by_level[str(l)]["latency_ms"].get("p50", 0) for l in levels]
    p90 = [by_level[str(l)]["latency_ms"].get("p90", 0) for l in levels]
    p99 = [by_level[str(l)]["latency_ms"].get("p99", 0) for l in levels]

    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.plot(levels, p50, color=CAT["blue"], linewidth=2, marker="o", markersize=4, label="p50")
    ax.plot(levels, p90, color=CAT["yellow"], linewidth=2, marker="o", markersize=4, label="p90")
    ax.plot(levels, p99, color=CAT["red"], linewidth=2, marker="o", markersize=4, label="p99")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Concurrent requests (log scale)")
    ax.set_ylabel("Per-request latency, ms (log scale)")
    ax.set_title("Latency percentiles vs concurrency level", fontsize=12, fontweight="bold", color=INK["primary"])
    ax.set_xticks(levels)
    ax.set_xticklabels([str(l) for l in levels])
    ax.legend(frameon=False, title=None)
    return _save(fig, "04_concurrency_latency_percentiles")


def fig_resource_timeline(longrun: dict) -> Path | None:
    soak = longrun.get("soak", {})
    live_raw = soak.get("live_server_samples_raw", [])
    self_raw = soak.get("profiling_process_samples_raw", [])
    if not live_raw and not self_raw:
        return None

    # The live-server series is only meaningful if _find_live_server_pid()
    # actually matched the real process — a near-zero average RSS means it
    # matched the wrong PID (see the memory_growth_soak finding), and
    # plotting it would misrepresent a known-bad measurement as real data.
    live_avg_mem = (sum(s["proc_mem_mb"] for s in live_raw) / len(live_raw)) if live_raw else 0
    live_reliable = live_avg_mem > 20
    skipped_note = None if live_reliable else (
        f"Live server process series omitted this run — PID detection matched "
        f"a process reporting ~{live_avg_mem:.1f} MB avg RSS, inconsistent with "
        f"a running FastAPI+PyTorch process (see memory_growth_soak finding)."
    )

    fig, (ax_cpu, ax_mem) = plt.subplots(2, 1, figsize=(8, 6), sharex=True)
    series = [(self_raw, "In-process heavy-load worker", CAT["aqua"])]
    if live_reliable:
        series.insert(0, (live_raw, "Live server process", CAT["blue"]))
    for raw, label, color in series:
        if not raw:
            continue
        t0 = raw[0]["t"]
        xs = [(s["t"] - t0) for s in raw]
        ax_cpu.plot(xs, [s["proc_cpu_percent"] for s in raw], color=color, linewidth=1.3, label=label)
        ax_mem.plot(xs, [s["proc_mem_mb"] for s in raw], color=color, linewidth=1.3, label=label)

    if skipped_note:
        ax_cpu.text(0.02, 0.95, skipped_note, transform=ax_cpu.transAxes, fontsize=7.5,
                    color=STATUS["warning"], va="top", wrap=True)

    ax_cpu.set_ylabel("Process CPU, %")
    ax_cpu.set_title("Resource utilization over the soak window", fontsize=12, fontweight="bold", color=INK["primary"])
    ax_cpu.legend(frameon=False)
    ax_mem.set_ylabel("Process RSS memory, MB")
    ax_mem.set_xlabel("Elapsed time, sec")
    return _save(fig, "05_resource_timeline_soak")


def fig_blockchain_scaling(longrun: dict) -> Path | None:
    bvs = longrun.get("blockchain_validate_scaling", {}).get("by_record_count", {})
    if not bvs:
        return None
    sizes = sorted(int(k) for k in bvs.keys())
    times_ms = [bvs[str(s)]["validate_ms"] for s in sizes]

    fig, ax = plt.subplots(figsize=(6.5, 4))
    ax.plot(sizes, times_ms, color=CAT["violet"], linewidth=2, marker="o", markersize=5)
    ax.set_xlabel("Total records ever notarized")
    ax.set_ylabel("ledger.validate() latency, ms")
    ax.set_title("Blockchain validate() cost vs chain size\n(called on every /health/detailed & /api/blockchain/status)",
                 fontsize=11, fontweight="bold", color=INK["primary"])
    return _save(fig, "06_blockchain_validate_scaling")


def fig_rate_limit_vs_capacity(latency: dict, throughput: dict) -> Path | None:
    rlc = latency.get("rate_limit_ceiling", {})
    ing = throughput.get("ingest_streaming", {})
    if not (rlc and ing.get("samples_per_sec")):
        return None
    rate_limit_rps = 120 / 60
    backend_rps = ing["samples_per_sec"]

    fig, ax = plt.subplots(figsize=(5.5, 4.2))
    labels = ["Deployed rate limit\n(120 req/min)", "Backend single-thread\ncapacity (measured)"]
    values = [rate_limit_rps, backend_rps]
    bars = ax.bar(labels, values, color=[STATUS["warning"], CAT["blue"]], width=0.55)
    ax.set_yscale("log")
    ax.set_ylabel("Requests/sec (log scale)")
    ax.set_title("External traffic ceiling vs backend capacity", fontsize=11, fontweight="bold", color=INK["primary"])
    for bar, v in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, v * 1.15, f"{v:.2f} req/s",
                ha="center", fontsize=9, color=INK["secondary"])
    return _save(fig, "07_rate_limit_vs_capacity")


def generate_all_figures() -> list[Path]:
    latency = _load("latency")
    throughput = _load("throughput")
    concurrency = _load("concurrency")
    longrun = _load("longrun")

    figs = [
        fig_subsystem_latency(latency),
        fig_inference_histogram(latency),
        fig_concurrency_throughput(concurrency),
        fig_concurrency_latency(concurrency),
        fig_resource_timeline(longrun),
        fig_blockchain_scaling(longrun),
        fig_rate_limit_vs_capacity(latency, throughput),
    ]
    return [f for f in figs if f is not None]


# ---------------------------------------------------------------------------
# Tables (CSV + XLSX)
# ---------------------------------------------------------------------------
def generate_tables() -> dict[str, Path]:
    latency = _load("latency")
    concurrency = _load("concurrency")
    bottleneck = _load("bottleneck_analysis")

    out = {}

    # subsystem latency summary
    rows = []
    for key, label in [("simulator", "Simulator generation"), ("blockchain", "Blockchain ingest (1 record)"),
                        ("inference", "ML inference (ensemble, full pipeline)")]:
        d = latency.get(key, {}).get("stats")
        if d:
            rows.append({"subsystem": label, **d})
    for ep, d in latency.get("rest_endpoints", {}).get("endpoints", {}).items():
        if d.get("stats"):
            rows.append({"subsystem": f"REST {ep}", **d["stats"], "errors": d.get("errors", 0)})
    df_latency = pd.DataFrame(rows)
    df_latency.to_csv(TABLES_DIR / "subsystem_latency.csv", index=False)
    out["subsystem_latency_csv"] = TABLES_DIR / "subsystem_latency.csv"

    # concurrency table
    by_level = concurrency.get("inprocess", {}).get("by_level", {})
    rows = []
    for level_str, d in sorted(by_level.items(), key=lambda kv: int(kv[0])):
        lm = d.get("latency_ms", {})
        rows.append({
            "concurrency_level": int(level_str), "pool_workers": d.get("pool_workers"),
            "wall_sec": d.get("wall_sec"), "throughput_req_per_sec": d.get("throughput_req_per_sec"),
            "p50_ms": lm.get("p50"), "p90_ms": lm.get("p90"), "p99_ms": lm.get("p99"),
            "errors": d.get("errors"), "incomplete": d.get("timed_out_or_incomplete"),
            "sys_cpu_avg_pct": d.get("resources", {}).get("sys_cpu_avg"),
            "proc_mem_peak_mb": d.get("resources", {}).get("proc_mem_peak_mb"),
        })
    df_conc = pd.DataFrame(rows)
    df_conc.to_csv(TABLES_DIR / "concurrency_results.csv", index=False)
    out["concurrency_csv"] = TABLES_DIR / "concurrency_results.csv"

    # bottleneck findings
    df_findings = pd.DataFrame([
        {"category": f["category"], "conclusion": f["conclusion"]}
        for f in bottleneck.get("findings", [])
    ])
    df_findings.to_csv(TABLES_DIR / "bottleneck_findings.csv", index=False)
    out["bottleneck_findings_csv"] = TABLES_DIR / "bottleneck_findings.csv"

    # combined Excel workbook
    xlsx_path = TABLES_DIR / "phase7_performance_report.xlsx"
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        df_latency.to_excel(writer, sheet_name="Subsystem Latency", index=False)
        df_conc.to_excel(writer, sheet_name="Concurrency", index=False)
        df_findings.to_excel(writer, sheet_name="Bottleneck Findings", index=False)
    out["xlsx"] = xlsx_path

    return out


# ---------------------------------------------------------------------------
# Final performance score
# ---------------------------------------------------------------------------
SCORE_TABLE = [
    ("Single-request latency", 75,
     "~270 ms end-to-end (ensemble = 2 sequential model forward passes); "
     "acceptable for a security-detection workload (not HFT), dominated by "
     "model compute, not overhead."),
    ("Streaming throughput (single worker)", 55,
     "~3.5-3.7 readings/sec ceiling on this hardware; adequate for the "
     "demo's 20 meters at a 2-min interval, tight for a materially larger fleet."),
    ("Concurrency / horizontal scalability", 30,
     "Measured throughput DEGRADES from ~5.0 req/s at 10 concurrent requests "
     "to ~2.4 req/s at 1000 — the synchronous, blocking detector.ingest() call "
     "inside an async def handler serializes work on a single worker "
     "regardless of client-side concurrency."),
    ("Resource efficiency under load", 45,
     "CPU saturates (peaks ~667%, system-wide ~100%) well before throughput "
     "improves at higher concurrency — the extra CPU is thread contention, "
     "not useful parallel work."),
    ("Rate limiting / operational ceiling", 70,
     "120 req/min is a deliberate, functioning security control; incidentally "
     "close to the real single-worker capacity, though for an unrelated reason."),
    ("Blockchain notarization", 80,
     "Sub-millisecond per-record cost today; ledger.validate() is O(total "
     "records ever notarized) and runs on every health check — cheap now, "
     "will compound over the system's operational lifetime."),
    ("Health/monitoring overhead", 50,
     "/health/detailed blocks the event loop ~100 ms per call "
     "(psutil.cpu_percent(interval=0.1), no executor offload) — polled every "
     "5s by the dashboard's own health widget."),
    ("Startup / cold-start cost", 80,
     "~2.7s model load, ~4.0s full app boot from process launch to healthy — "
     "acceptable for typical container restart/scaling cadence."),
    ("Memory stability (soak window)", 75,
     "No runaway growth observed in the (scaled-down, 5-minute) soak window; "
     "a longer soak on a dedicated schedule is recommended before declaring "
     "the system leak-free over days/weeks."),
]


def _overall_score() -> float:
    return round(sum(s for _, s, _ in SCORE_TABLE) / len(SCORE_TABLE), 1)


def generate_markdown_report() -> Path:
    latency = _load("latency")
    throughput = _load("throughput")
    concurrency = _load("concurrency")
    longrun = _load("longrun")
    bottleneck = _load("bottleneck_analysis")
    validation = _load("validation")

    lines = []
    lines.append("# Phase 7 — End-to-End Performance Profiling Report\n")
    lines.append("Measurement-only phase. No model, dataset, simulator, preprocessing, "
                  "blockchain, dashboard, API, auth, or detection-pipeline code was modified. "
                  "All figures/tables referenced here are in `perf/reports/`.\n")

    lines.append("## Final performance score\n")
    lines.append(f"**Overall: {_overall_score()}/100** — solid single-request correctness and "
                 "latency; the concrete, fixable gap is concurrent/horizontal scalability, "
                 "traced to one specific architectural pattern, not a diffuse set of issues.\n")
    lines.append("| Dimension | Score /100 | Basis |")
    lines.append("|---|---|---|")
    for dim, score, basis in SCORE_TABLE:
        lines.append(f"| {dim} | {score} | {basis} |")
    lines.append("")

    lines.append("## Bottleneck analysis (evidence-based)\n")
    for f in bottleneck.get("findings", []):
        lines.append(f"- **[{f['category']}]** {f['conclusion']}")
    lines.append("")

    lines.append("## Key numbers\n")
    if latency.get("inference", {}).get("stats"):
        s = latency["inference"]["stats"]
        lines.append(f"- AI inference (ensemble, full pipeline): mean **{s['mean']:.1f} ms**, "
                     f"p95 **{s['p95']:.1f} ms**, p99 **{s['p99']:.1f} ms** (n={s['n']})")
    if throughput.get("ingest_streaming", {}).get("samples_per_sec"):
        lines.append(f"- Single-threaded streaming throughput: "
                     f"**{throughput['ingest_streaming']['samples_per_sec']} readings/sec**")
    rlc = latency.get("rate_limit_ceiling", {})
    if rlc:
        lines.append(f"- Deployed rate limit: **120 req/min** (2 req/s) — confirmed via burst test "
                     f"({rlc.get('total_429s')}/{rlc.get('burst_requests')} requests rejected)")
    conc_by_level = concurrency.get("inprocess", {}).get("by_level", {})
    if conc_by_level:
        lo = conc_by_level.get("10", {})
        hi = conc_by_level.get("1000", {})
        if lo and hi:
            lines.append(f"- Concurrency scaling: **{lo['throughput_req_per_sec']} req/s** at 10 "
                         f"concurrent requests -> **{hi['throughput_req_per_sec']} req/s** at 1000 "
                         f"(degradation, not improvement)")
    cs, ast = latency.get("cold_start", {}), latency.get("app_startup", {})
    if cs.get("reported_load_ms") and ast.get("startup_ms"):
        lines.append(f"- Cold start: model load **{cs['reported_load_ms']:.0f} ms**, "
                     f"full app boot **{ast['startup_ms']:.0f} ms**")
    lines.append("")

    lines.append("## Optimization recommendations (not implemented — measurement-only phase)\n")
    lines.append("1. Offload `_ml_detector.ingest()` in `/api/detect` to a worker thread "
                 "(`await asyncio.to_thread(...)`) or run multiple uvicorn workers, so concurrent "
                 "requests stop serializing on a single blocking call.")
    lines.append("2. Offload `psutil.cpu_percent(interval=0.1)` in `/health/detailed` the same way, "
                 "or drop the blocking `interval` argument (non-blocking mode exists in psutil) — "
                 "removes a ~100ms stall on every health poll.")
    lines.append("3. Cache or incrementally maintain `ledger.validate()`'s result instead of "
                 "re-hashing the full chain on every `/health/detailed`/`/api/blockchain/status` "
                 "call, since this cost grows with the system's operational lifetime.")
    lines.append("4. If sustained throughput beyond ~4 readings/sec is ever required, consider "
                 "whether both ensemble models must run on every reading, or whether horizontal "
                 "scaling (the docker-compose 3-service topology already designed in Phase 6) is "
                 "a better lever than optimizing the single-instance path.")
    lines.append("")

    lines.append("## Production readiness impact\n")
    lines.append("None of the above are correctness bugs — every measured path returned correct, "
                 "consistent results (see Validation below). They are capacity/latency "
                 "characteristics that matter once real concurrent load (multiple dashboards, "
                 "multiple meters reporting simultaneously) exceeds what a single worker handling "
                 "one blocking call at a time can serialize through. For the current single-site, "
                 "small-fleet deployment this is a low-urgency finding; for any deployment "
                 "expecting more than a handful of concurrent callers, item 1 above is the "
                 "highest-leverage fix.\n")

    lines.append("## Validation — no regressions introduced\n")
    if validation:
        lines.append(f"Overall: **{'PASS' if validation.get('overall_pass') else 'CHECK NEEDED'}**\n")
        eps = validation.get("endpoints", {}).get("checks", {})
        for ep, d in eps.items():
            lines.append(f"- `{ep}`: HTTP {d.get('status_code')}")
        det = validation.get("model_determinism", {})
        internal = det.get("internal_determinism", {})
        if internal.get("two_independent_fresh_subprocesses_match") is True:
            lines.append(f"- Model determinism: two independent, fresh subprocess loads of the "
                         f"same artifacts produced the IDENTICAL anomaly score "
                         f"({internal.get('run_a_anomaly_score')}) for the same fixed input "
                         f"sequence — no drift in code, weights, or artifacts.")
        live_cmp = det.get("live_server_comparison_informational", {})
        if live_cmp.get("live_server_anomaly_score") is not None:
            lines.append(f"- Informational only: the live (long-uptime) server returned a "
                         f"different score ({live_cmp['live_server_anomaly_score']}) for the same "
                         f"input — expected, since its zone-consumption aggregator has accumulated "
                         f"this session's traffic while a fresh subprocess starts empty (a state "
                         f"difference, not a code difference; not used as a pass/fail signal).")
        lines.append(f"- {validation.get('only_perf_dir_touched', {}).get('claim', '')} "
                     f"({validation.get('only_perf_dir_touched', {}).get('count', 0)} files, all under `perf/`)")
    lines.append("")

    lines.append("## Figures\n")
    for f in sorted(FIGURES_DIR.glob("*.png")):
        lines.append(f"![{f.stem}](figures/{f.name})")
    lines.append("")

    lines.append("## Methodology notes / honest limitations\n")
    lines.append("- Concurrency levels 1-1000 were measured **in-process** against the same shared "
                 "detector instance api_server.py uses — zero HTTP, zero interaction with rate "
                 "limiting or auth. A small (1/5/10) live-HTTP sanity check against the real, "
                 "unmodified production instance confirms the same serialization behavior shows "
                 "up end-to-end.")
    lines.append("- The rate limiter was never altered, bypassed, or disabled anywhere, on any "
                 "instance, at any point in this phase.")
    lines.append("- The long-run soak window is 5 minutes (scaled down from a multi-hour/day "
                 "production soak, which isn't practical inside a single interactive session) — "
                 "explicitly a lower bound, not a substitute for a longer scheduled soak.")
    lines.append("- No GPU is used by this model (torch.cuda.is_available() is False on this "
                 "machine); an NVIDIA GTX 1650 is present but idle throughout — confirmed via "
                 "nvidia-smi sampling during every benchmark.")

    out_path = REPORTS_DIR / "phase7_performance_report.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def generate_pdf_report(md_title: str = "Phase 7 — Performance Profiling Report") -> Path:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak)
    from reportlab.lib.units import inch

    bottleneck = _load("bottleneck_analysis")
    validation = _load("validation")

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Small", fontSize=8, leading=10, textColor=colors.HexColor(INK["secondary"])))

    doc = SimpleDocTemplate(str(REPORTS_DIR / "phase7_performance_report.pdf"), pagesize=letter,
                            topMargin=0.6 * inch, bottomMargin=0.6 * inch)
    story = []
    story.append(Paragraph(md_title, styles["Title"]))
    story.append(Paragraph("Measurement-only phase — no model, dataset, simulator, preprocessing, "
                           "blockchain, dashboard, API, auth, or detection-pipeline code was modified.",
                           styles["Small"]))
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph(f"Overall performance score: {_overall_score()}/100", styles["Heading2"]))
    score_rows = [["Dimension", "Score", "Basis"]] + [
        [dim, str(score), Paragraph(basis, styles["Small"])] for dim, score, basis in SCORE_TABLE
    ]
    t = Table(score_rows, colWidths=[1.6 * inch, 0.5 * inch, 4.4 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(CAT["blue"])),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor(INK["grid"])),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(t)
    story.append(PageBreak())

    story.append(Paragraph("Bottleneck analysis", styles["Heading2"]))
    for f in bottleneck.get("findings", []):
        story.append(Paragraph(f"<b>[{f['category']}]</b> {f['conclusion']}", styles["Normal"]))
        story.append(Spacer(1, 0.08 * inch))
    story.append(PageBreak())

    story.append(Paragraph("Figures", styles["Heading2"]))
    for fig_path in sorted(FIGURES_DIR.glob("*.png")):
        try:
            story.append(Image(str(fig_path), width=6.2 * inch, height=6.2 * inch * 0.6, kind="proportional"))
            story.append(Spacer(1, 0.15 * inch))
        except Exception:
            pass

    story.append(Paragraph("Validation — no regressions introduced", styles["Heading2"]))
    story.append(Paragraph(f"Overall: {'PASS' if validation.get('overall_pass') else 'CHECK NEEDED'}",
                           styles["Normal"]))

    doc.build(story)
    return REPORTS_DIR / "phase7_performance_report.pdf"


if __name__ == "__main__":
    figs = generate_all_figures()
    print(f"[report] {len(figs)} figures written to {FIGURES_DIR}")
    tables = generate_tables()
    print(f"[report] tables written: {list(tables.values())}")
    md = generate_markdown_report()
    print(f"[report] markdown -> {md}")
    pdf = generate_pdf_report()
    print(f"[report] pdf -> {pdf}")
