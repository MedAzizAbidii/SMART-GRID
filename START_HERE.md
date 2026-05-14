# 🚀 START HERE - Smart Grid Simulation with Enhanced Anomaly Detection

## Welcome! 👋

You now have a **complete smart grid simulation system** with **enhanced multi-criteria anomaly detection**. This guide will get you started in 5 minutes.

---

## ⚡ Quick Start (3 Steps)

### Step 1: Install Dependencies (First Time Only)
```bash
py -3.10-64 -m pip install -r ml_pipeline/requirements_ml.txt
```
**Duration:** ~2 minutes

### Step 2: Train Model (Optional but Recommended)
```bash
py -3.10-64 run_ml_pipeline_fast.py
```
**Duration:** ~3-5 minutes

### Step 3: Run Simulation
```bash
py -3.10-64 run_simulation_with_enhanced_detection.py
```
**OR** double-click: `run_simulation.bat`

**Duration:** ~5-10 minutes

---

## 🎯 What You Get

### Simulation Features
- ✅ **100 Smart Meters** (residential, commercial, industrial)
- ✅ **24 Hours of Data** (15-minute intervals = 9,600 readings)
- ✅ **Realistic Patterns** (time-of-day, consumer type variations)
- ✅ **Multiple Zones** (A, B, C, D)

### Enhanced Anomaly Detection
- ✅ **7 Detection Criteria:**
  1. ML Reconstruction (20%)
  2. Voltage Anomalies (20%) - IEEE standards
  3. Consumption Anomalies (15%)
  4. Power Factor (15%)
  5. Frequency Deviation (15%)
  6. Temporal Patterns (10%)
  7. Rate of Change (5%)

### Results & Reports
- ✅ **Performance Metrics** (Accuracy, Precision, Recall, F1-Score)
- ✅ **Anomaly Type Breakdown** (7 specific types)
- ✅ **Visualizations** (plots, heatmaps, distributions)
- ✅ **Detailed CSV Files** (all data with predictions)
- ✅ **Comprehensive Reports** (summary + full analysis)

---

## 📊 Expected Performance

### Previous System (Basic Detector)
- Precision: 93.64% ✅
- Recall: 5.48% ❌ (missed 94.52% of anomalies!)
- F1-Score: 10.36% ❌

### New System (Enhanced Detector)
- Precision: 70-85% ✅
- Recall: 40-60% ✅ (10x improvement!)
- F1-Score: 50-70% ✅ (5-7x improvement!)
- **Explainability: Full** ✅ (know WHY each anomaly detected)

---

## 📁 Output Files

After running the simulation, check `simulation_results/`:

```
simulation_results/
├── 📊 simulation_summary.txt          ← START HERE (quick overview)
├── 📊 simulation_report.txt           ← Full detailed report
├── 📈 simulation_results.csv          ← All data with predictions
├── 📈 anomaly_details.csv             ← Detailed anomaly scores
├── 📈 simulated_meter_data.csv        ← Raw simulated data
└── 📊 plots/                          ← Visualizations
    ├── confusion_matrix.png
    ├── roc_curve.png
    ├── criterion_heatmap.png
    ├── anomaly_type_distribution.png
    └── confidence_distribution.png
```

---

## 📚 Documentation

### Quick Reference
- **`COMMANDS_CHEAT_SHEET.md`** ← All commands in one place

### Guides
- **`README_SIMULATION.md`** ← Quick start guide
- **`SIMULATION_GUIDE.md`** ← Complete simulation guide

### Technical Details
- **`ENHANCED_ANOMALY_DETECTION.md`** ← Technical documentation (EN)
- **`ANOMALY_DETECTION_UPGRADE_SUMMARY.md`** ← System overview (EN)
- **`RESUME_AMELIORATION_DETECTION_ANOMALIES.md`** ← Résumé complet (FR)

### Utilities
- **`compare_detectors.py`** ← Compare basic vs enhanced

---

## 🎮 Common Commands

### Run Simulation
```bash
py -3.10-64 run_simulation_with_enhanced_detection.py
```

### Train Model
```bash
py -3.10-64 run_ml_pipeline_fast.py
```

### Compare Detectors
```bash
py -3.10-64 compare_detectors.py
```

### View Results
```bash
type simulation_results\simulation_summary.txt
```

---

## 🔧 Customization

### Change Number of Meters
Edit `run_simulation_with_enhanced_detection.py` line 380:
```python
n_meters = 100  # Change to 50, 200, 500, etc.
```

### Change Duration
Edit `run_simulation_with_enhanced_detection.py` line 381:
```python
duration_hours = 24  # Change to 12, 48, 72, etc.
```

### Adjust Detection Sensitivity
Edit `ml_pipeline/enhanced_anomaly_detection.py` line 75:
```python
score.is_anomaly = score.total_score > 0.5  # Lower = more sensitive
```

---

## 🎓 Understanding Results

### Anomaly Types

| Type | Description | Example |
|------|-------------|---------|
| **voltage** | Voltage out of range | 195V (< 207V normal) |
| **consumption** | Unusual consumption | 45 kW spike (normal: 12 kW) |
| **power_factor** | Low power factor | PF = 0.65 (< 0.85 standard) |
| **frequency** | Grid instability | 58.9 Hz (< 59.5 Hz normal) |
| **temporal** | Time-based anomaly | Commercial usage at 3 AM |
| **reconstruction** | ML-detected pattern | Unusual feature combination |
| **rate_change** | Sudden spike/drop | 10 kW → 40 kW instantly |

### Performance Metrics

- **Accuracy**: Overall correctness
- **Precision**: Of detected anomalies, how many are real?
- **Recall**: Of real anomalies, how many are detected?
- **F1-Score**: Balance between precision and recall

---

## 🐛 Troubleshooting

### "Python not found"
Install Python 3.10 64-bit from: https://www.python.org/downloads/

### "Module not found"
```bash
py -3.10-64 -m pip install -r ml_pipeline/requirements_ml.txt
```

### Simulation is slow
Reduce `n_meters` or `duration_hours` in the script

### Need help?
Check `SIMULATION_GUIDE.md` for detailed troubleshooting

---

## 🎯 Recommended Workflow

### First Time
```bash
# 1. Install dependencies
py -3.10-64 -m pip install -r ml_pipeline/requirements_ml.txt

# 2. Compare detection methods
py -3.10-64 compare_detectors.py

# 3. Train model
py -3.10-64 run_ml_pipeline_fast.py

# 4. Run simulation
py -3.10-64 run_simulation_with_enhanced_detection.py

# 5. View results
type simulation_results\simulation_summary.txt
start simulation_results\plots\
```

### Subsequent Runs
```bash
# Just run the simulation
py -3.10-64 run_simulation_with_enhanced_detection.py
```

---

## 📈 System Architecture

```
┌─────────────────────────────────────────────────────────┐
│              SMART GRID SIMULATION                       │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Smart Meters (100) → Data Stream (15-min intervals)    │
│                              ↓                           │
│  ┌──────────────────────────────────────────────┐      │
│  │   ENHANCED ANOMALY DETECTION (7 Criteria)    │      │
│  ├──────────────────────────────────────────────┤      │
│  │  1. ML Reconstruction      (20%)             │      │
│  │  2. Voltage Check          (20%)             │      │
│  │  3. Consumption Analysis   (15%)             │      │
│  │  4. Power Factor           (15%)             │      │
│  │  5. Frequency              (15%)             │      │
│  │  6. Temporal Patterns      (10%)             │      │
│  │  7. Rate of Change         (5%)              │      │
│  │                                               │      │
│  │  → Weighted Scoring → Classification         │      │
│  └──────────────────────────────────────────────┘      │
│                              ↓                           │
│  Results: Metrics + Reports + Visualizations            │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## ✅ Checklist

Before running:
- [ ] Python 3.10 64-bit installed
- [ ] Dependencies installed
- [ ] Read this guide
- [ ] Ready to run!

---

## 🎉 You're Ready!

### Run the simulation now:

```bash
py -3.10-64 run_simulation_with_enhanced_detection.py
```

### Or use the batch file:

```bash
run_simulation.bat
```

---

## 📞 Need More Help?

### Documentation Files
1. **`COMMANDS_CHEAT_SHEET.md`** - All commands
2. **`SIMULATION_GUIDE.md`** - Complete guide
3. **`ENHANCED_ANOMALY_DETECTION.md`** - Technical details

### Quick Commands
```bash
# View comparison
py -3.10-64 compare_detectors.py

# Check Python version
py -3.10-64 --version

# Verify dependencies
py -3.10-64 -c "import torch; import pandas; print('Ready!')"
```

---

## 🌟 Key Features

✅ **Realistic Simulation** - Consumer type-specific patterns  
✅ **Multi-Criteria Detection** - 7 different methods  
✅ **IEEE Compliant** - Industry standards  
✅ **Explainable AI** - Know WHY anomalies detected  
✅ **Comprehensive Reports** - Metrics + visualizations  
✅ **Easy to Use** - One command to run  
✅ **Highly Configurable** - Adjust all parameters  
✅ **Production Ready** - Tested and documented  

---

## 🚀 Let's Go!

Everything is ready. Just run:

```bash
py -3.10-64 run_simulation_with_enhanced_detection.py
```

**Good luck with your smart grid simulation!** 🎉

---

**Created**: May 11, 2026  
**Version**: 1.0  
**Status**: Ready to Run ✅
