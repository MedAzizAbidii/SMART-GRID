# 🔥 Smart Grid Simulation with Enhanced Anomaly Detection

## Quick Start

### Windows (Easiest)
Double-click `run_simulation.bat`

### Command Line
```bash
py -3.10-64 run_simulation_with_enhanced_detection.py
```

---

## What This Does

This simulation creates a **complete smart grid environment** with:

1. **100 Smart Meters** (configurable)
   - Residential, Commercial, Industrial consumers
   - Realistic consumption patterns by time of day
   - Multiple zones (A, B, C, D)

2. **24 Hours of Data** (configurable)
   - 15-minute intervals (96 readings per meter)
   - Total: 9,600 readings

3. **Enhanced Anomaly Detection**
   - 7 detection criteria (voltage, consumption, power factor, etc.)
   - ML-based + Rule-based detection
   - IEEE standards compliance
   - Full explainability

4. **Comprehensive Reports**
   - Performance metrics
   - Anomaly type breakdown
   - Visualizations (plots, heatmaps)
   - Detailed CSV results

---

## System Requirements

- **Python**: 3.10 64-bit
- **RAM**: 4 GB minimum, 8 GB recommended
- **Disk Space**: 500 MB free
- **OS**: Windows 10/11

---

## Installation

### 1. Install Python 3.10 64-bit
Download from: https://www.python.org/downloads/

### 2. Install Dependencies
```bash
py -3.10-64 -m pip install -r ml_pipeline/requirements_ml.txt
```

### 3. (Optional) Train Model First
```bash
py -3.10-64 run_ml_pipeline_fast.py
```

---

## Running the Simulation

### Method 1: Batch File (Easiest)
```bash
run_simulation.bat
```

### Method 2: Python Command
```bash
py -3.10-64 run_simulation_with_enhanced_detection.py
```

### Method 3: Train + Simulate
```bash
# Step 1: Train model on existing data
py -3.10-64 run_ml_pipeline_fast.py

# Step 2: Run simulation
py -3.10-64 run_simulation_with_enhanced_detection.py
```

---

## Output Files

All results are saved to `simulation_results/`:

```
simulation_results/
├── simulated_meter_data.csv          # Raw simulated data
├── simulation_results.csv            # With anomaly predictions
├── anomaly_details.csv               # Detailed scores
├── simulation_summary.txt            # Quick overview
├── simulation_report.txt             # Full report
└── plots/                            # Visualizations
    ├── confusion_matrix.png
    ├── roc_curve.png
    ├── criterion_heatmap.png
    ├── anomaly_type_distribution.png
    └── confidence_distribution.png
```

---

## Customization

### Change Number of Meters
Edit `run_simulation_with_enhanced_detection.py` line ~380:
```python
n_meters = 100  # Change to 50, 200, 500, etc.
```

### Change Simulation Duration
Edit `run_simulation_with_enhanced_detection.py` line ~381:
```python
duration_hours = 24  # Change to 12, 48, 72, etc.
```

### Adjust Detection Sensitivity
Edit `ml_pipeline/enhanced_anomaly_detection.py` line ~75:
```python
score.is_anomaly = score.total_score > 0.5  # Lower = more sensitive
```

---

## Understanding Results

### Anomaly Types Detected

| Type | What It Means |
|------|---------------|
| **voltage** | Voltage out of normal range (207-253V) |
| **consumption** | Unusual consumption pattern or spike |
| **power_factor** | Low power factor (< 0.85) |
| **frequency** | Grid frequency deviation (59.5-60.5 Hz) |
| **temporal** | Unusual time-based pattern |
| **reconstruction** | ML-detected pattern deviation |
| **rate_change** | Sudden spike or drop |

### Performance Metrics

- **Accuracy**: Overall correctness
- **Precision**: How many detected anomalies are real
- **Recall**: How many real anomalies are detected
- **F1-Score**: Balance between precision and recall

### Expected Performance

| Metric | Target |
|--------|--------|
| Precision | 70-85% |
| Recall | 40-60% |
| F1-Score | 50-70% |

---

## Troubleshooting

### "Python not found"
Install Python 3.10 64-bit from python.org

### "Module not found"
```bash
py -3.10-64 -m pip install -r ml_pipeline/requirements_ml.txt
```

### Simulation is slow
Reduce `n_meters` or `duration_hours` in the script

### Low performance
Train model first: `py -3.10-64 run_ml_pipeline_fast.py`

---

## Documentation

- **`SIMULATION_GUIDE.md`** - Complete guide
- **`ENHANCED_ANOMALY_DETECTION.md`** - Technical details
- **`ANOMALY_DETECTION_UPGRADE_SUMMARY.md`** - System overview
- **`compare_detectors.py`** - Compare basic vs enhanced

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    SMART GRID SIMULATION                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐      ┌──────────────┐                    │
│  │ Smart Meters │─────▶│ Data Stream  │                    │
│  │  (100 units) │      │ (15-min int) │                    │
│  └──────────────┘      └──────┬───────┘                    │
│                               │                             │
│                               ▼                             │
│  ┌────────────────────────────────────────────────┐        │
│  │     ENHANCED ANOMALY DETECTION SYSTEM          │        │
│  ├────────────────────────────────────────────────┤        │
│  │                                                 │        │
│  │  1. ML Reconstruction (20%)                    │        │
│  │  2. Voltage Check (20%)                        │        │
│  │  3. Consumption Analysis (15%)                 │        │
│  │  4. Power Factor (15%)                         │        │
│  │  5. Frequency (15%)                            │        │
│  │  6. Temporal Patterns (10%)                    │        │
│  │  7. Rate of Change (5%)                        │        │
│  │                                                 │        │
│  │  ▼ Weighted Scoring ▼                          │        │
│  │                                                 │        │
│  │  Anomaly Classification + Confidence           │        │
│  └────────────────┬────────────────────────────────┘        │
│                   │                                         │
│                   ▼                                         │
│  ┌────────────────────────────────────────────────┐        │
│  │           RESULTS & REPORTS                     │        │
│  ├────────────────────────────────────────────────┤        │
│  │  • Performance Metrics                          │        │
│  │  • Anomaly Type Breakdown                       │        │
│  │  • Visualizations                               │        │
│  │  • Detailed CSV Reports                         │        │
│  └────────────────────────────────────────────────┘        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Features

✅ **Realistic Simulation**
- Consumer type-specific patterns
- Time-of-day variations
- Weekend/weekday differences

✅ **Multi-Criteria Detection**
- 7 different detection methods
- Weighted scoring system
- Configurable thresholds

✅ **IEEE Compliant**
- Voltage standards (±10%)
- Frequency tolerance (±0.5 Hz)
- Power factor minimum (0.85)

✅ **Explainable AI**
- Know WHY each anomaly detected
- Detailed criterion breakdown
- Confidence scores

✅ **Comprehensive Reports**
- Performance metrics
- Type-based analysis
- Visual plots and heatmaps

---

## Example Output

```
================================================================================
SMART GRID SIMULATION WITH ENHANCED ANOMALY DETECTION
================================================================================

⏰ Simulation started at: 2026-05-11 14:30:00
⚙️ Device: cpu

================================================================================
STEP 1: LOAD/TRAIN ANOMALY DETECTION MODEL
================================================================================

✅ Loading existing model from: ml_pipeline/models/best_transformer.pth

================================================================================
STEP 2: INITIALIZE ENHANCED ANOMALY DETECTOR
================================================================================

✅ Enhanced detector initialized with 7 detection criteria:
   1. ML Reconstruction Error (20%)
   2. Voltage Anomalies (20%)
   3. Consumption Anomalies (15%)
   4. Power Factor Anomalies (15%)
   5. Frequency Anomalies (15%)
   6. Temporal Anomalies (10%)
   7. Rate of Change Anomalies (5%)

================================================================================
STEP 3: SIMULATE SMART METER DATA
================================================================================

🏭 Simulating 100 smart meters for 24 hours...
   • Generating 96 timesteps (15-min intervals)...
   • Progress: 25.0% (24/96 timesteps)
   • Progress: 50.0% (48/96 timesteps)
   • Progress: 75.0% (72/96 timesteps)
   • Progress: 100.0% (96/96 timesteps)

   ✅ Simulation complete: 9,600 readings generated

================================================================================
REAL-TIME ANOMALY DETECTION
================================================================================

📊 Computing baseline statistics...
   ✅ Baseline statistics computed
      • Avg consumption: 12.45 kW
      • Avg voltage: 230.12 V

🔍 Running enhanced multi-criteria detection...
   ✅ Detection complete:
      • Total samples: 9,600
      • Anomalies detected: 1,248 (13.00%)

   📊 Anomaly breakdown:
      • consumption: 412 (33.0%)
      • voltage: 356 (28.5%)
      • power_factor: 245 (19.6%)
      • temporal: 134 (10.7%)
      • reconstruction: 67 (5.4%)
      • frequency: 23 (1.8%)
      • rate_change: 11 (0.9%)

================================================================================
✅ SIMULATION COMPLETE
================================================================================

📁 Results saved to: simulation_results/
   • Simulated data: simulation_results/simulated_meter_data.csv
   • Detection results: simulation_results/simulation_results.csv
   • Anomaly details: simulation_results/anomaly_details.csv
   • Summary report: simulation_results/simulation_summary.txt
   • Full report: simulation_results/simulation_report.txt
   • Visualizations: simulation_results/plots/

📊 Final Performance:
   • Accuracy:  87.23%
   • Precision: 76.45%
   • Recall:    54.32%
   • F1-Score:  63.51%

⏰ Simulation completed at: 2026-05-11 14:35:23
```

---

## Support

For issues or questions:
1. Check `SIMULATION_GUIDE.md` for detailed instructions
2. Review `ENHANCED_ANOMALY_DETECTION.md` for technical details
3. Run `compare_detectors.py` to understand the system

---

## License

See `License.txt` in the project root.

---

**Ready to simulate!** 🚀

```bash
py -3.10-64 run_simulation_with_enhanced_detection.py
```
