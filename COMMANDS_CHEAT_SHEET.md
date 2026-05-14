# 🚀 Smart Grid Simulation - Commands Cheat Sheet

## Quick Commands

### 🎯 Run Complete Simulation (Recommended)
```bash
py -3.10-64 run_simulation_with_enhanced_detection.py
```
**OR** double-click: `run_simulation.bat`

**What it does:**
- Simulates 100 smart meters for 24 hours
- Detects anomalies using 7 criteria
- Generates comprehensive reports
- Saves results to `simulation_results/`

**Duration:** ~5-10 minutes

---

### 🔧 Train Model First (Optional but Recommended)
```bash
py -3.10-64 run_ml_pipeline_fast.py
```

**What it does:**
- Trains Transformer Autoencoder on existing data
- Tests enhanced anomaly detection
- Saves model to `ml_pipeline/models/best_transformer.pth`
- Generates baseline performance metrics

**Duration:** ~3-5 minutes

---

### 📊 Compare Detection Methods
```bash
py -3.10-64 compare_detectors.py
```

**What it does:**
- Shows comparison between basic and enhanced detectors
- Explains 7 detection criteria
- Shows expected improvements

**Duration:** < 1 minute

---

## Complete Workflow

### First Time Setup
```bash
# 1. Install dependencies
py -3.10-64 -m pip install -r ml_pipeline/requirements_ml.txt

# 2. Train the model
py -3.10-64 run_ml_pipeline_fast.py

# 3. Run simulation
py -3.10-64 run_simulation_with_enhanced_detection.py
```

### Subsequent Runs
```bash
# Just run the simulation (model already trained)
py -3.10-64 run_simulation_with_enhanced_detection.py
```

---

## Alternative Commands

### Using Standard Python (if py command doesn't work)
```bash
python run_simulation_with_enhanced_detection.py
```

### Using Batch File (Windows)
```bash
run_simulation.bat
```

### Check Python Version
```bash
py -3.10-64 --version
```

### Verify Dependencies
```bash
py -3.10-64 -c "import torch; import pandas; import numpy; import sklearn; print('All packages installed!')"
```

---

## File Locations

### Input Files
- `donnees_smart_meters.csv` - Training data (optional)
- `ml_pipeline/requirements_ml.txt` - Dependencies list

### Output Directories
- `simulation_results/` - Simulation outputs
- `ml_pipeline/models/` - Trained models
- `ml_pipeline/results/` - Training results
- `ml_pipeline/plots/` - Visualizations

### Configuration Files
- `ml_pipeline/config_ml.py` - ML configuration
- `ml_pipeline/enhanced_anomaly_detection.py` - Detection settings

---

## Quick Customization

### Change Number of Meters
Edit `run_simulation_with_enhanced_detection.py` line 380:
```python
n_meters = 100  # Change to 50, 200, 500, etc.
```

### Change Simulation Duration
Edit `run_simulation_with_enhanced_detection.py` line 381:
```python
duration_hours = 24  # Change to 12, 48, 72, etc.
```

### Adjust Detection Sensitivity
Edit `ml_pipeline/enhanced_anomaly_detection.py` line 75:
```python
score.is_anomaly = score.total_score > 0.5  # Lower = more sensitive (0.3-0.7)
```

---

## View Results

### Quick Summary
```bash
type simulation_results\simulation_summary.txt
```

### Full Report
```bash
type simulation_results\simulation_report.txt
```

### Open Results in Excel
```bash
start simulation_results\simulation_results.csv
```

### View Plots
```bash
start simulation_results\plots\
```

---

## Troubleshooting Commands

### Check if Python 64-bit is Installed
```bash
py -3.10-64 --version
```

### Install Missing Dependencies
```bash
py -3.10-64 -m pip install torch pandas numpy scikit-learn matplotlib seaborn shap
```

### Reinstall All Dependencies
```bash
py -3.10-64 -m pip install --upgrade -r ml_pipeline/requirements_ml.txt
```

### Check PyTorch Installation
```bash
py -3.10-64 -c "import torch; print('PyTorch version:', torch.__version__); print('Device:', 'cuda' if torch.cuda.is_available() else 'cpu')"
```

### Clear Previous Results
```bash
rmdir /s /q simulation_results
```

---

## Performance Testing

### Quick Test (Small Scale)
Edit `run_simulation_with_enhanced_detection.py`:
```python
n_meters = 50
duration_hours = 12
```
Then run: `py -3.10-64 run_simulation_with_enhanced_detection.py`

### Standard Test (Default)
```python
n_meters = 100
duration_hours = 24
```

### Large Scale Test
```python
n_meters = 500
duration_hours = 48
```

---

## Data Analysis Commands

### Count Anomalies
```bash
py -3.10-64 -c "import pandas as pd; df = pd.read_csv('simulation_results/simulation_results.csv'); print(f'Total: {len(df)}, Anomalies: {df[\"is_anomaly\"].sum()}, Rate: {df[\"is_anomaly\"].mean()*100:.2f}%')"
```

### Anomaly Type Distribution
```bash
py -3.10-64 -c "import pandas as pd; df = pd.read_csv('simulation_results/simulation_results.csv'); print(df[df['is_anomaly']==1]['anomaly_type'].value_counts())"
```

### Average Confidence Score
```bash
py -3.10-64 -c "import pandas as pd; df = pd.read_csv('simulation_results/simulation_results.csv'); print(f'Avg confidence: {df[\"confidence\"].mean():.4f}')"
```

---

## Documentation Commands

### View Simulation Guide
```bash
type SIMULATION_GUIDE.md
```

### View Enhanced Detection Details
```bash
type ENHANCED_ANOMALY_DETECTION.md
```

### View Upgrade Summary
```bash
type ANOMALY_DETECTION_UPGRADE_SUMMARY.md
```

### View French Summary
```bash
type RESUME_AMELIORATION_DETECTION_ANOMALIES.md
```

---

## Common Workflows

### Workflow 1: First Time User
```bash
# 1. Check Python
py -3.10-64 --version

# 2. Install dependencies
py -3.10-64 -m pip install -r ml_pipeline/requirements_ml.txt

# 3. View comparison
py -3.10-64 compare_detectors.py

# 4. Train model
py -3.10-64 run_ml_pipeline_fast.py

# 5. Run simulation
py -3.10-64 run_simulation_with_enhanced_detection.py

# 6. View results
start simulation_results\simulation_summary.txt
```

### Workflow 2: Quick Test
```bash
# Just run simulation (uses default settings)
py -3.10-64 run_simulation_with_enhanced_detection.py
```

### Workflow 3: Experimentation
```bash
# 1. Modify detection settings in enhanced_anomaly_detection.py
# 2. Run simulation
py -3.10-64 run_simulation_with_enhanced_detection.py
# 3. Compare results
# 4. Adjust and repeat
```

---

## Batch Operations

### Run Multiple Simulations
Create a batch file `run_multiple.bat`:
```batch
@echo off
echo Running simulation 1...
py -3.10-64 run_simulation_with_enhanced_detection.py
move simulation_results simulation_results_1

echo Running simulation 2...
py -3.10-64 run_simulation_with_enhanced_detection.py
move simulation_results simulation_results_2

echo Running simulation 3...
py -3.10-64 run_simulation_with_enhanced_detection.py
move simulation_results simulation_results_3

echo All simulations complete!
```

---

## Environment Variables (Optional)

### Set Python Path
```bash
set PYTHON_PATH=C:\Python310-64\python.exe
%PYTHON_PATH% run_simulation_with_enhanced_detection.py
```

### Set Output Directory
Edit script to use custom output directory:
```python
output_dir = "custom_results"
```

---

## Git Commands (If Using Version Control)

### Ignore Results
Add to `.gitignore`:
```
simulation_results/
ml_pipeline/models/*.pth
ml_pipeline/results/
ml_pipeline/plots/
*.csv
temp_*.csv
```

### Commit Changes
```bash
git add .
git commit -m "Enhanced anomaly detection system"
git push
```

---

## Performance Benchmarks

| Configuration | Meters | Hours | Readings | Duration | Memory |
|--------------|--------|-------|----------|----------|--------|
| Quick Test | 50 | 12 | 2,400 | ~2 min | ~500 MB |
| Standard | 100 | 24 | 9,600 | ~5 min | ~1 GB |
| Large | 500 | 24 | 48,000 | ~15 min | ~3 GB |
| Full Day | 1000 | 24 | 96,000 | ~25 min | ~5 GB |

---

## Emergency Commands

### Kill Stuck Process
```bash
Ctrl + C
```

### Force Stop Python
```bash
taskkill /F /IM python.exe
```

### Clear Python Cache
```bash
py -3.10-64 -m pip cache purge
```

### Reinstall Everything
```bash
py -3.10-64 -m pip uninstall -y torch pandas numpy scikit-learn matplotlib seaborn shap
py -3.10-64 -m pip install -r ml_pipeline/requirements_ml.txt
```

---

## Summary

### Most Important Commands

1. **Run Simulation:**
   ```bash
   py -3.10-64 run_simulation_with_enhanced_detection.py
   ```

2. **Train Model:**
   ```bash
   py -3.10-64 run_ml_pipeline_fast.py
   ```

3. **View Comparison:**
   ```bash
   py -3.10-64 compare_detectors.py
   ```

4. **Check Results:**
   ```bash
   type simulation_results\simulation_summary.txt
   ```

---

**That's it! You're ready to run the simulation.** 🚀

```bash
py -3.10-64 run_simulation_with_enhanced_detection.py
```
