# Final Project Statistics — v1.0.0-thesis

All counts below were generated directly from the repository at freeze
time (commands shown for reproducibility), not estimated.

## Code

| Metric | Count | Command |
|---|---|---|
| Lines of Python code | **21,560** | `find . -name "*.py" -not -path "./.venv/*" -not -path "*/__pycache__/*" \| xargs wc -l` |
| Python files/modules | **128** | same, `wc -l` of file list |
| Top-level packages/phases | **27** directories (`ablation, benchmark, blockchain, calibration, components, dashboard, data_generation, docs, frontend, investigation, ml_pipeline, perf, production, realdata, robustness, scripts, simulation, thesis_package, ...`) | `ls -d */` |

**Note on the 21,560-line figure**: this counts every `.py` file in the
repository, including historical/exploratory scripts predating the
phase-based scientific structure (e.g., root-level analysis scripts from
early project iterations, some of which show as deleted in the current
uncommitted `git status` — see the release notes). The figure is reported
as-is rather than hand-filtered, to avoid an arbitrary "which files count"
judgment call.

## Tests

| Metric | Count |
|---|---|
| Production test suite | 46 tests (`production/tests/`) |
| Benchmark phase tests | 9 |
| Ablation phase tests | 8 |
| Robustness phase tests | 14 |
| Calibration phase tests | 11 |
| Real-data phase tests | 8 |
| **Total unit tests** | **96** |
| Production code coverage | 90% (documented, `production/README.md`) |
| Test pass rate at freeze | **96/96 (100%)** |

## Models

| Item | Count/detail |
|---|---|
| Production ensemble (deployed) | 2 models: `outputs/early_stopping_final` (precision-optimized, "v3"), `outputs/test_run_now` (recall-optimized, "v2") |
| Architecture families benchmarked | 3 (unsupervised-distance, unsupervised-reconstruction, supervised) across 7 named models (Chapter 11) |
| Total trained-model artifact directories under `outputs/` | 19 (includes scenario-test variants, generalization-test models, and historical experiment snapshots alongside the 2 production models) |
| Ablation configurations trained | 38 (Chapter 12) |

## Experiments & results

| Phase | Result JSON files |
|---|---|
| Benchmark | 2 |
| Ablation | 76 (38 configs × per-experiment artifacts) |
| Investigation | 1 |
| Robustness | 61 |
| Calibration | 6 |
| Real-data (SGCC) | 9 |
| Performance profiling (Phase 7 + 8.5 reprofile) | 8 |
| **Total** | **163** |

## Figures, tables, and reports

| Artifact type | Count |
|---|---|
| Figures (`.png`) across the whole repository | **209** |
| Tables (`.csv`/`.xlsx`, excluding raw `data/`) | **80** |
| Markdown reports/docs across the whole repository | **98** |
| — of which, thesis package documentation pages | **37** (20 thesis chapters + 5 defense docs + 2 publication docs + 1 review + 1 verified-facts ledger + 4 Phase 8.5 correction reports + this statistics file + the release report + release notes) |
| Architecture diagrams (Graphviz, rendered PNG) | 11 |
| UML diagrams (Graphviz, rendered PNG) | 6 |
| **Total diagrams** | **17** |

## Documentation

| Document set | Page/file count |
|---|---|
| Production operational docs (`production/docs/`) | 11 (9 from Phase 6 + `docker_validation.md` + `key_rotation_and_recovery.md`, both new in Phase 8.5) |
| Thesis chapters | 20 |
| Defense material files | 5 |
| Publication package files | 2 |
| Final review | 1 |
| Phase 8.5 correction reports + release documents | 7 (4 corrections + final release report + release notes + this file) |
| GitHub package files | 4 |

## Scientific phases completed

9 sequential phases: Phase 0 (data-leakage fix) → Phase 1 (benchmark) →
Phase 2/2.5 (ablation + investigation) → Phase 3/4 (robustness +
calibration) → Phase 5 (real-data validation) → Phase 6 (production
hardening) → Phase 7 (performance profiling) → Phase 8 (thesis/defense/
publication package + final review) → Phase 8.5 (this release).
