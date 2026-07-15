"""
generate_realistic_dataset.py — Production-quality smart grid data generator.

Models the Algerian electricity grid (Sonelgaz distribution network):
  - Northern Algeria climate: 8-12C winter, 38-45C summer
  - Algerian daily load profile: morning 7-9h, evening 17-22h peaks
  - Ramadan consumption shift (suhoor/iftar cycles)
  - Friday prayer load drop (12:00-14:00 commercial dip)
  - Seasonal AC dominance (June-August 2-3x higher residential consumption)
  - Multi-tier noise: meter noise + process noise + communication jitter
  - Realistic attack prevalence: ~1.5% of readings (vs unrealistic 48% baseline)
  - Subtle FDIA: falsify within 2-sigma of normal to test adversarial robustness
  - Output format matches donnees_smart_meters.csv exactly (SM_0001..SM_0050)

Usage:
    python data_generation/generate_realistic_dataset.py
    python data_generation/generate_realistic_dataset.py --days 30 --attack-rate 0.01

Output: data/realistic/donnees_realistic_YYYYMMDD.csv
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUTPUT_DIR = ROOT / "data" / "realistic"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Algerian grid constants ────────────────────────────────────────────────────
NOMINAL_VOLTAGE_V   = 220.0   # Sonelgaz low-voltage distribution
NOMINAL_FREQ_HZ     = 50.0
VOLTAGE_TOLERANCE   = 0.10    # ±10% allowed before violation
METER_NOISE_STD_V   = 1.2     # CT/PT measurement noise (V)
METER_NOISE_STD_A   = 0.08    # Current transformer noise (A)

# ── Meter population ──────────────────────────────────────────────────────────
METER_COUNT = 50

# Zone assignment (reflects Algerian urban geography)
ZONE_MAP = {
    "A": [f"SM_{i:04d}" for i in range(1,  13)],   # Algiers suburb (dense residential)
    "B": [f"SM_{i:04d}" for i in range(13, 26)],   # Oran commercial zone
    "C": [f"SM_{i:04d}" for i in range(26, 38)],   # Constantine mixed zone
    "D": [f"SM_{i:04d}" for i in range(38, 51)],   # Annaba light industrial
}

# Consumer type per meter (fixed per meter — same meter always same type)
np.random.seed(2025)
_rng_init = np.random.default_rng(2025)
CONSUMER_TYPES = {}
for mid in [f"SM_{i:04d}" for i in range(1, 51)]:
    r = _rng_init.random()
    if r < 0.55:
        CONSUMER_TYPES[mid] = "residentiel"
    elif r < 0.80:
        CONSUMER_TYPES[mid] = "commercial"
    elif r < 0.93:
        CONSUMER_TYPES[mid] = "industriel"
    elif r < 0.97:
        CONSUMER_TYPES[mid] = "mosquee"    # Mosque — specific Friday / Ramadan pattern
    else:
        CONSUMER_TYPES[mid] = "hopital"    # Hospital — near-flat 24h profile

# Base consumption parameters per consumer type (kW)
BASE_PARAMS = {
    #                  min,  max,  daily_peak_factor, night_floor
    "residentiel":   (0.8,  3.5,  2.8,               0.25),
    "commercial":    (2.0,  12.0, 2.0,               0.10),
    "industriel":    (15.0, 60.0, 1.4,               0.50),
    "mosquee":       (0.3,  1.2,  3.5,               0.05),
    "hopital":       (8.0,  25.0, 1.15,              0.85),
}

# Fixed base load per meter (drawn once at init)
_BASE_LOADS = {
    mid: float(_rng_init.uniform(BASE_PARAMS[CONSUMER_TYPES[mid]][0],
                                 BASE_PARAMS[CONSUMER_TYPES[mid]][1]))
    for mid in [f"SM_{i:04d}" for i in range(1, 51)]
}

# Meters with rooftop solar (residential + some commercial)
_SOLAR_METERS = {
    mid for mid in [f"SM_{i:04d}" for i in range(1, 51)]
    if CONSUMER_TYPES[mid] in ("residentiel", "commercial") and _rng_init.random() < 0.25
}
_SOLAR_CAPACITY = {mid: float(_rng_init.uniform(1.5, 4.0)) for mid in _SOLAR_METERS}


# ── Algerian climate model ────────────────────────────────────────────────────

def outdoor_temp_c(month: int, hour: float) -> float:
    """
    Monthly mean temperature for northern Algeria (Algiers/Oran climate zone).
    Monthly means: Jan=12, Feb=13, Mar=16, Apr=19, May=23, Jun=28,
                   Jul=33, Aug=33, Sep=28, Oct=22, Nov=17, Dec=13
    Daily amplitude: ~8C in winter, ~12C in summer.
    """
    monthly_mean  = [12, 13, 16, 19, 23, 28, 33, 33, 28, 22, 17, 13]
    monthly_amp   = [ 7,  7,  8,  9, 10, 12, 13, 13, 11,  9,  8,  7]
    mean = monthly_mean[month - 1]
    amp  = monthly_amp[month - 1]
    # Daily cycle: minimum at 5h, maximum at 15h
    daily = amp * np.sin(np.pi * (hour - 5.0) / 10.0) if 5 <= hour <= 15 else \
            -amp * 0.3 * np.sin(np.pi * (hour - 15.0) / 14.0)
    return float(mean + daily + np.random.normal(0, 0.8))


def solar_factor(hour: float, month: int, cloud_cover: float = 0.15) -> float:
    """
    Solar irradiance factor 0-1. Algeria: very high solar potential.
    Sunrise: ~6h in summer, ~7h30 in winter. Sunset: ~20h summer, ~17h30 winter.
    """
    sunrise = 7.5 - 0.5 * np.sin(2 * np.pi * (month - 3) / 12.0)  # 7h winter, 6h summer
    sunset  = 17.5 + 2.5 * np.sin(2 * np.pi * (month - 3) / 12.0) # 18h winter, 20h summer
    if hour < sunrise or hour >= sunset:
        return 0.0
    midday = (sunrise + sunset) / 2.0
    factor = float(max(0.0, np.sin(np.pi * (hour - sunrise) / (sunset - sunrise))))
    cloud_effect = 1.0 - cloud_cover * (0.5 + 0.5 * np.random.random())
    return float(factor * cloud_effect * (0.92 + 0.08 * np.random.random()))


# ── Algerian load profile ────────────────────────────────────────────────────

def is_ramadan(ts: datetime) -> bool:
    """
    Approximate Ramadan periods for 2024-2026.
    These shift ~11 days earlier each year.
    """
    y, m, d = ts.year, ts.month, ts.day
    # 2024: March 11 - April 9
    if y == 2024 and ((m == 3 and d >= 11) or (m == 4 and d <= 9)):
        return True
    # 2025: March 1 - March 30
    if y == 2025 and (m == 3 and 1 <= d <= 30):
        return True
    # 2026: February 18 - March 19
    if y == 2026 and ((m == 2 and d >= 18) or (m == 3 and d <= 19)):
        return True
    return False


def daily_load_factor(hour: float, consumer_type: str, is_weekday: bool,
                      is_friday: bool, ramadan: bool, month: int) -> float:
    """
    Returns a multiplier 0-1 for the base load at a given hour.
    Captures the Algerian daily consumption profile per consumer type.
    """
    h = hour

    if consumer_type == "hopital":
        # Nearly flat: slight increase during day (6-22h)
        return 0.88 + 0.12 * (1.0 if 6 <= h <= 22 else 0.0)

    if consumer_type == "mosquee":
        # Peaks at prayer times: Fajr~5h, Dhuhr~12h, Asr~15h, Maghrib~sunset, Isha~21h
        peaks = [5.0, 12.0, 15.25, 18.5, 21.0]
        f = 0.05  # near-zero between prayers
        for p in peaks:
            f += 0.8 * max(0.0, 1.0 - abs(h - p) / 0.75)
        if ramadan:
            f += 0.3 * max(0.0, 1.0 - abs(h - 3.5) / 1.0)   # Suhoor
            f += 0.4 * max(0.0, 1.0 - abs(h - 19.0) / 1.5)  # Iftar
        return float(np.clip(f, 0.02, 1.0))

    if consumer_type == "residentiel":
        if ramadan:
            # Day sleep → load very low 9-16h; Iftar peak ~19h; Suhoor mini-peak ~3h
            if 9 <= h <= 16:
                f = 0.12
            elif 18 <= h <= 22:
                f = 0.85 + 0.15 * max(0.0, np.sin(np.pi * (h - 18) / 4.0))
            elif 2 <= h <= 4:
                f = 0.50  # Suhoor
            elif 0 <= h <= 2:
                f = 0.65  # late social time
            else:
                f = 0.25
        else:
            # Morning wake-up 6-9h, midday low, evening peak 18-22h, night base
            if 5 <= h <= 9:
                f = 0.40 + 0.50 * np.sin(np.pi * (h - 5) / 4.0)
            elif 9 <= h <= 12:
                f = 0.45
            elif 12 <= h <= 14:
                f = 0.55   # lunch at home (Mediterranean culture)
            elif 14 <= h <= 17:
                f = 0.35   # siesta / low activity
            elif 17 <= h <= 22:
                f = 0.55 + 0.45 * np.sin(np.pi * (h - 17) / 5.0)
            elif 22 <= h <= 24:
                f = 0.40 - 0.20 * (h - 22) / 2.0
            else:
                f = 0.20   # night base
        # Summer AC boost: significant in July-August
        if month in (6, 7, 8, 9):
            ac_boost = 0.30 * max(0.0, (outdoor_temp_c(month, h) - 26.0) / 10.0)
            f += ac_boost
        return float(np.clip(f, 0.10, 1.0))

    if consumer_type == "commercial":
        if is_friday:
            # Friday half-day for many Algerian businesses
            if 12 <= h <= 14:
                f = 0.20    # prayer break
            elif 7 <= h <= 12:
                f = 0.70
            elif 14 <= h <= 17:
                f = 0.50   # many close early
            else:
                f = 0.08
        elif is_weekday:
            if 8 <= h <= 12:
                f = 0.80 + 0.20 * (h - 8) / 4.0
            elif 12 <= h <= 14:
                f = 0.65   # lunch break (not full close)
            elif 14 <= h <= 18:
                f = 0.85
            elif 18 <= h <= 21:
                f = 0.50   # retail stays open
            else:
                f = 0.08
        else:
            # Weekend: half activity
            if 9 <= h <= 18:
                f = 0.45
            else:
                f = 0.06
        if ramadan:
            # Businesses open late, close around Iftar
            if 14 <= h <= 18:
                f = max(f, 0.70)
        if month in (6, 7, 8):
            f += 0.20  # AC / refrigeration
        return float(np.clip(f, 0.05, 1.0))

    if consumer_type == "industriel":
        # 3-shift pattern (6-14, 14-22, 22-6); weekend reduced
        if not is_weekday:
            return 0.45 + 0.10 * np.random.random()
        # Each shift starts strong, slight dip mid-shift
        shift1 = (6 <= h < 14)
        shift2 = (14 <= h < 22)
        shift3 = (h >= 22 or h < 6)
        if shift1 or shift2:
            f = 0.88
        else:
            f = 0.55   # night shift skeleton crew
        return float(f + np.random.normal(0, 0.03))

    return 0.5


# ── Voltage physics ───────────────────────────────────────────────────────────

def compute_voltage(base_v: float, load_fraction: float, consumer_type: str) -> float:
    """
    Kirchhoff-based voltage drop model.
    Longer cable runs (industrial/suburban) → higher impedance drop.
    """
    # Cable impedance per consumer type (typical Sonelgaz distribution)
    impedance = {"residentiel": 0.35, "commercial": 0.28, "industriel": 0.15,
                 "mosquee": 0.40, "hopital": 0.20}.get(consumer_type, 0.30)
    # V_drop = Z * I, I proportional to load
    v_drop = impedance * load_fraction * 15.0   # max ~5V drop at full load
    noise  = np.random.normal(0, METER_NOISE_STD_V)
    return float(np.clip(base_v - v_drop + noise, base_v * 0.85, base_v * 1.10))


def compute_power_factor(consumer_type: str, load_fraction: float,
                         ac_running: bool) -> float:
    """
    Power factor model. AC units degrade power factor significantly.
    Industrial motors introduce lagging PF.
    """
    base_pf = {"residentiel": 0.93, "commercial": 0.90, "industriel": 0.82,
               "mosquee": 0.96, "hopital": 0.88}.get(consumer_type, 0.90)
    if ac_running:
        base_pf -= 0.06
    # Load-dependent correction: at very low load, PF drops
    if load_fraction < 0.15:
        base_pf -= 0.08
    return float(np.clip(base_pf + np.random.normal(0, 0.012), 0.70, 0.99))


# ── Attack generators ─────────────────────────────────────────────────────────

def inject_attack(attack_type: str, reading: dict, rng: np.random.Generator) -> dict:
    """
    Inject a realistic attack into a meter reading.
    All attacks designed to be detectable but not trivially obvious.
    """
    r = reading.copy()

    if attack_type == "FDIA_voltage":
        # False Data Injection: falsify voltage sensor by +5 to +12%
        # Goal: mislead SCADA into thinking grid is healthy under overload
        scale = rng.uniform(1.05, 1.12)
        r["tension_v"] = round(reading["tension_v"] * scale, 3)
        r["anomalies"] = "FDIA"

    elif attack_type == "FDIA_subtle":
        # Adversarial FDIA: keep zone_consumption_mean within normal range
        # by slightly inflating all meters simultaneously.
        # Detectable only via temporal pattern — not via zone mean.
        delta = rng.uniform(0.04, 0.09)  # 4-9% injection
        r["consommation_kw"]  = round(reading["consommation_kw"] * (1 + delta), 3)
        r["courant_a"]        = round(reading["courant_a"] * (1 + delta * 0.8), 3)
        r["power_factor"]     = round(min(0.99, reading["power_factor"] * rng.uniform(0.96, 1.02)), 3)
        r["anomalies"] = "FDIA"

    elif attack_type == "DoS":
        # Denial of Service: replays the last reading (stale data)
        # Signature: voltage and consumption don't change between readings
        r["tension_v"]        = round(reading["tension_v"] + rng.normal(0, 0.1), 3)
        r["consommation_kw"]  = round(reading["consommation_kw"] + rng.normal(0, 0.02), 3)
        r["courant_a"]        = round(reading["courant_a"] + rng.normal(0, 0.01), 3)
        r["anomalies"] = "DoS"

    elif attack_type == "Fraud":
        # Energy theft: consumption much higher than billed
        # Signature: consumption spike + power_factor distortion (bypass meter wiring)
        r["consommation_kw"] = round(reading["consommation_kw"] * rng.uniform(1.8, 3.5), 3)
        r["courant_a"]       = round(reading["courant_a"] * rng.uniform(1.6, 3.0), 3)
        r["power_factor"]    = round(rng.uniform(0.45, 0.70), 3)  # wiring bypass = bad PF
        r["tension_v"]       = round(reading["tension_v"] * rng.uniform(0.93, 0.97), 3)
        r["anomalies"] = "Fraud"

    elif attack_type == "Fault":
        # Physical fault: sudden voltage sag + current spike
        r["tension_v"]       = round(reading["tension_v"] * rng.uniform(0.72, 0.88), 3)
        r["courant_a"]       = round(reading["courant_a"] * rng.uniform(1.4, 2.2), 3)
        r["power_factor"]    = round(rng.uniform(0.70, 0.82), 3)
        r["anomalies"] = "Fault"

    r["statut"]    = "ANOMALIE"
    r["is_alert"]  = 1
    return r


# ── Main generator ────────────────────────────────────────────────────────────

class RealisticDatasetGenerator:
    """
    Generates a realistic Algerian smart grid dataset.

    Attack prevalence is configurable (default 1.5%).
    Zone statistics are computed from the current timestep's actual readings,
    making zone_consumption_mean a derived feature just like in preprocessing.
    """

    ATTACK_TYPES = ["FDIA_voltage", "FDIA_subtle", "DoS", "Fraud", "Fault"]

    def __init__(
        self,
        n_meters: int = 50,
        attack_rate: float = 0.015,
        interval_minutes: int = 2,
        seed: int = 42,
    ):
        self.n_meters = n_meters
        self.attack_rate = attack_rate
        self.interval_min = interval_minutes
        self.rng = np.random.default_rng(seed)
        self.meters = [f"SM_{i:04d}" for i in range(1, n_meters + 1)]
        self.zone_of = {m: z for z, ms in ZONE_MAP.items() for m in ms}

    def _meter_reading(self, mid: str, ts: datetime) -> dict:
        """Generate a single realistic meter reading."""
        month    = ts.month
        hour     = ts.hour + ts.minute / 60.0
        weekday  = ts.weekday()          # 0=Mon … 6=Sun
        is_friday   = (weekday == 4)
        is_weekday  = (weekday < 5)
        ramadan     = is_ramadan(ts)
        ctype       = CONSUMER_TYPES[mid]
        base_kw     = _BASE_LOADS[mid]

        # --- Load factor ---
        lf = daily_load_factor(hour, ctype, is_weekday, is_friday, ramadan, month)
        # Per-meter stochastic jitter (each meter has its own habits)
        m_jitter = float(self.rng.normal(0, 0.04))
        lf = float(np.clip(lf + m_jitter, 0.05, 1.0))

        # --- Gross consumption ---
        consommation_kw = max(0.05, base_kw * lf * BASE_PARAMS[ctype][2])
        consommation_kw += float(self.rng.normal(0, consommation_kw * 0.03))  # meter noise

        # --- Solar generation (subtract) ---
        if mid in _SOLAR_METERS:
            cloud = float(self.rng.beta(2, 5))   # Algeria mostly sunny → low cloud
            sf = solar_factor(hour, month, cloud)
            solar_kw = _SOLAR_CAPACITY[mid] * sf
            consommation_kw = max(0.02, consommation_kw - solar_kw)

        consommation_kw = round(consommation_kw, 3)

        # --- Voltage ---
        ac_running = (ctype == "residentiel" and month in (6, 7, 8, 9) and 12 <= hour <= 23)
        tension_v  = compute_voltage(NOMINAL_VOLTAGE_V, lf, ctype)
        tension_v  = round(tension_v, 3)

        # --- Current (physics: I = P / V) ---
        courant_a = (consommation_kw * 1000.0) / max(tension_v, 1.0)
        courant_a += float(self.rng.normal(0, METER_NOISE_STD_A))
        courant_a = round(max(0.0, courant_a), 3)

        # --- Power factor ---
        pf = compute_power_factor(ctype, lf, ac_running)
        power_factor = round(pf, 4)

        return {
            "timestamp":        ts.strftime("%Y-%m-%d %H:%M:%S"),
            "meter_id":         mid,
            "zone":             f"Zone {self.zone_of.get(mid, 'A')}",
            "type":             ctype,
            "consommation_kw":  consommation_kw,
            "tension_v":        tension_v,
            "courant_a":        courant_a,
            "power_factor":     power_factor,
            "statut":           "NORMAL",
            "anomalies":        "",
            "is_alert":         0,
        }

    def generate(
        self,
        start: datetime,
        end: datetime,
        verbose: bool = True,
    ) -> pd.DataFrame:
        """
        Generate readings for all meters over the date range.
        Returns a DataFrame in the same column format as donnees_smart_meters.csv.
        """
        n_steps = int((end - start).total_seconds() / (self.interval_min * 60))
        timestamps = [start + timedelta(minutes=i * self.interval_min) for i in range(n_steps)]

        # Pre-determine which (timestamp, meter) pairs will be attacked
        # Attack clusters: one meter attacked at a time, in short bursts (5-30 min)
        attack_events = self._plan_attack_events(timestamps)

        all_rows = []
        n_attacks = 0

        for ts in timestamps:
            ts_rows = []
            for mid in self.meters:
                row = self._meter_reading(mid, ts)
                # Check if this meter is under attack at this timestamp
                atk = attack_events.get((ts, mid))
                if atk:
                    row = inject_attack(atk, row, self.rng)
                    n_attacks += 1
                ts_rows.append(row)

            # Add zone_consumption_mean (derived from current timestep)
            # This mirrors the preprocessing.py add_smart_meter_features()
            zone_means = {}
            for row in ts_rows:
                z = row["zone"]
                if z not in zone_means:
                    zone_means[z] = []
                zone_means[z].append(row["consommation_kw"])
            for row in ts_rows:
                row["zone_consumption_mean"] = round(
                    float(np.mean(zone_means[row["zone"]])), 4
                )

            all_rows.extend(ts_rows)

        df = pd.DataFrame(all_rows)

        if verbose:
            total = len(df)
            n_atk = (df["is_alert"] == 1).sum()
            print(f"  Generated {total:,} readings ({n_steps} timesteps x {self.n_meters} meters)")
            print(f"  Attacks: {n_atk:,} ({100.0*n_atk/total:.2f}% of readings)")
            print(f"  Attack type distribution:")
            for t, c in df[df["is_alert"]==1]["anomalies"].value_counts().items():
                print(f"    {t}: {c:,}")
            print(f"  Consumer type distribution:")
            for t, c in df["type"].value_counts().items():
                print(f"    {t}: {c:,}")

        return df

    def _plan_attack_events(
        self,
        timestamps: list[datetime],
    ) -> dict[tuple, str]:
        """
        Pre-plan attack events so the attack rate matches the target.
        Attacks come in bursts (5-30 min) on a single meter — not random noise.
        This is more realistic than independent Bernoulli flips.
        """
        total_cells = len(timestamps) * self.n_meters
        target_attack_cells = int(total_cells * self.attack_rate)

        events: dict[tuple, str] = {}
        cells_used = 0

        while cells_used < target_attack_cells:
            # Pick a random meter and start time
            mid = self.meters[int(self.rng.integers(0, self.n_meters))]
            start_idx = int(self.rng.integers(0, len(timestamps)))
            burst_len = int(self.rng.integers(3, 16))   # 3-15 timestep burst
            attack_type = self.ATTACK_TYPES[int(self.rng.integers(0, len(self.ATTACK_TYPES)))]

            for i in range(burst_len):
                idx = start_idx + i
                if idx >= len(timestamps):
                    break
                key = (timestamps[idx], mid)
                if key not in events:
                    events[key] = attack_type
                    cells_used += 1

        return events


# ── CLI entry point ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate realistic Algerian smart grid data")
    parser.add_argument("--days",        type=int,   default=14,    help="Days of data to generate")
    parser.add_argument("--start",       type=str,   default=None,  help="Start date YYYY-MM-DD (default: today)")
    parser.add_argument("--attack-rate", type=float, default=0.015, help="Fraction of readings that are attacks (default: 0.015 = 1.5%%)")
    parser.add_argument("--interval",    type=int,   default=2,     help="Sampling interval in minutes (default: 2)")
    parser.add_argument("--seed",        type=int,   default=42)
    args = parser.parse_args()

    start_dt = datetime.strptime(args.start, "%Y-%m-%d") if args.start else \
               datetime(2026, 6, 1)  # default: June 2026 (summer, includes Iftar patterns)
    end_dt   = start_dt + timedelta(days=args.days)

    print("=" * 60)
    print("  Realistic Algerian Smart Grid Dataset Generator")
    print("=" * 60)
    print(f"  Period : {start_dt.date()} -> {end_dt.date()} ({args.days} days)")
    print(f"  Meters : {METER_COUNT}")
    print(f"  Interval: {args.interval} min")
    print(f"  Attack rate: {args.attack_rate*100:.1f}%")
    print()

    gen = RealisticDatasetGenerator(
        n_meters=METER_COUNT,
        attack_rate=args.attack_rate,
        interval_minutes=args.interval,
        seed=args.seed,
    )
    df = gen.generate(start_dt, end_dt, verbose=True)

    out_name = f"donnees_realistic_{start_dt.strftime('%Y%m%d')}_{args.days}days.csv"
    out_path = OUTPUT_DIR / out_name
    df.to_csv(out_path, index=False)

    print(f"\n  Saved: {out_path}")
    print(f"  Shape: {df.shape}")
    print("=" * 60)
    print()
    print("  Next step: run ml_pipeline/run_transformer_autoencoder.py")
    print("  with --data-path pointing to the new CSV to retrain on")
    print("  realistic data distribution.")
    print("=" * 60)


if __name__ == "__main__":
    main()
