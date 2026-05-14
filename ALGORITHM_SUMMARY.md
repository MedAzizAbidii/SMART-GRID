# 🎯 Algorithm Summary - Quick Reference

## ❓ ML or LLM?

### **ANSWER: MACHINE LEARNING (ML)**

| Aspect | Your Project | LLM (like ChatGPT) |
|--------|-------------|-------------------|
| **Data Type** | ✅ Numerical time series | ❌ Text/Language |
| **Task** | ✅ Anomaly Detection | ❌ Text Generation |
| **Input** | ✅ Voltage, Current, Power | ❌ Words, Sentences |
| **Output** | ✅ NORMAL/ANOMALY | ❌ Text Response |
| **Domain** | ✅ Smart Grid/IoT | ❌ Natural Language |

---

## 🧠 ALGORITHM USED

### **Transformer Autoencoder**

**Type**: Deep Learning - Unsupervised Anomaly Detection

**Simple Explanation**:
```
1. Model learns what "NORMAL" smart meter data looks like
2. When it sees new data, it tries to reconstruct it
3. If reconstruction is BAD → Data is ABNORMAL (Anomaly)
4. If reconstruction is GOOD → Data is NORMAL
```

**Mathematical Formula**:
```
Anomaly Score = ||Input - Reconstructed||²

If Anomaly Score > Threshold:
    Prediction = ANOMALY
Else:
    Prediction = NORMAL
```

---

## 📊 PIPELINE IN 5 STEPS

### **STEP 1: DATA PREPARATION**
```
Raw Data (288,000 readings)
    ↓
Clean (remove outliers, missing values)
    ↓
Engineer Features (14 features)
    ↓
Create Sequences (20 timesteps each)
    ↓
Normalize (StandardScaler)
```

**Input Shape**: `(batch, 20, 14)`
- 20 timesteps (20 minutes)
- 14 features per timestep

---

### **STEP 2: MODEL ARCHITECTURE**
```
INPUT (20 timesteps × 14 features)
    ↓
Embedding Layer (14 → 128 dimensions)
    ↓
Positional Encoding (add time info)
    ↓
Transformer Encoder (4 layers, 8 attention heads)
    ↓
Decoder (128 → 14 features)
    ↓
OUTPUT (20 timesteps × 14 features)
```

**Parameters**: 1.2 million trainable weights

---

### **STEP 3: TRAINING**
```python
for epoch in range(50):
    # Forward pass
    reconstructed = model(input_data)
    
    # Calculate error
    loss = MSE(input_data, reconstructed)
    
    # Update weights
    optimizer.step()
    
    # Validate
    if val_loss improved:
        save_best_model()
```

**Training Time**: ~10-15 minutes on CPU

---

### **STEP 4: ANOMALY DETECTION**

**Multi-Criteria System (7 Criteria)**:

| Criterion | Weight | Threshold |
|-----------|--------|-----------|
| ML Reconstruction Error | 20% | 95th percentile |
| Voltage Anomaly | 20% | <207V or >253V |
| Consumption Anomaly | 15% | >mean+3σ |
| Power Factor | 15% | <0.85 |
| Frequency Deviation | 15% | <59.5Hz or >60.5Hz |
| Temporal Pattern | 10% | Unusual time |
| Rate of Change | 5% | Rapid spike/drop |

**Decision Rule**:
```python
total_score = sum(all_criteria_scores)

if total_score > 0.2:  # 20% threshold
    return ANOMALY
else:
    return NORMAL
```

---

### **STEP 5: VALIDATION**

**Metrics**:
```
Accuracy  = (TP + TN) / Total
Precision = TP / (TP + FP)
Recall    = TP / (TP + FN)
F1-Score  = 2 × (Precision × Recall) / (Precision + Recall)
```

**Current Performance**:
- ✅ Precision: 99.86% (very few false alarms)
- ⚠️ Recall: 15.22% (misses some anomalies)
- 📊 F1-Score: 26.42%

---

## 🔄 PRE-TRAINED MODEL (Transfer Learning)

### **What's Different?**

| Aspect | From Scratch | Pre-trained |
|--------|-------------|-------------|
| **Initialization** | Random weights | BERT-style weights |
| **Training Time** | Longer | Faster |
| **Data Needed** | More | Less |
| **Performance** | Good | Better |
| **Recall** | ~15% | ~30-45% (expected) |

### **Why Better?**
- Pre-trained model already learned attention patterns
- Fine-tune on your specific smart grid data
- Transfer knowledge from similar tasks

---

## 📈 DATA FLOW DIAGRAM

```
┌──────────────────────────────────────────────────────────┐
│ RAW DATA                                                 │
│ timestamp, meter_id, voltage, current, consumption, ...  │
└────────────────────┬─────────────────────────────────────┘
                     ↓
┌──────────────────────────────────────────────────────────┐
│ CLEANING                                                 │
│ Remove: duplicates, missing values, outliers            │
└────────────────────┬─────────────────────────────────────┘
                     ↓
┌──────────────────────────────────────────────────────────┐
│ FEATURE ENGINEERING (14 features)                        │
│ • Temporal: hour_sin, hour_cos, day_of_week             │
│ • Statistical: rolling_mean, rolling_std                │
│ • Rate: consumption_diff, rate_change                   │
└────────────────────┬─────────────────────────────────────┘
                     ↓
┌──────────────────────────────────────────────────────────┐
│ SEQUENCE CREATION                                        │
│ [t1, t2, ..., t20] → One sequence                        │
│ Shape: (N, 20, 14)                                       │
└────────────────────┬─────────────────────────────────────┘
                     ↓
┌──────────────────────────────────────────────────────────┐
│ NORMALIZATION                                            │
│ x_norm = (x - mean) / std                                │
└────────────────────┬─────────────────────────────────────┘
                     ↓
┌──────────────────────────────────────────────────────────┐
│ TRANSFORMER MODEL                                        │
│ Input → Encoder → Decoder → Output                       │
│ Learn to reconstruct normal patterns                     │
└────────────────────┬─────────────────────────────────────┘
                     ↓
┌──────────────────────────────────────────────────────────┐
│ ANOMALY DETECTION                                        │
│ Reconstruction Error + 6 Domain Rules                    │
│ → NORMAL or ANOMALY                                      │
└──────────────────────────────────────────────────────────┘
```

---

## 🎓 FOR YOUR PROFESSOR

### **Key Points to Mention**:

1. **Algorithm**: Transformer Autoencoder
   - Deep learning architecture
   - Originally from NLP, adapted for time series
   - Unsupervised anomaly detection

2. **Innovation**: Multi-Criteria Detection
   - Not just ML model
   - Combines ML + IEEE standards
   - 7 weighted criteria

3. **Transfer Learning**: Pre-trained Model
   - BERT-style initialization
   - Fine-tuned on smart grid data
   - Improves performance with less data

4. **Validation**: Comprehensive Metrics
   - Precision, Recall, F1-Score
   - ROC-AUC curve
   - Confusion matrix

5. **Real-world Application**:
   - IEEE 1547 compliance
   - Real-time detection
   - Dashboard visualization

---

## 📚 TECHNICAL TERMS EXPLAINED

| Term | Simple Explanation |
|------|-------------------|
| **Autoencoder** | Neural network that compresses and reconstructs data |
| **Transformer** | Architecture using attention mechanism |
| **Attention** | Model learns which parts of data are important |
| **Sequence** | Series of timesteps (like a video frame sequence) |
| **Embedding** | Converting data to higher-dimensional space |
| **Reconstruction Error** | Difference between input and output |
| **Transfer Learning** | Using pre-trained model knowledge |
| **Fine-tuning** | Adjusting pre-trained model for specific task |

---

## 🔢 FEATURE ENGINEERING DETAILS

### **14 Features Created**:

**Group 1: Temporal (4 features)**
- `hour_sin`, `hour_cos` - Cyclical time encoding
- `day_of_week` - 0=Monday, 6=Sunday
- `is_weekend` - Binary flag

**Group 2: Categorical (2 features)**
- `zone_encoded` - Geographic zone (0-3)
- `type_encoded` - Meter type (0-2)

**Group 3: Statistical (3 features)**
- `consumption_rolling_mean` - Average of last 5 readings
- `consumption_rolling_std` - Variability of last 5 readings
- `voltage_rolling_mean` - Average voltage

**Group 4: Rate of Change (2 features)**
- `consumption_diff` - Change from previous reading
- `consumption_rate_change` - Percentage change

**Group 5: Original (3 features)**
- `consommation_kw` - Power consumption
- `tension_v` - Voltage
- `courant_a` - Current

---

## 🎯 QUICK COMPARISON

### **Your Project vs Common ML**

| Aspect | Your Project | Typical ML |
|--------|-------------|-----------|
| **Algorithm** | Transformer Autoencoder | Random Forest, SVM |
| **Data Type** | Time Series Sequences | Tabular Data |
| **Features** | 14 engineered | Raw features |
| **Detection** | Multi-criteria (7) | Single model |
| **Standards** | IEEE 1547 compliant | Generic |
| **Deployment** | Real-time dashboard | Batch processing |

---

## ✅ SUMMARY FOR PRESENTATION

**"Our project uses a Transformer Autoencoder, a deep learning algorithm, for anomaly detection in smart grid data. The model learns normal patterns from 288,000 smart meter readings with 14 engineered features. We combine ML reconstruction error with 6 domain-specific rules based on IEEE standards. The system achieves 99.86% precision and is deployed with real-time dashboard visualization. We also implement transfer learning with a pre-trained BERT-style model to improve recall from 15% to an expected 30-45%."**

---

**Document Created**: May 14, 2026
**Purpose**: Academic explanation and presentation reference
