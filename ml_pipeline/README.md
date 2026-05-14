# 🔥 XAI-Transformer Pipeline for Smart Grid Anomaly Detection

Complete implementation of the 11-step end-to-end pipeline for explainable anomaly detection in smart grids.

## 📋 Pipeline Overview

### **Architecture Finale:**
```
DATA → preprocessing → sequences 
→ Transformer Autoencoder 
→ anomaly score 
→ Attention (où) 
→ SHAP (pourquoi) 
→ explication finale
```

## 🏗️ Components

### **1. Data Collection & Preprocessing** (`data_preprocessing.py`)
- ✅ Load smart meter CSV data
- ✅ Clean missing values and outliers
- ✅ Feature engineering (temporal, statistical, behavioral)
- ✅ Create temporal sequences
- ✅ Normalization (StandardScaler)

### **2. Transformer Autoencoder** (`transformer_model.py`)
- ✅ Input embedding
- ✅ Positional encoding
- ✅ Multi-head attention
- ✅ Feedforward layers
- ✅ Reconstruction decoder

### **3. Anomaly Detection** (`anomaly_detection.py`)
- ✅ Reconstruction error: `||input - output||`
- ✅ Dynamic threshold: `mean + k*std`
- ✅ Percentile-based threshold (95%)

### **4. Attention Explainability** (`attention_explainer.py`)
- ✅ Extract attention weights
- ✅ Identify critical timesteps
- ✅ Visualize attention heatmaps
- ✅ Answer: **WHERE** anomalies occur

### **5. SHAP Explainability** (`shap_explainer.py`)
- ✅ KernelSHAP implementation
- ✅ Feature importance ranking
- ✅ SHAP summary plots
- ✅ Answer: **WHY** anomalies occur

### **6. Explanation Fusion** (`explanation_fusion.py`)
- ✅ Combine Attention (WHERE) + SHAP (WHY)
- ✅ Generate human-readable summaries
- ✅ Export explanations to JSON

### **7. Evaluation** (`evaluation.py`)
- ✅ Accuracy, Precision, Recall, F1-Score
- ✅ ROC-AUC
- ✅ Confusion matrix
- ✅ Error distribution plots

## 🚀 Quick Start

### **1. Install Dependencies**
```bash
pip install -r ml_pipeline/requirements_ml.txt
```

### **2. Generate Smart Meter Data**
```bash
python smart_meters_simulator.py
```
Let it run for a few minutes to generate sufficient data.

### **3. Run Complete Pipeline**
```bash
python run_ml_pipeline.py
```

## 📊 Output

### **Models**
- `ml_pipeline/models/best_transformer.pth` - Trained model

### **Plots**
- `confusion_matrix.png` - Classification performance
- `roc_curve.png` - ROC curve
- `error_distribution.png` - Reconstruction error distribution
- `attention_heatmap.png` - Attention visualization
- `timestep_importance.png` - Critical timesteps
- `shap_feature_importance.png` - Feature contributions

### **Results**
- `anomaly_explanations.json` - Complete explanations for detected anomalies

## 📈 Features Engineered

1. **Temporal Features:**
   - `hour_sin`, `hour_cos` (cyclical encoding)
   - `day_of_week`, `is_weekend`

2. **Statistical Features:**
   - `consumption_rolling_mean`
   - `consumption_rolling_std`
   - `voltage_rolling_mean`

3. **Rate of Change:**
   - `consumption_diff`
   - `consumption_rate_change`

4. **Categorical Encoding:**
   - `zone_encoded`
   - `type_encoded` (residential/commercial/industrial)

## 🔍 Example Explanation Output

```
Anomalie détectée à t=4

CAUSE (Top 3 features):
  - volume trafic: +0.45
  - IP inconnue: +0.30
  - heure inhabituelle: +0.25

ZONE CRITIQUE (timesteps):
  - événements: t3, t4

METADATA:
  - Meter ID: SM_0042
  - Zone: Zone A
  - Type: commercial
```

## ⚙️ Configuration

Edit `ml_pipeline/config_ml.py` to customize:

- **Sequence length:** Number of timesteps per sequence
- **Model architecture:** d_model, n_heads, n_layers
- **Training:** epochs, learning rate, batch size
- **Thresholds:** Anomaly detection sensitivity
- **SHAP:** Number of background/test samples

## 📚 References

- **Transformer Architecture:** "Attention Is All You Need" (Vaswani et al., 2017)
- **SHAP:** "A Unified Approach to Interpreting Model Predictions" (Lundberg & Lee, 2017)
- **Anomaly Detection:** Reconstruction-based approach with autoencoders

## 🎯 Use Cases

1. **Real-time Monitoring:** Deploy model for live anomaly detection
2. **SOC Dashboard:** Integrate explanations into security operations
3. **Research:** Train ML models on realistic smart grid data
4. **Forensics:** Investigate past anomalies with full explainability

## 🔧 Advanced Usage

### **Custom Feature Engineering**
```python
from ml_pipeline.data_preprocessing import SmartGridDataPreprocessor

preprocessor = SmartGridDataPreprocessor(sequence_length=30)
# Add custom features in engineer_features() method
```

### **Model Tuning**
```python
from ml_pipeline.transformer_model import TransformerAutoencoder

model = TransformerAutoencoder(
    n_features=14,
    d_model=256,  # Increase capacity
    n_heads=16,
    n_encoder_layers=6
)
```

### **Threshold Optimization**
```python
from ml_pipeline.anomaly_detection import AnomalyDetector

detector = AnomalyDetector(model)
detector.set_threshold_dynamic(val_errors, multiplier=3.0)  # More conservative
```

## 📞 Support

For issues or questions, refer to the main project README or documentation.

---

**Built for:** Smart Grid Cybersecurity Research  
**Framework:** PyTorch + SHAP  
**License:** MIT
