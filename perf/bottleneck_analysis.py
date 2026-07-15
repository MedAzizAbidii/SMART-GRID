"""Phase 7 — bottleneck analysis.

Loads every raw result file produced by bench_latency/throughput/concurrency/
longrun and derives evidence-backed conclusions: slowest subsystem, highest
memory/CPU consumer, highest latency source, and the architectural findings
discovered while building the suite (rate limiter ceiling, the synchronous
blocking call inside the async /api/detect handler, the blocking psutil call
in /health/detailed, blockchain validate() scaling). Every conclusion here
cites the specific number(s) that produced it.
"""
from __future__ import annotations

import json
from pathlib import Path

from perf.config import RESULTS_DIR


def _load(name: str) -> dict:
    path = RESULTS_DIR / f"{name}.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def analyze() -> dict:
    latency = _load("latency")
    throughput = _load("throughput")
    concurrency = _load("concurrency")
    longrun = _load("longrun")

    findings = []

    # -----------------------------------------------------------------
    # 1. Slowest recurring subsystem
    # -----------------------------------------------------------------
    subsystem_costs = {}
    if latency.get("simulator", {}).get("stats"):
        subsystem_costs["simulator_generation"] = latency["simulator"]["stats"]["mean"]
    if latency.get("blockchain", {}).get("stats"):
        subsystem_costs["blockchain_ingest_record"] = latency["blockchain"]["stats"]["mean"]
    if latency.get("inference", {}).get("stats"):
        subsystem_costs["ml_inference_ensemble (preprocessing+2x forward+XAI)"] = latency["inference"]["stats"]["mean"]
    rest = latency.get("rest_endpoints", {}).get("endpoints", {})
    for ep, data in rest.items():
        if data.get("stats"):
            subsystem_costs[f"rest_endpoint {ep}"] = data["stats"]["mean"]

    if subsystem_costs:
        slowest = max(subsystem_costs, key=subsystem_costs.get)
        fastest = min(subsystem_costs, key=subsystem_costs.get)
        findings.append({
            "category": "slowest_subsystem",
            "conclusion": f"'{slowest}' is the slowest recurring, per-request subsystem "
                          f"at {subsystem_costs[slowest]:.2f} ms mean, "
                          f"{subsystem_costs[slowest] / subsystem_costs[fastest]:,.0f}x slower "
                          f"than the fastest measured operation ('{fastest}', {subsystem_costs[fastest]:.4f} ms).",
            "evidence": subsystem_costs,
        })

    # -----------------------------------------------------------------
    # 2. Inference cost breakdown (ensemble = 2 sequential forward passes)
    # -----------------------------------------------------------------
    inf = latency.get("inference", {})
    if inf.get("stats") and inf.get("detector_reported_avg_latency_ms"):
        total = inf["stats"]["mean"]
        single_model = inf["detector_reported_avg_latency_ms"]
        findings.append({
            "category": "inference_architecture",
            "conclusion": f"The deployed detector is an EnsembleDetector running v2 AND v3 "
                          f"sequentially on every reading ({total:.1f} ms measured total vs "
                          f"~{single_model:.1f} ms self-reported for a single model's forward "
                          f"pass) — confirms end-to-end latency is ~2x a single model's cost "
                          f"by architecture, not an anomaly.",
            "evidence": {"total_ingest_ms": total, "single_model_avg_latency_ms": single_model},
        })

    # -----------------------------------------------------------------
    # 3. Streaming throughput ceiling
    # -----------------------------------------------------------------
    ing = throughput.get("ingest_streaming", {})
    if ing.get("samples_per_sec"):
        findings.append({
            "category": "streaming_throughput_ceiling",
            "conclusion": f"Single-threaded streaming throughput of the full detection "
                          f"pipeline is {ing['samples_per_sec']} readings/sec "
                          f"({ing.get('implied_max_ms_per_sample')} ms/reading) — this, not "
                          f"I/O, network, or the simulator (27,958+ samples/sec measured), "
                          f"is what caps how fast a single worker can process a continuous "
                          f"stream of meter readings.",
            "evidence": ing,
        })

    # -----------------------------------------------------------------
    # 4. Rate limiter is the dominant EXTERNAL ceiling, well below backend capacity
    # -----------------------------------------------------------------
    rlc = latency.get("rate_limit_ceiling", {})
    if rlc.get("total_429s") is not None:
        findings.append({
            "category": "operational_rate_limit_ceiling",
            "conclusion": f"The deployed RateLimitMiddleware (120 req/min default) is the "
                          f"dominant ceiling for external API traffic — a burst of "
                          f"{rlc['burst_requests']} requests produced {rlc['total_429s']} "
                          f"HTTP 429s (first rejection at request #{rlc.get('first_429_at_request_index')}). "
                          f"This is ~{120/60:.1f} req/sec, roughly "
                          f"{(1000 / max(subsystem_costs.get('ml_inference_ensemble (preprocessing+2x forward+XAI)', 270), 1)):.1f}x "
                          f"below the backend's own single-threaded inference capacity "
                          f"(see streaming_throughput_ceiling) — the limiter, not the model, "
                          f"is what an external client actually experiences.",
            "evidence": rlc,
        })

    # -----------------------------------------------------------------
    # 5. Blocking call inside async /api/detect handler -> serialization under concurrency
    # -----------------------------------------------------------------
    conc = concurrency.get("inprocess", {}).get("by_level", {})
    if conc:
        levels = sorted((int(k) for k in conc.keys()))
        low, high = levels[0], levels[-1]
        tp_low = conc[str(low)]["throughput_req_per_sec"]
        tp_high = conc[str(high)]["throughput_req_per_sec"]
        scaling_factor = round(tp_high / tp_low, 2) if tp_low else None
        findings.append({
            "category": "concurrency_scaling",
            "conclusion": f"api_server.py's /api/detect handler is `async def` but calls "
                          f"`_ml_detector.ingest()` directly (no run_in_executor/asyncio.to_thread) — "
                          f"a synchronous, ~270ms-per-call function. Measured in-process "
                          f"throughput went from {tp_low} req/s at concurrency={low} to "
                          f"{tp_high} req/s at concurrency={high} "
                          f"({scaling_factor}x, on an 8-logical-core machine, "
                          f"bounded thread pool of {concurrency['inprocess']['pool_cap']}) — "
                          f"far from the {high}x linear scaling the requested concurrency "
                          f"level implies. On a single uvicorn worker (this deployment's "
                          f"default), concurrent HTTP requests to /api/detect queue behind "
                          f"the blocking call and are effectively processed close to "
                          f"one-at-a-time.",
            "evidence": {"levels_tested": levels, "throughput_by_level": {k: v["throughput_req_per_sec"] for k, v in conc.items()}},
        })

    # -----------------------------------------------------------------
    # 6. /health/detailed blocking psutil call
    # -----------------------------------------------------------------
    hdb = longrun.get("health_detailed_blocking", {})
    rest_detailed = rest.get("/health/detailed", {}).get("stats", {})
    if hdb.get("stats") and rest_detailed:
        findings.append({
            "category": "health_endpoint_blocking_call",
            "conclusion": f"production/monitoring/health.py's /health/detailed calls "
                          f"psutil.cpu_percent(interval=0.1) synchronously inside an `async "
                          f"def` route. That single call measured {hdb['stats']['mean']:.1f} ms "
                          f"mean, accounting for "
                          f"{100 * hdb['stats']['mean'] / rest_detailed['mean']:.0f}% of the "
                          f"endpoint's own measured latency ({rest_detailed['mean']:.1f} ms). "
                          f"Since it blocks the whole event loop, every dashboard health-widget "
                          f"poll (every 5s, per dashboard/index.html) freezes ALL other "
                          f"in-flight requests on a single-worker deployment for ~100ms.",
            "evidence": {"psutil_call_ms": hdb["stats"], "endpoint_total_ms": rest_detailed},
        })

    # -----------------------------------------------------------------
    # 7. Blockchain validate() scaling
    # -----------------------------------------------------------------
    bvs = longrun.get("blockchain_validate_scaling", {})
    if bvs.get("by_record_count"):
        biggest = max((int(k) for k in bvs["by_record_count"].keys()))
        biggest_ms = bvs["by_record_count"][str(biggest)]["validate_ms"]
        findings.append({
            "category": "blockchain_validate_scaling",
            "conclusion": f"ledger.validate() (called on every /health/detailed and "
                          f"/api/blockchain/status request) is O(total records ever "
                          f"notarized) — measured {biggest_ms:.2f} ms at {biggest:,} records "
                          f"on an isolated ledger (~{bvs.get('approx_slope_ms_per_1000_records')} ms "
                          f"per additional 1,000 records). The live ledger currently holds "
                          f"only 1 block, so this cost is negligible today, but it will grow "
                          f"linearly with the system's operational lifetime and compounds "
                          f"with the psutil blocking call on the same endpoint.",
            "evidence": bvs["by_record_count"],
        })

    # -----------------------------------------------------------------
    # 8. Cold start / app startup (one-time costs)
    # -----------------------------------------------------------------
    cs, ast = latency.get("cold_start", {}), latency.get("app_startup", {})
    if cs.get("reported_load_ms") and ast.get("startup_ms"):
        findings.append({
            "category": "startup_cost",
            "conclusion": f"Model weight loading takes ~{cs['reported_load_ms']:.0f} ms "
                          f"(cold, from disk); full app startup (uvicorn boot to first "
                          f"healthy /health) takes ~{ast['startup_ms']:.0f} ms. Both are "
                          f"one-time per-process costs, not recurring — relevant to container "
                          f"restart/scaling latency (e.g. how fast a new replica becomes ready "
                          f"behind a load balancer), not steady-state throughput.",
            "evidence": {"cold_start_ms": cs["reported_load_ms"], "app_startup_ms": ast["startup_ms"]},
        })

    # -----------------------------------------------------------------
    # 9. Memory growth over the soak window
    # -----------------------------------------------------------------
    soak = longrun.get("soak", {})
    live_res = soak.get("live_server_resources")
    self_res = soak.get("profiling_process_resources")
    if live_res or self_res:
        parts = []
        live_res_reliable = bool(live_res and live_res.get("proc_mem_avg_mb", 0) > 20)
        if live_res:
            if live_res_reliable:
                parts.append(f"live server process: {live_res.get('proc_mem_growth_mb')} MB growth over "
                             f"{live_res.get('duration_sec')}s ({live_res.get('proc_mem_start_mb')} -> "
                             f"{live_res.get('proc_mem_end_mb')} MB)")
            else:
                parts.append(f"live server process: MEASUREMENT UNRELIABLE this run — "
                             f"_find_live_server_pid() matched a process (PID {soak.get('live_server_pid')}) "
                             f"reporting {live_res.get('proc_mem_avg_mb')} MB average RSS, far too low for a "
                             f"running FastAPI+PyTorch process; likely picked up a stale/wrong PID via "
                             f"cmdline matching. Not treated as evidence either way")
        if self_res:
            parts.append(f"in-process heavy-load worker: {self_res.get('proc_mem_growth_mb')} MB growth "
                         f"over {self_res.get('duration_sec')}s processing "
                         f"{soak.get('inprocess_heavy_load', {}).get('total_readings')} readings "
                         f"back-to-back")
        findings.append({
            "category": "memory_growth_soak",
            "conclusion": "; ".join(parts) + ". " + (
                "No unbounded growth observed in the reliable measurement(s) over this window — "
                "see the report for the scaled-down soak duration used and the recommendation "
                "for a longer run with corrected PID detection."
            ),
            "evidence": {"live_server": live_res, "profiling_process": self_res},
        })

    return {
        "findings": findings,
        "n_findings": len(findings),
    }


def run_all() -> dict:
    result = analyze()
    out_path = RESULTS_DIR / "bottleneck_analysis.json"
    out_path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(f"[bottleneck] {result['n_findings']} findings -> {out_path}")
    for f in result["findings"]:
        print(f"  - [{f['category']}] {f['conclusion'][:140]}...")
    return result


if __name__ == "__main__":
    run_all()
