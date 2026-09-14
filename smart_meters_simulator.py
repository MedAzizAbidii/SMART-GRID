"""
smart_meters_simulator.py
=========================
Simulates 50 Algerian smart meters, injects realistic attacks,
signs every reading through the PoA blockchain, then saves:

  data/raw/donnees_smart_meters_<date>.csv          — all readings (raw format)
  data/normal/donnees_normal_<date>.csv             — normal-only (clean training)
  data/blockchain/chain_<date>.json                 — full PoA chain
  data/blockchain/blocks/                           — individual block JSON files
  data/blockchain_verified/donnees_verified_<date>.csv — raw + block_hash / proposer

Usage:
    .\\venv64\\Scripts\\python.exe .\\smart_meters_simulator.py
    .\\venv64\\Scripts\\python.exe .\\smart_meters_simulator.py --days 7 --attack-rate 0.02
    .\\venv64\\Scripts\\python.exe .\\smart_meters_simulator.py --days 1 --interval 5 --no-blockchain

Arguments:
    --days INT            Days of data to generate        (default: 7)
    --start YYYY-MM-DD    Simulation start date           (default: today)
    --interval INT        Sampling interval in minutes    (default: 2)
    --attack-rate FLOAT   Fraction of readings = attack   (default: 0.015 = 1.5%)
    --meters INT          Number of smart meters          (default: 50)
    --block-size INT      Rows per blockchain block       (default: 100)
    --seed INT            RNG seed for reproducibility    (default: 42)
    --no-blockchain       Skip blockchain (fast mode)
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import signal
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# ── Locate the smartgrid_simulation package ───────────────────────────────────
_ROOT = Path(__file__).resolve().parent
_SIM  = _ROOT / "smartgrid_simulation"
if str(_SIM) not in sys.path:
    sys.path.insert(0, str(_SIM))

from blockchain.poa_ledger import (
    ProofOfAuthorityLedger, AuthorityNode, _sha256_text, _canonical_json,
)

# ── Output directories ────────────────────────────────────────────────────────
DATA_DIR        = _ROOT / "data"
RAW_DIR         = DATA_DIR / "raw"
NORMAL_DIR      = DATA_DIR / "normal"
CHAIN_DIR       = DATA_DIR / "blockchain"
VERIFIED_DIR    = DATA_DIR / "blockchain_verified"
STREAM_DIR      = DATA_DIR / "stream"

for d in (RAW_DIR, NORMAL_DIR, CHAIN_DIR, VERIFIED_DIR, STREAM_DIR):
    d.mkdir(parents=True, exist_ok=True)

# ── Grid constants (matches reference donnees_smart_meters.csv) ───────────────
NOMINAL_V     = 230.0   # volts (nominal — data spreads ~218-241 V)
NOMINAL_HZ    = 60.0    # Hz    (nominal — data spreads ~59.7-60.3 Hz)
METER_NOISE_V = 6.0     # PT metering spread (V)
METER_NOISE_A = 0.09    # CT noise (A)

# ── Meter topology (fixed, reproducible) ─────────────────────────────────────
# Zones cycle A,B,C,D by meter index (SM_0001->A, SM_0002->B, ...), exactly as
# in the reference dataset.
_ZONE_LETTERS = ["A", "B", "C", "D"]
_ZONE_OF = {i: _ZONE_LETTERS[(i - 1) % 4] for i in range(1, 51)}

# Consumer type — 3 classes only (residentiel / commercial / industriel), to
# match the reference data and the trained model's feature set.
_TYPE_SEED = np.random.default_rng(2025)
_CTYPE: dict[int, str] = {}
for _i in range(1, 51):
    _r = _TYPE_SEED.random()
    if   _r < 0.55: _CTYPE[_i] = "residentiel"
    elif _r < 0.80: _CTYPE[_i] = "commercial"
    else:           _CTYPE[_i] = "industriel"

# Base load ranges per type: (min_kw, max_kw, peak_multiplier) — calibrated so
# evening magnitudes match the reference (resid ~1-5, comm ~4-8, indus ~15-22).
_BASE_RANGE = {
    "residentiel": (0.5,  2.2,  2.5),
    "commercial":  (2.5,  5.0,  1.8),
    "industriel": (12.0, 17.0,  1.3),
}
_BASE_KW = {
    i: float(_TYPE_SEED.uniform(*_BASE_RANGE[_CTYPE[i]][:2]))
    for i in range(1, 51)
}

# Attack labels — French, matching the reference dataset. Fraud/theft classes
# (the project's `fraude energetique` focus) are kept separate so --fraud-share
# can boost them.
CYBER_TYPES = ["Surcharge", "Tension hors norme", "Pic soudain"]
FRAUD_TYPES = ["Fraude", "Consommation nulle suspecte"]
ATTACK_TYPES = CYBER_TYPES + FRAUD_TYPES

# Output column order — matches the reference donnees_smart_meters.csv exactly.
RAW_COLS = [
    "timestamp", "meter_id", "zone", "type",
    "consommation_kw", "tension_v", "courant_a",
    "power_factor", "frequency_hz",
    "statut", "anomalies",
]


def _backup_once(path: Path) -> None:
    """Back up an existing file once (never overwrite an existing backup)."""
    if path.exists():
        backup = path.with_name(path.stem + "_ORIGINAL_backup" + path.suffix)
        if not backup.exists():
            import shutil
            shutil.copy2(path, backup)
            print(f"    [backup] existing {path.name} -> {backup.name}")


# ─────────────────────────────────────────────────────────────────────────────
# Physics helpers
# ─────────────────────────────────────────────────────────────────────────────

def _temp(month: int, hour: float) -> float:
    """Outdoor temperature — northern Algeria climate model."""
    means = [12, 13, 16, 19, 23, 28, 33, 33, 28, 22, 17, 13]
    amps  = [ 7,  7,  8,  9, 10, 12, 13, 13, 11,  9,  8,  7]
    m, a  = means[month - 1], amps[month - 1]
    daily = a * np.sin(np.pi * (hour - 5) / 10) if 5 <= hour <= 15 else \
            -a * 0.3 * np.sin(np.pi * (hour - 15) / 14)
    return float(m + daily + np.random.normal(0, 0.8))


def _solar_factor(hour: float, month: int) -> float:
    """Solar generation factor 0-1 for Algeria (high irradiance)."""
    rise = 7.5 - 0.5 * np.sin(2 * np.pi * (month - 3) / 12)
    set_ = 17.5 + 2.5 * np.sin(2 * np.pi * (month - 3) / 12)
    if hour < rise or hour >= set_:
        return 0.0
    cloud = np.random.beta(2, 8)   # Algeria: mostly sunny
    peak  = float(max(0.0, np.sin(np.pi * (hour - rise) / (set_ - rise))))
    return float(peak * (1 - cloud) * (0.92 + 0.08 * np.random.random()))


def _is_ramadan(ts: datetime) -> bool:
    y, m, d = ts.year, ts.month, ts.day
    if y == 2024 and ((m == 3 and d >= 11) or (m == 4 and d <= 9)):  return True
    if y == 2025 and  m == 3 and 1 <= d <= 30:                        return True
    if y == 2026 and ((m == 2 and d >= 18) or (m == 3 and d <= 19)): return True
    return False


def _load_factor(hour: float, ctype: str, weekday: bool,
                 friday: bool, ramadan: bool, month: int) -> float:
    """
    Dimensionless load multiplier 0-1 reflecting Algerian consumption patterns.
    Each consumer type has its own daily shape calibrated against Sonelgaz data.
    """
    h = hour

    # Hospital: near-flat, slight daytime increase
    if ctype == "hopital":
        return float(0.85 + 0.15 * (1.0 if 6 <= h <= 22 else 0.0))

    # Mosque: peaks at the 5 daily prayer times + Ramadan boost
    if ctype == "mosquee":
        prayers = [5.0, 12.0, 15.25, 18.5, 21.0]
        f = 0.05
        for p in prayers:
            f += 0.8 * max(0.0, 1.0 - abs(h - p) / 0.75)
        if ramadan:
            f += 0.3 * max(0.0, 1.0 - abs(h - 3.5) / 1.0)   # Suhoor
            f += 0.4 * max(0.0, 1.0 - abs(h - 19.0) / 1.5)  # Iftar
        return float(np.clip(f, 0.02, 1.0))

    # Residential
    if ctype == "residentiel":
        if ramadan:
            if 9 <= h <= 16:    f = 0.12   # daytime sleep
            elif 18 <= h <= 22: f = 0.85 + 0.15 * max(0.0, np.sin(np.pi * (h-18)/4))
            elif 2 <= h <= 4:   f = 0.50   # Suhoor meal
            elif 0 <= h <= 2:   f = 0.65   # late socialising
            else:               f = 0.25
        else:
            if 5 <= h <= 9:     f = 0.40 + 0.50 * np.sin(np.pi * (h-5)/4)
            elif 9 <= h <= 12:  f = 0.45
            elif 12 <= h <= 14: f = 0.55   # lunch at home (Mediterranean habit)
            elif 14 <= h <= 17: f = 0.35   # siesta / low activity
            elif 17 <= h <= 22: f = 0.55 + 0.45 * np.sin(np.pi * (h-17)/5)
            elif 22 <= h:       f = 0.40 - 0.20 * (h-22) / 2.0
            else:               f = 0.20   # 0-5h night floor
        # Summer AC dominance: June-September
        if month in (6, 7, 8, 9):
            temp = _temp(month, h)
            ac_boost = 0.35 * max(0.0, (temp - 26.0) / 12.0)
            f = float(f + ac_boost)
        return float(np.clip(f, 0.10, 1.0))

    # Commercial
    if ctype == "commercial":
        if friday:
            if 12 <= h <= 14:   f = 0.20   # Jumu'a prayer — close for lunch
            elif 7 <= h <= 12:  f = 0.70
            elif 14 <= h <= 17: f = 0.45
            else:               f = 0.07
        elif weekday:
            if 8 <= h <= 12:    f = 0.80 + 0.20 * (h-8)/4
            elif 12 <= h <= 14: f = 0.65
            elif 14 <= h <= 18: f = 0.85
            elif 18 <= h <= 21: f = 0.50
            else:               f = 0.07
        else:
            f = 0.45 if 9 <= h <= 18 else 0.06
        if ramadan and 14 <= h <= 18:
            f = max(f, 0.70)   # shops stay open near Iftar
        if month in (6, 7, 8):
            f += 0.20          # AC/refrigeration summer boost
        return float(np.clip(f, 0.05, 1.0))

    # Industrial: 3-shift operation
    if ctype == "industriel":
        if not weekday:
            return float(0.45 + 0.10 * np.random.random())
        f = 0.88 if (6 <= h < 22) else 0.55
        return float(f + np.random.normal(0, 0.03))

    return 0.5


def _voltage(base_v: float, load_frac: float, ctype: str,
             rng: np.random.Generator | None = None) -> float:
    """Voltage around nominal: small load-dependent sag + wide metering spread."""
    r = rng if rng is not None else np.random
    z = {"residentiel": 0.35, "commercial": 0.28,
         "industriel":  0.20}.get(ctype, 0.30)
    drop  = z * load_frac * 8.0
    noise = float(r.normal(0, METER_NOISE_V))
    return float(np.clip(base_v - drop + noise, 210.0, 245.0))


def _power_factor(ctype: str, load_frac: float,
                  rng: np.random.Generator | None = None) -> float:
    r = rng if rng is not None else np.random
    base = 0.905
    if load_frac < 0.15:
        base -= 0.03
    return float(np.clip(base + float(r.normal(0, 0.022)), 0.85, 0.95))


def _frequency(load_frac: float, rng: np.random.Generator | None = None) -> float:
    """Grid frequency around nominal: tiny sag under load + measurement noise."""
    r = rng if rng is not None else np.random
    val = NOMINAL_HZ - 0.08 * load_frac + float(r.normal(0, 0.15))
    return float(np.clip(val, 59.5, 60.5))


# ─────────────────────────────────────────────────────────────────────────────
# Attack injector
# ─────────────────────────────────────────────────────────────────────────────

def _inject(attack_type: str, row: dict, rng: np.random.Generator) -> dict:
    """
    Modify a reading to simulate an attack.
    Each attack type has a distinct electrical signature that the ML model
    should learn to recognise.
    """
    r = dict(row)
    label = attack_type   # value written to the 'anomalies' column

    if attack_type == "Surcharge":
        # Overload: consumption + current spike, slight voltage sag, freq droop.
        sc = float(rng.uniform(1.6, 2.6))
        r["consommation_kw"] = round(row["consommation_kw"] * sc, 3)
        r["courant_a"]       = round(row["courant_a"] * sc, 3)
        r["tension_v"]       = round(row["tension_v"] - float(rng.uniform(3, 10)), 2)
        r["frequency_hz"]    = round(row["frequency_hz"] - float(rng.uniform(0.10, 0.35)), 2)

    elif attack_type == "Tension hors norme":
        # Voltage out of tolerance: deep sag OR over-voltage spike.
        if rng.random() < 0.5:
            r["tension_v"] = round(float(rng.uniform(185, 205)), 2)   # sag
        else:
            r["tension_v"] = round(float(rng.uniform(248, 265)), 2)   # spike
        r["courant_a"]     = round((row["consommation_kw"] * 1000.0) / max(r["tension_v"], 1.0), 3)

    elif attack_type == "Pic soudain":
        # Sudden brief spike in load and current.
        sc = float(rng.uniform(2.0, 4.0))
        r["consommation_kw"] = round(row["consommation_kw"] * sc, 3)
        r["courant_a"]       = round(row["courant_a"] * sc, 3)
        r["frequency_hz"]    = round(row["frequency_hz"] - float(rng.uniform(0.05, 0.25)), 2)

    elif attack_type == "Consommation nulle suspecte":
        # Suspicious zero — meter forced to ~0 during a real load window (theft).
        r["consommation_kw"] = round(float(rng.uniform(0.0, 0.12)), 3)
        r["courant_a"]       = round(float(rng.uniform(0.0, 0.6)), 3)
        r["power_factor"]    = round(float(rng.uniform(0.50, 0.75)), 3)

    elif attack_type == "Fraude":
        # ── Energy theft (fraude energetique) — UNDER-reporting ───────────────
        # The meter records far less than the real consumption so the customer
        # is under-billed. Tell: reads well below zone peers + inconsistent P/V/I.
        keep = float(rng.uniform(0.20, 0.55))       # only 20-55% recorded
        r["consommation_kw"] = round(row["consommation_kw"] * keep, 3)
        r["courant_a"]       = round(row["courant_a"] * float(rng.uniform(0.20, 0.55)), 3)
        r["power_factor"]    = round(float(rng.uniform(0.55, 0.80)), 3)

    r["statut"]    = "ALERTE"
    r["anomalies"] = label
    return r


# ─────────────────────────────────────────────────────────────────────────────
# Attack scheduler: burst pattern (realistic — not random per row)
# ─────────────────────────────────────────────────────────────────────────────

def _schedule_attacks(
    timestamps: list[datetime],
    meter_ids: list[str],
    attack_rate: float,
    rng: np.random.Generator,
    fraud_share: float = 0.25,
) -> dict[tuple[datetime, str], str]:
    """
    Return dict mapping (timestamp, meter_id) → attack_type.

    Attacks arrive in bursts on a single meter, the way real incidents behave:
      - Cyber/physical (Surcharge, Tension hors norme, Pic soudain): short
        bursts of 3-15 readings.
      - Energy fraud/theft (Fraude, Consommation nulle suspecte): long
        persistent windows, because a tampered meter keeps under-reporting
        until an inspection catches it.

    `fraud_share` is the fraction of attack EVENTS that are energy fraud, so a
    security team focused on `fraude énergétique` can generate fraud-heavy data
    (e.g. --fraud-share 0.6) without losing the other attack classes.
    """
    total    = len(timestamps) * len(meter_ids)
    target   = int(total * attack_rate)
    events: dict[tuple[datetime, str], str] = {}
    placed   = 0

    while placed < target:
        mid       = meter_ids[int(rng.integers(0, len(meter_ids)))]
        start_idx = int(rng.integers(0, len(timestamps)))

        if rng.random() < fraud_share:
            atype = FRAUD_TYPES[int(rng.integers(0, len(FRAUD_TYPES)))]
            burst = int(rng.integers(20, 80))   # persistent theft window
        else:
            atype = CYBER_TYPES[int(rng.integers(0, len(CYBER_TYPES)))]
            burst = int(rng.integers(3, 16))    # short incident

        for offset in range(burst):
            idx = start_idx + offset
            if idx >= len(timestamps):
                break
            key = (timestamps[idx], mid)
            if key not in events:
                events[key] = atype
                placed += 1

    return events


# ─────────────────────────────────────────────────────────────────────────────
# Row generator
# ─────────────────────────────────────────────────────────────────────────────

def _make_row(
    mid_idx: int,
    ts: datetime,
    rng: np.random.Generator,
) -> dict:
    """
    Generate one raw meter reading in the exact donnees_smart_meters.csv format.
    """
    ctype   = _CTYPE[mid_idx]
    base_kw = _BASE_KW[mid_idx]
    month   = ts.month
    hour    = ts.hour + ts.minute / 60.0
    weekday = ts.weekday()
    friday  = (weekday == 4)
    is_wd   = (weekday < 5)
    ramadan = _is_ramadan(ts)

    # Load factor with per-meter behavioural jitter
    lf = _load_factor(hour, ctype, is_wd, friday, ramadan, month)
    lf = float(np.clip(lf + float(rng.normal(0, 0.04)), 0.05, 1.0))

    # Gross consumption
    _, _, peak_mult = _BASE_RANGE[ctype]
    consumption = max(0.05, base_kw * lf * peak_mult)
    consumption += float(rng.normal(0, consumption * 0.03))
    consumption = round(consumption, 3)

    # Voltage
    tension_v = round(_voltage(NOMINAL_V, lf, ctype, rng), 2)

    # Current (I = P/V, as in the reference data)
    courant_a = (consumption * 1000.0) / max(tension_v, 1.0)
    courant_a += float(rng.normal(0, METER_NOISE_A))
    courant_a = round(max(0.0, courant_a), 3)

    # Power factor + grid frequency
    power_factor = round(_power_factor(ctype, lf, rng), 3)
    frequency_hz = round(_frequency(lf, rng), 2)

    zone = _ZONE_OF[mid_idx]

    return {
        "timestamp":       ts.strftime("%Y-%m-%d %H:%M:%S"),
        "meter_id":        f"SM_{mid_idx:04d}",
        "zone":            f"Zone {zone}",
        "type":            ctype,
        "consommation_kw": consumption,
        "tension_v":       tension_v,
        "courant_a":       courant_a,
        "power_factor":    power_factor,
        "frequency_hz":    frequency_hz,
        "statut":          "NORMAL",
        "anomalies":       "",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main simulator
# ─────────────────────────────────────────────────────────────────────────────

class SmartMeterSimulator:
    """
    Runs the full simulation pipeline:
      generate readings → inject attacks → anchor to blockchain → save CSVs
    """

    def __init__(
        self,
        n_meters: int = 50,
        attack_rate: float = 0.015,
        interval_minutes: int = 2,
        block_size: int = 100,
        seed: int = 42,
        use_blockchain: bool = True,
        fraud_share: float = 0.25,
    ):
        self.n_meters      = n_meters
        self.attack_rate   = attack_rate
        self.interval_min  = interval_minutes
        self.block_size    = block_size
        self.use_blockchain = use_blockchain
        self.fraud_share   = fraud_share
        self.rng           = np.random.default_rng(seed)
        self.meter_ids     = [f"SM_{i:04d}" for i in range(1, n_meters + 1)]
        self.meter_indices = list(range(1, n_meters + 1))

    # ------------------------------------------------------------------
    def run(self, start: datetime, end: datetime) -> dict[str, Path]:
        """
        Full simulation run. Returns dict of saved file paths.
        """
        date_tag  = start.strftime("%Y%m%d")
        n_steps   = int((end - start).total_seconds() / (self.interval_min * 60))
        timestamps = [start + timedelta(minutes=i * self.interval_min)
                      for i in range(n_steps)]

        print(f"  Meters        : {self.n_meters}")
        print(f"  Timesteps     : {n_steps:,}  ({self.interval_min}-min intervals)")
        print(f"  Total readings: {n_steps * self.n_meters:,}")
        print(f"  Attack rate   : {self.attack_rate*100:.1f}%")
        print(f"  Fraud share   : {self.fraud_share*100:.0f}% of attacks (fraude energetique)")
        print(f"  Blockchain    : {'YES' if self.use_blockchain else 'NO (fast mode)'}")
        print()

        # Pre-schedule attacks (burst pattern, realistic)
        attack_events = _schedule_attacks(
            timestamps, self.meter_ids, self.attack_rate, self.rng,
            fraud_share=self.fraud_share,
        )

        # Generate all readings
        print("  [1/3] Generating readings ...", flush=True)
        all_rows: list[dict] = []
        n_attack = 0

        for step, ts in enumerate(timestamps):
            ts_rows: list[dict] = []
            for idx in self.meter_indices:
                row = _make_row(idx, ts, self.rng)
                mid = f"SM_{idx:04d}"
                atk = attack_events.get((ts, mid))
                if atk:
                    row = _inject(atk, row, self.rng)
                    n_attack += 1
                ts_rows.append(row)

            all_rows.extend(ts_rows)

            # Simple console progress (every 10%)
            if (step + 1) % max(1, n_steps // 10) == 0:
                pct = (step + 1) / n_steps * 100
                bar = "#" * int(pct // 5) + "." * (20 - int(pct // 5))
                print(f"\r    [{bar}] {pct:.0f}%", end="", flush=True)

        print(f"\r    [####################] 100%  — {len(all_rows):,} readings generated")

        total     = len(all_rows)
        pct_atk   = 100.0 * n_attack / total if total > 0 else 0
        print(f"    Attacks: {n_attack:,} ({pct_atk:.2f}%)")

        saved: dict[str, Path] = {}

        # ------------------------------------------------------------------
        # Save raw CSV (all readings) — canonical donnees_smart_meters.csv
        print("\n  [2/3] Saving CSVs ...", flush=True)
        df_all = pd.DataFrame(all_rows)[RAW_COLS]

        raw_path = RAW_DIR / "donnees_smart_meters.csv"
        _backup_once(raw_path)                      # protect any pre-existing file
        df_all.to_csv(raw_path, index=False, encoding="utf-8")
        saved["raw"] = raw_path
        print(f"    Raw CSV     : {raw_path}")

        # Normal-only CSV (clean data for unsupervised/pretrain phase)
        df_normal   = df_all[df_all["statut"] == "NORMAL"].copy()
        normal_path = NORMAL_DIR / "donnees_normal.csv"
        df_normal.to_csv(normal_path, index=False, encoding="utf-8")
        saved["normal"] = normal_path
        print(f"    Normal CSV  : {normal_path}  ({len(df_normal):,} rows)")

        # ------------------------------------------------------------------
        # Blockchain anchoring
        if self.use_blockchain:
            print("\n  [3/3] Anchoring to PoA blockchain ...", flush=True)
            verified_path = self._anchor_to_blockchain(
                raw_path, date_tag, all_rows
            )
            saved["verified"] = verified_path
            print(f"    Verified CSV: {verified_path}")
        else:
            print("\n  [3/3] Blockchain skipped (--no-blockchain).")

        return saved

    # ------------------------------------------------------------------
    def run_stream(
        self,
        start: datetime,
        tick_seconds: float = 2.0,
        flush_every: int = 20,
        append_main: bool = False,
    ) -> None:
        """
        CONTINUOUS collection mode — runs forever until Ctrl+C.

        Every `tick_seconds` real seconds it emits one timestep of readings for
        all meters (advancing the simulated clock by `--interval` minutes),
        appends them to a growing CSV, and — once a full block_size of rows has
        accumulated — seals a PoA blockchain block live.

        append_main=True  -> keep appending to data/raw/donnees_smart_meters.csv
                             (the main dataset grows live; header kept if present).
        append_main=False -> fresh timestamped files under data/stream/.
        """
        date_tag = start.strftime("%Y%m%d_%H%M%S")
        if append_main:
            raw_path      = RAW_DIR / "donnees_smart_meters.csv"
            verified_path = VERIFIED_DIR / "donnees_verified.csv"
            chain_path    = CHAIN_DIR / "chain_live.json"
        else:
            raw_path      = STREAM_DIR / f"donnees_stream_{date_tag}.csv"
            verified_path = STREAM_DIR / f"donnees_stream_{date_tag}_verified.csv"
            chain_path    = STREAM_DIR / f"chain_{date_tag}.json"

        VER_COLS = RAW_COLS + ["row_index", "row_hash", "block_index",
                               "block_hash", "proposer"]

        # Live blockchain ledger (kept in memory, appended incrementally)
        ledger = ProofOfAuthorityLedger(
            block_size=self.block_size, source_file=raw_path.name
        ) if self.use_blockchain else None

        # Stateful attack manager: meter_id -> [attack_type, remaining_ticks]
        active: dict[str, list] = {}
        # Per-tick probability of a meter STARTING a new attack burst, tuned so
        # the long-run attack rate matches self.attack_rate.
        p_start = self.attack_rate / 8.0

        print(f"  Meters       : {self.n_meters}")
        print(f"  Cadence      : 1 batch / {tick_seconds:g}s real  "
              f"(sim step = {self.interval_min} min)")
        print(f"  Attack rate  : ~{self.attack_rate*100:.1f}%  "
              f"(fraud share {self.fraud_share*100:.0f}%)")
        print(f"  Blockchain   : {'live sealing' if ledger else 'OFF'}")
        print(f"  Raw file     : {raw_path}")
        if ledger:
            print(f"  Verified file: {verified_path}")
        print("\n  Press Ctrl+C to stop.\n")
        print(f"  {'time':<19} {'meter':<8} {'type':<11} "
              f"{'kW':>7} {'V':>8} {'A':>8}  status")
        print("  " + "-" * 74)

        # Graceful shutdown flag
        self._stop = False
        def _handle(sig, frm):
            self._stop = True
        signal.signal(signal.SIGINT, _handle)

        # Append to an existing main file, or create fresh with a header.
        existing_rows = 0
        raw_is_new = not (append_main and raw_path.exists())
        if not raw_is_new:
            with raw_path.open("r", encoding="utf-8") as _fh:
                existing_rows = max(0, sum(1 for _ in _fh) - 1)   # minus header
        raw_fh = raw_path.open("a" if not raw_is_new else "w", newline="", encoding="utf-8")
        raw_w  = csv.DictWriter(raw_fh, fieldnames=RAW_COLS)
        if raw_is_new:
            raw_w.writeheader()

        ver_fh = ver_w = None
        if ledger:
            ver_is_new = not (append_main and verified_path.exists())
            ver_fh = verified_path.open("a" if not ver_is_new else "w", newline="", encoding="utf-8")
            ver_w  = csv.DictWriter(ver_fh, fieldnames=VER_COLS)
            if ver_is_new:
                ver_w.writeheader()

        if existing_rows:
            print(f"  Appending to existing file ({existing_rows:,} rows already present)\n")

        sim_ts = start
        row_index = existing_rows
        total_rows = 0
        total_attacks = 0
        pending: list[dict] = []            # rows awaiting block sealing
        blocks_sealed = 0

        try:
            while not self._stop:
                ts_rows: list[dict] = []
                for idx in self.meter_indices:
                    row = _make_row(idx, sim_ts, self.rng)
                    mid = f"SM_{idx:04d}"

                    # ── stateful attack injection ────────────────────────────
                    if mid in active:
                        atype, remaining = active[mid]
                        row = _inject(atype, row, self.rng)
                        total_attacks += 1
                        remaining -= 1
                        if remaining <= 0:
                            del active[mid]
                        else:
                            active[mid] = [atype, remaining]
                    elif self.rng.random() < p_start:
                        if self.rng.random() < self.fraud_share:
                            atype = FRAUD_TYPES[int(self.rng.integers(0, len(FRAUD_TYPES)))]
                            burst = int(self.rng.integers(20, 80))
                        else:
                            atype = CYBER_TYPES[int(self.rng.integers(0, len(CYBER_TYPES)))]
                            burst = int(self.rng.integers(3, 16))
                        row = _inject(atype, row, self.rng)
                        total_attacks += 1
                        active[mid] = [atype, burst - 1]

                    ts_rows.append(row)

                # Write + PERSIST + display each reading immediately, one by one,
                # so the CSV on disk grows in real time (an external viewer sees
                # every row the instant it is produced).
                for r in ts_rows:
                    raw_w.writerow({k: r.get(k, "") for k in RAW_COLS})
                    raw_fh.flush()              # push to disk immediately
                    row_index += 1
                    if ledger is not None:
                        rec = {"row_index": row_index,
                               **{k: ("" if r.get(k) is None else str(r.get(k)))
                                  for k in RAW_COLS}}
                        rec["row_hash"] = _sha256_text(_canonical_json(rec))
                        pending.append(rec)

                    # live line for this reading
                    is_atk = r["statut"] == "ALERTE"
                    flag = f"** {r['anomalies']}" if is_atk else "OK"
                    print(f"  {r['timestamp']:<19} {r['meter_id']:<8} "
                          f"{r['type']:<11} {r['consommation_kw']:>7.2f} "
                          f"{r['tension_v']:>8.2f} {r['courant_a']:>8.2f}  {flag}",
                          flush=True)
                total_rows += len(ts_rows)

                # seal full blocks
                while ledger is not None and len(pending) >= self.block_size:
                    batch, pending = pending[:self.block_size], pending[self.block_size:]
                    ledger.ingest_records(batch)
                    block = ledger.chain[-1]
                    blocks_sealed += 1
                    raw_lookup = {r["meter_id"] + "|" + r["timestamp"]: r for r in ts_rows}
                    for txn in batch:
                        base = {k: txn.get(k, "") for k in RAW_COLS}
                        ver_w.writerow({**base,
                            "row_index": txn["row_index"], "row_hash": txn["row_hash"],
                            "block_index": block.index, "block_hash": block.block_hash,
                            "proposer": block.proposer})
                    ver_fh.flush()

                # periodic status line + chain checkpoint
                if (total_rows // self.n_meters) % flush_every == 0:
                    if ledger is not None:
                        ledger.save(chain_path)
                    print(f"  ... collected {total_rows:,} readings | "
                          f"attacks {total_attacks:,} | blocks {blocks_sealed} "
                          f"| active {len(active)}")

                sim_ts += timedelta(minutes=self.interval_min)
                # sleep in short slices so Ctrl+C is responsive
                slept = 0.0
                while slept < tick_seconds and not self._stop:
                    time.sleep(min(0.2, tick_seconds - slept))
                    slept += 0.2

        finally:
            raw_fh.close()
            if ledger is not None:
                ledger.save(chain_path)
                ver_fh.close()
            print("\n  " + "=" * 60)
            print("  STREAM STOPPED — collected data saved")
            print("  " + "=" * 60)
            print(f"  Readings : {total_rows:,}  (attacks {total_attacks:,})")
            if ledger is not None:
                valid, _ = ledger.validate()
                print(f"  Blocks   : {blocks_sealed}  (chain valid: {'YES' if valid else 'NO'})")
            print(f"  Raw CSV  : {raw_path}")
            if ledger is not None:
                print(f"  Verified : {verified_path}")
                print(f"  Chain    : {chain_path}")
            print("  " + "=" * 60)

    # ------------------------------------------------------------------
    def _anchor_to_blockchain(
        self,
        raw_csv_path: Path,
        date_tag: str,
        all_rows: list[dict],
    ) -> Path:
        """
        Build the PoA chain from the raw CSV, save chain files,
        then produce a blockchain_verified CSV that links each row
        to its block_hash + proposer.
        """
        chain_dir  = CHAIN_DIR / f"chain_{date_tag}"
        blocks_dir = chain_dir / "blocks"
        chain_dir.mkdir(parents=True, exist_ok=True)
        blocks_dir.mkdir(parents=True, exist_ok=True)

        # Build ledger
        ledger = ProofOfAuthorityLedger.from_csv(
            csv_path=raw_csv_path,
            block_size=self.block_size,
        )

        # Validate
        valid, errors = ledger.validate()
        if valid:
            print(f"    Chain valid  : YES  ({len(ledger.chain)} blocks)")
        else:
            print(f"    Chain INVALID: {errors[:3]}")

        # Save full chain JSON + individual block files
        chain_json  = chain_dir / f"chain_{date_tag}.json"
        ledger.save(chain_json, block_dir=blocks_dir)
        print(f"    Chain JSON  : {chain_json}")
        print(f"    Block files : {blocks_dir}  ({len(ledger.chain)} files)")

        summary = ledger.summary()
        print(f"    Blocks      : {summary['total_blocks']}  "
              f"(alerts={summary['total_alerts']:,}  "
              f"normals={summary['total_normals']:,})")

        # Build row → block mapping (row_index is 1-based, same as CSV row number)
        row_to_block: dict[int, dict] = {}
        for block in ledger.chain[1:]:   # skip genesis
            for txn in block.transactions:
                row_idx = int(txn.get("row_index", 0))
                row_to_block[row_idx] = {
                    "block_index":  block.index,
                    "block_hash":   block.block_hash,
                    "proposer":     block.proposer,
                    "row_hash":     txn.get("row_hash", ""),
                }

        # Produce blockchain_verified CSV
        verified_rows = []
        for i, row in enumerate(all_rows, start=1):
            binfo = row_to_block.get(i, {
                "block_index": -1, "block_hash": "",
                "proposer": "", "row_hash": "",
            })
            verified_rows.append({**row, **binfo})

        verified_path = VERIFIED_DIR / f"donnees_verified_{date_tag}.csv"
        pd.DataFrame(verified_rows).to_csv(verified_path, index=False, encoding="utf-8")

        # Save a human-readable summary
        summary_path = chain_dir / "summary.json"
        with open(summary_path, "w", encoding="utf-8") as fh:
            json.dump({**summary, "date_tag": date_tag,
                       "verified_csv": str(verified_path)}, fh, indent=2)

        return verified_path


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Algerian Smart Grid Simulator — generates + signs meter data"
    )
    p.add_argument("--days",          type=int,   default=7)
    p.add_argument("--start",         type=str,   default=None,
                   help="Start date YYYY-MM-DD (default: today)")
    p.add_argument("--interval",      type=int,   default=2,
                   help="Sampling interval in minutes (default: 2)")
    p.add_argument("--attack-rate",   type=float, default=0.015,
                   help="Fraction of readings that are attacks (default: 0.015)")
    p.add_argument("--fraud-share",   type=float, default=0.25,
                   help="Fraction of attacks that are energy fraud/theft (default: 0.25). "
                        "Raise (e.g. 0.6) to generate fraud-focused datasets.")
    p.add_argument("--meters",        type=int,   default=50)
    p.add_argument("--block-size",    type=int,   default=100,
                   help="Rows per blockchain block (default: 100)")
    p.add_argument("--seed",          type=int,   default=42)
    p.add_argument("--no-blockchain", action="store_true",
                   help="Skip blockchain anchoring (fast mode)")
    p.add_argument("--stream",        action="store_true",
                   help="Continuous collection: run forever (Ctrl+C to stop), "
                        "appending readings and sealing blockchain blocks live.")
    p.add_argument("--tick",          type=float, default=2.0,
                   help="Stream mode: real seconds between batches (default: 2.0)")
    p.add_argument("--append-main",   action="store_true",
                   help="Stream mode: keep appending to the main "
                        "data/raw/donnees_smart_meters.csv (it grows live).")
    return p.parse_args()


def main():
    args = _parse_args()

    if args.start:
        start_dt = datetime.strptime(args.start, "%Y-%m-%d")
    elif args.stream:
        start_dt = datetime.now().replace(microsecond=0)   # real wall clock
    else:
        start_dt = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    sim = SmartMeterSimulator(
        n_meters     = args.meters,
        attack_rate  = args.attack_rate,
        interval_minutes = args.interval,
        block_size   = args.block_size,
        seed         = args.seed,
        use_blockchain = not args.no_blockchain,
        fraud_share  = args.fraud_share,
    )

    # ── Continuous "no-stop" collection mode ─────────────────────────────────
    if args.stream:
        print("=" * 60)
        print("  Smart Meters Simulator — CONTINUOUS COLLECTION")
        print("=" * 60)
        print(f"  Started : {start_dt.strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        sim.run_stream(start_dt, tick_seconds=args.tick, append_main=args.append_main)
        return

    end_dt = start_dt + timedelta(days=args.days)

    print("=" * 60)
    print("  Smart Meters Simulator — Algerian Grid (Sonelgaz)")
    print("=" * 60)
    print(f"  Period : {start_dt.strftime('%Y-%m-%d')} -> {end_dt.strftime('%Y-%m-%d')}  ({args.days} day(s))")
    print()

    saved = sim.run(start_dt, end_dt)

    print("\n" + "=" * 60)
    print("  DONE — output files")
    print("=" * 60)
    for label, path in saved.items():
        size_kb = os.path.getsize(path) / 1024
        print(f"  [{label:<10}] {path.name}  ({size_kb:,.0f} KB)")
    print()
    print("  To use this data for ML training:")
    print(f"    Normal data  -> {saved.get('normal', 'N/A')}")
    print(f"    Labeled data -> {saved.get('raw', 'N/A')}")
    if "verified" in saved:
        print(f"    Blockchain   -> {saved['verified']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
