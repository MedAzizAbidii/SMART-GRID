# 🤖 ML Pipeline Explanation - Smart Grid Anomaly Detection

## ❓ IS THIS ML OR LLM?

### **THIS IS MACHINE LEARNING (ML), NOT LLM**

**Key Differences:**
- **LLM (Large Language Model)**: Models like GPT, BERT for text/language (ChatGPT, Claude)
- **ML (Machine Learning)**: Mathematical models for pattern recognition and prediction

**Your Project = ML** because:
- ✅ Works with **numerical time series data** (voltage, current, consumption)
- ✅ Uses **supervised learning** (labeled data: NORMAL vs ALERTE)
- ✅ Performs **anomaly detection** (classification task)
- ✅ Uses **Transformer architecture** (borrowed from NLP but adapted for time series)

---

## 🧠 ALGORITHM USED

### **Primary Algorithm: Transformer Autoencoder**

**Type**: Deep Learning - Unsupervised/Semi-supervised Anomaly Detection

**Architecture Components:**
1. **Autoencoder**: Neural network that learns to compress and reconstruct data
2. **Transformer**: Attention mechanism to capture temporal dependencies
3. **Multi-Head Attention**: Learns relationships between different time steps

**How it Works:**
```
Input Sequence → Encoder → Compressed Representation → Decoder → Reconstructed Output
                    ↓
            If reconstruction error is HIGH → ANOMALY
            If reconstruction error is LOW → NORMAL
```

**Mathematical Foundation:**
- **Loss Function**: Mean Squared Error (MSE)
  ```
  Loss = (1/n) Σ(x_original - x_reconstructed)²
  ```
- **Anomaly Score**: Reconstruction error per sample
- **Decision**: If error > threshold → Anomaly

---

## 📊 COMPLETE ML PIPELINE OVERVIEW

### **STEP 1: DATA COLLECTION**

**Source Data:**
- **File**: `balanced_training_data.csv` (288,000 rows)
- **Features**: 11 raw features per smart meter reading
- **Labels**: NORMAL (70%) vs ALERTE (30%)

**Raw Features:**
```
1. timestamp          - Time of reading
2. meter_id          - Smart meter identifier
3. zone              - Geographic zone (A, B, C, D)
4. type              - Meter type (residential, commercial, industrial)
5. consommation_kw   - Power consumption (kW)
6. tension_v         - Voltage (V)
7. courant_a         - Current (A)
8. facteur_puissance - Power factor
9. frequence_hz      - Frequency (Hz)
10. statut           - Label (NORMAL/ALERTE)
11. anomalies        - Anomaly type
```

---

### **STEP 2: DATA CLEANING**

**File**: `ml_pipeline/data_preprocessing.py`

**Operations:**
1. **Remove Duplicates**
   ```python
   df = df.drop_duplicates()
   ```

2. **Handle Missing Values**
   ```python
   df = df.dropna(subset=['consommation_kw', 'tension_v', 'courant_a'])
   ```

3. **Remove Extreme Outliers** (beyond 5 standard deviations)
   ```python
   for col in ['consommation_kw', 'tension_v', 'courant_a']:
       mean = df[col].mean()
       std = df[col].std()
       df = df[(df[col] >= mean - 5*std) & (df[col] <= mean + 5*std)]
   ```

**Result**: Clean dataset ready for feature engineering

---

### **STEP 3: FEATURE ENGINEERING**

**File**: `ml_pipeline/data_preprocessing.py` → `engineer_features()`

**Created Features (14 total):**

#### **A. Temporal Features** (Capture time patterns)
```python
1. hour_sin = sin(2π × hour / 24)     # Cyclical hour encoding
2. hour_cos = cos(2π × hour / 24)     # Cyclical hour encoding
3. day_of_week = 0-6                   # Monday=0, Sunday=6
4. is_weekend = 1 if weekend else 0    # Weekend indicator
```

#### **B. Categorical Encoding**
```python
5. zone_encoded = LabelEncoder(zone)   # Zone A→0, B→1, etc.
6. type_encoded = LabelEncoder(type)   # residential→0, etc.
```

#### **C. Statistical Features** (Rolling windows)
```python
7. consumption_rolling_mean = rolling_mean(5 timesteps)
8. consumption_rolling_std = rolling_std(5 timesteps)
9. voltage_rolling_mean = rolling_mean(5 timesteps)
```

#### **D. Rate of Change Features**
```python
10. consumption_diff = current - previous
11. consumption_rate_change = (current - previous) / previous
```

#### **E. Original Features**
```python
12. consommation_kw
13. tension_v
14. courant_a
```

**Why These Features?**
- **Temporal**: Anomalies often occur at specific times
- **Statistical**: Detect sudden changes from normal behavior
- **Rate of Change**: Identify rapid spikes/drops

---

### **STEP 4: SEQUENCE CREATION**

**Concept**: Transform individual readings into temporal sequences

**Process:**
```python
# Instead of: [reading1, reading2, reading3, ...]
# Create: [[reading1, reading2, ..., reading20],  # Sequence 1
#          [reading2, reading3, ..., reading21],  # Sequence 2
#          ...]                                    # Sliding window
```

**Parameters:**
- **Sequence Length**: 20 timesteps (20 minutes of data)
- **Sliding Window**: Overlap to create more training samples

**Shape Transformation:**
```
Before: (288000, 14)           # 288k readings × 14 features
After:  (N, 20, 14)            # N sequences × 20 timesteps × 14 features
```

**Why Sequences?**
- Transformers need temporal context
- Anomalies often span multiple timesteps
- Captures patterns over time

---

### **STEP 5: DATA NORMALIZATION**

**Method**: StandardScaler (Z-score normalization)

**Formula:**
```
x_normalized = (x - mean) / std
```

**Process:**
```python
1. Fit scaler on TRAINING data only
2. Transform train, validation, test sets
3. Prevents data leakage
```

**Why Normalize?**
- Features have different scales (voltage: 220V, current: 5A)
- Neural networks train better with normalized inputs
- Prevents features with large values from dominating

---

### **STEP 6: DATA SPLITTING**

**Split Ratios:**
- **Training**: 70% (for learning patterns)
- **Validation**: 15% (for hyperparameter tuning)
- **Test**: 15% (for final evaluation)

**Stratified Split**: Maintains anomaly ratio in all splits

**Example:**
```
Total: 100,000 sequences
├── Train: 70,000 (30% anomalies)
├── Val:   15,000 (30% anomalies)
└── Test:  15,000 (30% anomalies)
```

---

### **STEP 7: MODEL ARCHITECTURE**

**File**: `ml_pipeline/transformer_model.py`

**Architecture Layers:**

```
INPUT (batch, 20, 14)
    ↓
[1] Input Embedding Layer
    Linear(14 → 128)
    ↓
[2] Positional Encoding
    Add position information
    ↓
[3] Transformer Encoder (4 layers)
    ├── Multi-Head Attention (8 heads)
    ├── Layer Normalization
    ├── Feedforward Network (128 → 512 → 128)
    └── Residual Connections
    ↓
[4] Decoder
    ├── Linear(128 → 512)
    ├── GELU Activation
    ├── Dropout(0.1)
    └── Linear(512 → 14)
    ↓
OUTPUT (batch, 20, 14)
```

**Key Components:**

1. **Input Embedding**: Projects 14 features → 128 dimensions
2. **Positional Encoding**: Adds temporal position information
3. **Multi-Head Attention**: 
   - 8 attention heads
   - Each head learns different temporal patterns
   - Captures dependencies between timesteps
4. **Feedforward Network**: Non-linear transformations
5. **Decoder**: Reconstructs original 14 features

**Parameters:**
- Total: ~1.2 million parameters
- Trainable: All parameters

---

### **STEP 8: MODEL TRAINING**

**File**: `ml_pipeline/transformer_model.py` → `TransformerTrainer`

**Training Configuration:**
```python
Optimizer: Adam
Learning Rate: 0.0001
Batch Size: 64
Epochs: 20-50 (with early stopping)
Loss Function: Mean Squared Error (MSE)
Weight Decay: 1e-5 (L2 regularization)
```

**Training Loop:**
```python
for epoch in range(epochs):
    # 1. Forward pass
    reconstructed = model(input_data)
    
    # 2. Calculate loss
    loss = MSE(reconstructed, input_data)
    
    # 3. Backward pass
    loss.backward()
    
    # 4. Update weights
    optimizer.step()
    
    # 5. Validate
    val_loss = validate(val_data)
    
    # 6. Early stopping
    if val_loss < best_loss:
        save_model()
    else:
        patience_counter += 1
```

**Early Stopping:**
- Monitors validation loss
- Stops if no improvement for 10 epochs
- Prevents overfitting

---

### **STEP 9: ANOMALY DETECTION**

**File**: `ml_pipeline/enhanced_anomaly_detection.py`

**Multi-Criteria Detection System:**

#### **Criterion 1: ML Reconstruction Error (20%)**
```python
error = mean((input - reconstructed)²)
if error > threshold_95th_percentile:
    anomaly_score += 0.20
```

#### **Criterion 2: Voltage Anomaly (20%)**
```python
if voltage < 207V or voltage > 253V:  # IEEE 1547 standard
    anomaly_score += 0.20
```

#### **Criterion 3: Consumption Anomaly (15%)**
```python
if consumption > mean + 3×std:  # Statistical outlier
    anomaly_score += 0.15
```

#### **Criterion 4: Power Factor (15%)**
```python
if power_factor < 0.85:  # IEEE standard
    anomaly_score += 0.15
```

#### **Criterion 5: Frequency Deviation (15%)**
```python
if frequency < 59.5Hz or frequency > 60.5Hz:
    anomaly_score += 0.15
```

#### **Criterion 6: Temporal Patterns (10%)**
```python
if unusual_time_pattern:  # Night spike, etc.
    anomaly_score += 0.10
```

#### **Criterion 7: Rate of Change (5%)**
```python
if abs(consumption_change) > threshold:
    anomaly_score += 0.05
```

**Final Decision:**
```python
if total_anomaly_score > 0.2:  # 20% threshold
    prediction = ANOMALY
else:
    prediction = NORMAL
```

---

### **STEP 10: MODEL VALIDATION**

**File**: `ml_pipeline/evaluation.py`

**Metrics Calculated:**

1. **Accuracy**: (TP + TN) / Total
   ```
   Correct predictions / All predictions
   ```

2. **Precision**: TP / (TP + FP)
   ```
   Of predicted anomalies, how many are real?
   ```

3. **Recall**: TP / (TP + FN)
   ```
   Of real anomalies, how many did we detect?
   ```

4. **F1-Score**: 2 × (Precision × Recall) / (Precision + Recall)
   ```
   Harmonic mean of precision and recall
   ```

5. **ROC-AUC**: Area under ROC curve
   ```
   Measures discrimination ability
   ```

**Confusion Matrix:**
```
                Predicted
              NORMAL  ANOMALY
Actual NORMAL   TN      FP
       ANOMALY  FN      TP
```

**Current Performance:**
```
Accuracy:  ~75%
Precision: ~99.86%
Recall:    ~15.22%
F1-Score:  ~26.42%
```

---

## 🔄 PRE-TRAINED MODEL APPROACH

**File**: `ml_pipeline/pretrained_transformer.py`

**What is Transfer Learning?**
- Use knowledge from pre-trained models
- Fine-tune on your specific task
- Faster training, better performance

**Architecture:**
```
BERT-style Encoder (Pre-trained)
    ↓
Fine-tuning on Smart Grid Data
    ↓
Custom Decoder for Reconstruction
```

**Advantages:**
1. **Better Feature Learning**: Pre-trained attention mechanisms
2. **Faster Convergence**: Starts with good weights
3. **Improved Performance**: Expected 30-45% recall (vs 15%)

**Key Difference from Scratch:**
```
From Scratch:
- Random initialization
- Learn everything from your data
- Slower, needs more data

Pre-trained:
- BERT-style initialization
- Transfer learned patterns
- Faster, better with less data
```

---

## 📈 COMPLETE PIPELINE FLOW

```
┌─────────────────────────────────────────────────────────────┐
│ 1. DATA COLLECTION                                          │
│    balanced_training_data.csv (288,000 rows)                │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. DATA CLEANING                                            │
│    - Remove duplicates                                      │
│    - Handle missing values                                  │
│    - Remove outliers (>5σ)                                  │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. FEATURE ENGINEERING                                      │
│    14 features: temporal, statistical, rate-of-change       │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. SEQUENCE CREATION                                        │
│    Sliding window: 20 timesteps per sequence                │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. NORMALIZATION                                            │
│    StandardScaler: (x - μ) / σ                              │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. TRAIN/VAL/TEST SPLIT                                     │
│    70% / 15% / 15% (stratified)                             │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ 7. MODEL TRAINING                                           │
│    Transformer Autoencoder (1.2M parameters)                │
│    - Input Embedding (14 → 128)                             │
│    - Positional Encoding                                    │
│    - 4 Transformer Encoder Layers                           │
│    - 8 Multi-Head Attention                                 │
│    - Decoder (128 → 14)                                     │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ 8. ANOMALY DETECTION                                        │
│    Multi-Criteria System (7 criteria)                       │
│    - ML Reconstruction (20%)                                │
│    - Voltage (20%)                                          │
│    - Consumption (15%)                                      │
│    - Power Factor (15%)                                     │
│    - Frequency (15%)                                        │
│    - Temporal (10%)                                         │
│    - Rate of Change (5%)                                    │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────────┐
│ 9. VALIDATION & EVALUATION                                  │
│    Metrics: Accuracy, Precision, Recall, F1, ROC-AUC        │
│    Visualizations: Confusion Matrix, ROC Curve              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 SUMMARY

### **Algorithm Type**: Machine Learning (ML)
- **Category**: Deep Learning - Anomaly Detection
- **Architecture**: Transformer Autoencoder
- **Learning Type**: Semi-supervised

### **Pipeline Stages**:
1. ✅ **Data Collection**: 288k balanced samples
2. ✅ **Data Cleaning**: Remove noise and outliers
3. ✅ **Feature Engineering**: 14 engineered features
4. ✅ **Sequence Creation**: 20-timestep windows
5. ✅ **Normalization**: StandardScaler
6. ✅ **Model Training**: Transformer with 1.2M parameters
7. ✅ **Anomaly Detection**: 7-criteria weighted system
8. ✅ **Validation**: Comprehensive metrics

### **Key Innovations**:
- ✨ Transformer architecture for time series
- ✨ Multi-criteria detection (not just ML)
- ✨ IEEE standard compliance
- ✨ Transfer learning with pre-trained models

### **Performance**:
- Current: 15% recall, 99% precision
- Target (pre-trained): 30-45% recall, 95%+ precision

---

## 📚 ACADEMIC REFERENCES

**Algorithms Used:**
1. **Transformer**: Vaswani et al. (2017) "Attention Is All You Need"
2. **Autoencoder**: Hinton & Salakhutdinov (2006)
3. **Transfer Learning**: Pan & Yang (2010)
4. **Anomaly Detection**: Chandola et al. (2009)

**Standards:**
- IEEE 1547: Grid interconnection standards
- IEEE C37.118: Synchrophasor measurements

---

**Generated**: May 14, 2026
**Project**: Smart Grid Anomaly Detection
**Model**: Transformer Autoencoder with Multi-Criteria Detection
