# Release Notes — v1.0.0-thesis

**Note on this release**: this document describes the intended content of
a `v1.0.0-thesis` release. Per this repository's current state (see
"Repository state" below), no git tag or commit has actually been created
by this phase — that action is left to the user, since this repository
carries substantial pre-existing uncommitted history unrelated to this
project's work.

## Summary

This release freezes the Smart Grid Cybersecurity Detection Platform for
thesis submission. It represents the completion of 9 sequential phases:
scientific validation (data-leakage correction, benchmarking, ablation,
robustness, calibration, real-data validation), production hardening,
performance profiling, full thesis/defense/publication documentation, and
a final engineering-correction pass that fixed a critical, previously-
undetected cryptographic vulnerability alongside two measured performance
bottlenecks.

## Highlights

- **A real security vulnerability, found and fixed within the project's
  own review process.** The Phase 8 final review (conducted as an
  IEEE-reviewer-style critique of the completed system) identified that
  the blockchain ledger's authority signing keys were derivable from
  public information. Phase 8.5 replaced them with real Ed25519 keypairs
  and verified the fix closes the exact attack found.
- **Two measured performance bottlenecks, fixed and re-verified.**
  Concurrent request serialization (root cause: a blocking call in an
  async handler) and a blocking health-check call are both fixed;
  the fix for concurrency is proven via the collapse of the min/max
  latency spread at 5 concurrent requests from 4.98× (serialized) to
  1.02× (parallel).
- **Zero regressions.** 96/96 tests passing across production and all 5
  scientific-phase test suites, plus live smoke-testing of the running
  server after every change.
- **A complete thesis package**: 20 chapters (French), defense material,
  an IEEE-format publication package (English), a GitHub-ready README/
  guides, 17 architecture/UML diagrams, and this release's own 4
  structured correction reports plus final release report.

## What this release does NOT include

- A mobile application, Solidity smart contracts, or Firebase
  integration — the PFE subject's third pillar, explicitly out of scope
  across every phase and disclosed as such throughout (thesis Chapter 18).
- A build-verified Docker deployment — documented and ready to execute,
  not fabricated (`production/docs/docker_validation.md`).
- A retrained production model under the leak-free protocol — the
  currently deployed model artifacts predate that fix; retraining is
  flagged as the highest-priority follow-up (thesis Chapter 19.2) but was
  out of scope for this phase ("Do NOT retrain any model").

## Upgrade / migration notes

If you have an existing deployment using the pre-Phase-8.5 blockchain
code: the new signing scheme is **not backward-compatible** with blocks
signed under the old (insecure) scheme — this is expected and correct,
since the old scheme provided no real security to preserve. A fresh
genesis block will be created on first start with the new code. See
`production/docs/key_rotation_and_recovery.md`.

## Repository state (as found, not altered by this phase)

This repository has substantial pre-existing uncommitted state (106
changed paths at last check via `git status`), predominantly historical
file deletions unrelated to this project's work, plus this project's own
untracked `production/`, `perf/`, and `thesis_package/` directories. This
phase did not run any `git add`/`commit`/`tag` command — generating
release-facing files (this document, `CHANGELOG.md`) is a safe, reversible
action; altering shared git history is not, and is left to the user's
explicit decision given the scope of pre-existing changes that are not
this phase's to resolve unilaterally.

**Suggested next step, for the user to decide and execute**: review
`git status`, decide what (if anything) from the pre-existing changes
should be committed or discarded, then commit this project's own new
work and tag it `v1.0.0-thesis` if desired.
