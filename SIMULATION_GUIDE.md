# 🚀 Smart Grid Simulation with Enhanced Anomaly Detection - Guide

## Overview

This guide explains how to run the complete smart grid simulation with the new enhanced anomaly detection system.

---

## 📋 Prerequisites

### 1. Python Environment
Make sure you have Python 3.10 64-bit installed and all dependencies:

```bash
py -3.10-64 -m pip install -r ml_pipeline/requirements_ml.txt
```

### 2. Trained Model (Optional but Recommended)
For best results, train the model first:

```bash
py -3.10-64 run_ml_pipeline_fast.py
```

This will:
- Train the Transformer Autoencoder model
- Save it to `ml_pipeline/models/best_transformer.pth`
- Generate baseline performance metrics

---

## 🎯 Running the Simulation

### Option 1: Full Simulation (Recommended)

Run the complete simulation with enhanced anomaly detection:

```bash
py -3.10-64 run_simulation_with_enhanced_detection.py
```

**What it does:**
1. ✅ Loads or trains the anomaly detection model
2. ✅ Simulates 100 smart meters for 24 hours (15-min intervals)
3. ✅ Generates realistic consumption data by consumer type
4. ✅ Detects anomalies using 7 criteria (voltage, consumption, power factor, etc.)
5. ✅ Generates comprehensive reports and visualizations
6. ✅ Saves all results to `simulation_results/` directory

**Duration:** ~5-10 minutes (depending on your system)

### Option 2: Train Model Only

If you just want to train/test the enhanced detection on existing data:

```bash
py -3.10-64 run_ml_pipeline_fast.py
```

**What it does:**
1. ✅ Loads sample from `donnees_smart_meters.csv` (50,000 records)
2. ✅ Trains Transformer Autoencoder
3. ✅ Runs enhanced multi-criteria anomaly detection
4. ✅ Generates evaluation reports and plots
5. ✅ Saves results to `ml_pipeline/results/` and `ml_pipeline/plots/`

**Duration:** ~3-5 minutes

---

## 📊 Simulation Parameters

You can customize the simulation by editing `run_simulation_with_enhanced_detection.py`:

```python
# Line ~380 - Simulation parameters
n_meters = 100          # Number of smart meters (default: 100)
duration_hours = 24     # Simulation duration in hours (default: 24)
```

### Recommended Settings

| Use Case | n_meters | duration_hours | Total Readings | Duration |
|----------|----------|----------------|----------------|----------|
| **Quick Test** | 50 | 12 | 2,400 | ~2 min |
| **Standard** | 100 | 24 | 9,600 | ~5 min |
| **Large Scale** | 500 | 48 | 96,000 | ~20 min |
| **Full Day** | 1000 | 24 | 96,000 | ~20 min |

---

## 📁 Output Files

After running the simulation, you'll find results in `simulation_results/`:

### Main Results
```
simulation_results/
├── simulated_meter_data.csv          # Raw simulated data
├── simulation_results.csv            # Results with anomaly predictions
├── anomaly_details.csv               # Detailed anomaly scores
├── simulation_summary.txt            # Quick summary
├── simulation_report.txt             # Comprehensive report
└── plots/                            # Visualizations
    ├── confusion_matrix.png
    ├── roc_curve.png
    ├── criterion_heatmap.png
    ├── anomaly_type_distribution.png
    └── confidence_distribution.png
```

### Key Files Explained

#### 1. `simulation_results.csv`
Contains all readings with anomaly predictions:
- `timestamp`, `meter_id`, `type`, `zone`
- `consommation_kw`, `tension_v`, `courant_a`, `facteur_puissance`
- `is_anomaly` (0/1)
- `anomaly_type` (voltage, consumption, power_factor, etc.)
- `confidence` (0-1 score)
- Individual criterion scores

#### 2. `anomaly_details.csv`
Detailed breakdown for each sample:
- All 7 criterion scores
- Total weighted score
- Anomaly classification
- Confidence level

#### 3. `simulation_summary.txt`
Quick overview:
- Simulation parameters
- Detection statistics
- Performance metrics (Accuracy, Precision, Recall, F1-Score)

#### 4. `simulation_report.txt`
Comprehensive analysis:
- Performance by anomaly type
- Criterion contribution analysis
- Detailed statistics

---

## 🔍 Understanding the Results

### Anomaly Types

The enhanced detector classifies anomalies into 7 types:

| Type | Description | Example |
|------|-------------|---------|
| **reconstruction** | ML-detected pattern deviation | Unusual feature combination |
| **voltage** | Voltage out of range | 195V (< 207V normal) |
| **consumption** | Unusual consumption pattern | 45 kW spike (normal: 12 kW) |
| **power_factor** | Low power factor | PF = 0.65 (< 0.85 standard) |
| **frequency** | Grid frequency deviation | 58.9 Hz (< 59.5 Hz normal) |
| **temporal** | Time-based anomaly | Commercial usage at 3 AM |
| **rate_change** | Sudden spike/drop | 10 kW → 40 kW instantly |

### Performance Metrics

#### Accuracy
Percentage of correct predictions (both anomalies and normal)

#### Precision
Of all detected anomalies, how many were real?
- **High precision** = Few false alarms
- **Low precision** = Many false alarms

#### Recall
Of all real anomalies, how many were detected?
- **High recall** = Few missed anomalies
- **Low recall** = Many missed anomalies

#### F1-Score
Harmonic mean of precision and recall (balanced metric)
- **High F1** = Good balance between precision and recall

---

## 🎨 Visualizations

### 1. Confusion Matrix (`confusion_matrix.png`)
Shows:
- True Positives (correctly detected anomalies)
- True Negatives (correctly identified normal)
- False Positives (false alarms)
- False Negatives (missed anomalies)

### 2. ROC Curve (`roc_curve.png`)
Shows trade-off between true positive rate and false positive rate

### 3. Criterion Heatmap (`criterion_heatmap.png`)
Shows which criteria triggered for each detected anomaly
- Rows: 7 detection criteria
- Columns: Detected anomalies
- Color: Score intensity (0-1)

### 4. Anomaly Type Distribution (`anomaly_type_distribution.png`)
Bar chart showing count of each anomaly type detected

### 5. Confidence Distribution (`confidence_distribution.png`)
Histograms showing confidence scores for:
- True Positives
- False Positives
- True Negatives
- False Negatives

---

## 🔧 Customization

### Adjust Detection Sensitivity

Edit `ml_pipeline/enhanced_anomaly_detection.py`:

#### Make Detection More Sensitive (Detect More Anomalies)
```python
# Line ~75 - Lower the anomaly threshold
score.is_anomaly = score.total_score > 0.4  # Default: 0.5
```

#### Make Detection Less Sensitive (Fewer False Alarms)
```python
# Line ~75 - Raise the anomaly threshold
score.is_anomaly = score.total_score > 0.6  # Default: 0.5
```

### Adjust Criterion Weights

Edit `ml_pipeline/enhanced_anomaly_detection.py`:

```python
# Line ~48 - Adjust weights (must sum to 1.0)
self.weights = {
    'reconstruction': 0.20,  # ML-based detection
    'voltage': 0.30,         # Increase for voltage focus
    'consumption': 0.20,     # Increase for consumption focus
    'power_factor': 0.10,    # Decrease if less important
    'frequency': 0.10,       # Decrease if less important
    'temporal': 0.05,        # Decrease if less important
    'rate_change': 0.05      # Decrease if less important
}
```

### Adjust Voltage Thresholds

Edit `ml_pipeline/enhanced_anomaly_detection.py`:

```python
# Line ~38 - Adjust voltage thresholds
self.thresholds = {
    'voltage_min': 200.0,      # More strict (default: 207.0)
    'voltage_max': 260.0,      # More strict (default: 253.0)
    # ... other thresholds
}
```

---

## 🐛 Troubleshooting

### Error: "No module named 'torch'"
**Solution:** Install dependencies
```bash
py -3.10-64 -m pip install -r ml_pipeline/requirements_ml.txt
```

### Error: "donnees_smart_meters.csv not found"
**Solution:** The simulation will work without it, but for better results:
1. Make sure your data file is in the root directory
2. Or run simulation-only mode (it will generate synthetic data)

### Error: "CUDA out of memory"
**Solution:** The code automatically uses CPU if CUDA is not available. No action needed.

### Simulation is Slow
**Solutions:**
1. Reduce `n_meters` (e.g., 50 instead of 100)
2. Reduce `duration_hours` (e.g., 12 instead of 24)
3. Use faster computer or enable GPU if available

### Low Detection Performance
**Solutions:**
1. Train model on more data: Increase `nrows` in `run_ml_pipeline_fast.py`
2. Adjust detection threshold (see Customization section)
3. Adjust criterion weights based on your priorities

---

## 📈 Expected Results

### Enhanced Detector Performance

Based on the improvements, you should see:

| Metric | Basic Detector | Enhanced Detector |
|--------|---------------|-------------------|
| **Precision** | 93.64% | 70-85% |
| **Recall** | 5.48% | 40-60% |
| **F1-Score** | 10.36% | 50-70% |
| **Explainability** | None | Full (7 types) |

### Anomaly Distribution

Typical distribution of detected anomalies:
- **Voltage anomalies**: 20-30%
- **Consumption anomalies**: 25-35%
- **Power factor anomalies**: 15-20%
- **Temporal anomalies**: 10-15%
- **Reconstruction (ML)**: 10-15%
- **Frequency anomalies**: 5-10%
- **Rate of change**: 5-10%

---

## 🚀 Quick Start Commands

### Complete Workflow (Recommended)

```bash
# 1. Train the model (first time only)
py -3.10-64 run_ml_pipeline_fast.py

# 2. Run simulation with enhanced detection
py -3.10-64 run_simulation_with_enhanced_detection.py

# 3. View results
# Check simulation_results/ directory for all outputs
```

### Quick Test (No Training)

```bash
# Run simulation only (generates synthetic data)
py -3.10-64 run_simulation_with_enhanced_detection.py
```

### Compare Detectors

```bash
# View comparison between basic and enhanced
py -3.10-64 compare_detectors.py
```

---

## 📚 Additional Resources

### Documentation Files
- `ENHANCED_ANOMALY_DETECTION.md` - Technical details (English)
- `ANOMALY_DETECTION_UPGRADE_SUMMARY.md` - Complete summary (English)
- `RESUME_AMELIORATION_DETECTION_ANOMALIES.md` - Résumé complet (Français)

### Source Code
- `ml_pipeline/enhanced_anomaly_detection.py` - Detection logic
- `ml_pipeline/enhanced_evaluation.py` - Evaluation logic
- `run_simulation_with_enhanced_detection.py` - Main simulation script

---

## ✅ Checklist

Before running the simulation:

- [ ] Python 3.10 64-bit installed
- [ ] Dependencies installed (`pip install -r ml_pipeline/requirements_ml.txt`)
- [ ] Model trained (optional: `py -3.10-64 run_ml_pipeline_fast.py`)
- [ ] Reviewed simulation parameters (n_meters, duration_hours)
- [ ] Enough disk space for results (~100 MB for standard simulation)

---

## 🎉 You're Ready!

Run the simulation:

```bash
py -3.10-64 run_simulation_with_enhanced_detection.py
```

The simulation will:
1. ✅ Generate realistic smart meter data
2. ✅ Detect anomalies using 7 criteria
3. ✅ Provide detailed explanations for each anomaly
4. ✅ Generate comprehensive reports and visualizations
5. ✅ Save everything to `simulation_results/`

**Enjoy your enhanced smart grid anomaly detection system!** 🚀

---

**Created**: May 11, 2026  
**Version**: 1.0  
**Status**: Ready to Run
