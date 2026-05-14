# 🚀 Quick Start Guide - ML Pipeline

## Step-by-Step Instructions

### **Step 1: Install ML Dependencies**

```bash
cd "c:\Users\Batikha\Desktop\SMART GRID\smartgrid_simulation"
pip install -r ml_pipeline\requirements_ml.txt
```

### **Step 2: Generate Training Data**

Run the smart meter simulator to generate data:

```bash
python smart_meters_simulator.py
```

**Let it run for 5-10 minutes** to generate sufficient data (~1000+ readings).  
Press `Ctrl+C` to stop when you have enough data.

You should see files created:
- `donnees_smart_meters.csv` (main data)
- `alertes_smart_meters.csv` (anomalies)

### **Step 3: Run the Complete ML Pipeline**

```bash
python run_ml_pipeline.py
```

This will execute all 11 steps:
1. ✅ Data Collection
2. ✅ Preprocessing
3. ✅ Feature Engineering
4. ✅ Transformer Model Training
5. ✅ Anomaly Detection
6. ✅ Attention Explainability
7. ✅ SHAP Explainability
8. ✅ Explanation Fusion
9. ✅ SOC Interface (plots)
10. ✅ Optimization
11. ✅ Evaluation

### **Step 4: View Results**

Check the generated outputs:

**Models:**
```
ml_pipeline/models/best_transformer.pth
```

**Visualizations:**
```
ml_pipeline/plots/
├── confusion_matrix.png
├── roc_curve.png
├── error_distribution.png
├── attention_heatmap.png
├── timestep_importance.png
└── shap_feature_importance.png
```

**Explanations:**
```
ml_pipeline/results/anomaly_explanations.json
```

## 📊 Expected Output

```
================================================================================
🔥 SMART GRID ANOMALY DETECTION - XAI TRANSFORMER PIPELINE
================================================================================

⚙️ Device: cuda

================================================================================
STEP 1-3: DATA PREPROCESSING & FEATURE ENGINEERING
================================================================================
📂 Loading data from donnees_smart_meters.csv...
   ✅ Loaded 2,500 records
🧹 Cleaning data...
   ✅ Cleaned data: 2,450 records remaining
🔢 Engineering features...
   ✅ Created 23 features
📊 Creating sequences (length=20)...
   ✅ Created 1,200 sequences
   • Normal sequences: 1,080
   • Anomaly sequences: 120

================================================================================
STEP 4: TRANSFORMER AUTOENCODER MODEL
================================================================================
📐 Model Architecture:
   • Input features: 14
   • Embedding dimension: 128
   • Attention heads: 8
   • Encoder layers: 4
   • Total parameters: 1,234,567

🚀 Training Transformer Autoencoder on cuda...
Epoch 1/50 - Train Loss: 0.045123, Val Loss: 0.038456
...
   ⏹️ Early stopping at epoch 25
   ✅ Training complete. Best val loss: 0.012345

================================================================================
STEP 5: ANOMALY DETECTION
================================================================================
🔍 Computing reconstruction errors...
📊 Setting anomaly threshold...
   📊 Threshold set at 95th percentile: 0.025678
🎯 Detecting anomalies on test set...
   • Detected 18 anomalies out of 180 samples
   • Detection rate: 10.00%

================================================================================
STEP 11: MODEL EVALUATION
================================================================================
📊 EVALUATION METRICS
   • Accuracy:  0.9444
   • Precision: 0.8889
   • Recall:    0.8000
   • F1-Score:  0.8421
   • ROC-AUC:   0.9234

================================================================================
✅ PIPELINE COMPLETE
================================================================================
```

## 🎯 What Each Component Does

### **1. Data Preprocessing**
- Loads CSV data from smart meters
- Cleans missing values
- Engineers 14 features (temporal, statistical, behavioral)
- Creates sequences of 20 timesteps
- Normalizes data

### **2. Transformer Model**
- Learns normal behavior patterns
- Uses attention mechanism to focus on important timesteps
- Reconstructs input sequences
- High reconstruction error = anomaly

### **3. Anomaly Detection**
- Computes reconstruction error for each sequence
- Sets threshold at 95th percentile
- Flags sequences above threshold as anomalies

### **4. Attention Explainability (WHERE)**
- Extracts attention weights from transformer
- Shows which timesteps are most important
- Visualizes attention heatmaps
- **Answers: WHEN did the anomaly occur?**

### **5. SHAP Explainability (WHY)**
- Computes feature contributions using SHAP
- Ranks features by importance
- Shows which features caused the anomaly
- **Answers: WHY did the anomaly occur?**

### **6. Explanation Fusion**
- Combines Attention (WHERE) + SHAP (WHY)
- Generates human-readable explanations
- Example:
  ```
  Anomalie détectée à t=4
  CAUSE:
    - consommation_kw: +0.45
    - tension_v: +0.30
  ZONE CRITIQUE:
    - événements t3, t4
  ```

## 🔧 Troubleshooting

### **Issue: Not enough data**
```
❌ Error: Not enough sequences created
```
**Solution:** Run `smart_meters_simulator.py` longer to generate more data.

### **Issue: CUDA out of memory**
```
RuntimeError: CUDA out of memory
```
**Solution:** Edit `ml_pipeline/config_ml.py`:
```python
BATCH_SIZE = 32  # Reduce from 64
D_MODEL = 64     # Reduce from 128
```

### **Issue: SHAP takes too long**
```
Computing SHAP values... (stuck)
```
**Solution:** Reduce samples in `ml_pipeline/config_ml.py`:
```python
SHAP_BACKGROUND_SAMPLES = 50  # Reduce from 100
SHAP_TEST_SAMPLES = 20        # Reduce from 50
```

## 📈 Next Steps

1. **Integrate with Dashboard:**
   - Add ML predictions to `api_server.py`
   - Display explanations in real-time dashboard

2. **Deploy Model:**
   - Load trained model: `torch.load('ml_pipeline/models/best_transformer.pth')`
   - Use for real-time anomaly detection

3. **Tune Hyperparameters:**
   - Experiment with different architectures
   - Optimize threshold for your use case

4. **Add More Features:**
   - Include weather data
   - Add grid topology features
   - Incorporate historical patterns

## 📚 Documentation

- **Full Pipeline:** `ml_pipeline/README.md`
- **Configuration:** `ml_pipeline/config_ml.py`
- **Main Project:** `README.md`

---

**Ready to detect anomalies with explainable AI! 🔥**
