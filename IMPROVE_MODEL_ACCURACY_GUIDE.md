# Complete Guide to Improve Model Accuracy

## 🎯 CURRENT PROBLEM

**Your Model Performance:**
- Accuracy: 22.85%
- Precision: 82.42% ✅ (Good!)
- Recall: 5.08% ❌ (Very Low!)
- F1-Score: 9.56% ❌ (Very Low!)

**Root Cause:** **IMBALANCED DATA**
- Too many NORMAL samples (~90-95%)
- Too few ANOMALY samples (~5-10%)
- Model learned to be too conservative

---

## 🚀 SOLUTION: 5-STEP IMPROVEMENT PLAN

### STEP 1: Generate Balanced Training Data (MOST IMPORTANT!)

#### Why This Matters:
Your model needs to see MORE anomaly examples to learn what anomalies look like!

#### How to Do It:

**Option A: Modify Simulator to Generate More Anomalies**

I'll create a special data generation script for you:

```python
# File: generate_balanced_data.py
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

def generate_balanced_smart_meter_data(
    num_meters=100,
    hours=24,
    anomaly_rate=0.30  # 30% anomalies!
):
    """Generate balanced dataset with 30% anomalies"""
    
    data = []
    start_time = datetime.now()
    
    zones = ['Zone A', 'Zone B', 'Zone C', 'Zone D']
    types = ['residentiel', 'commercial', 'industriel']
    
    # Generate readings every minute
    for minute in range(hours * 60):
        timestamp = start_time + timedelta(minutes=minute)
        
        for meter_id in range(1, num_meters + 1):
            meter_name = f"SM_{meter_id:04d}"
            zone = random.choice(zones)
            meter_type = random.choice(types)
            
            # Base consumption by type
            if meter_type == 'residentiel':
                base_consumption = random.uniform(0.5, 5.0)
            elif meter_type == 'commercial':
                base_consumption = random.uniform(3.0, 12.0)
            else:  # industriel
                base_consumption = random.uniform(10.0, 40.0)
            
            # Normal voltage
            voltage = random.uniform(220, 240)
            
            # Decide if this is an anomaly
            is_anomaly = random.random() < anomaly_rate
            
            if is_anomaly:
                # Generate different types of anomalies
                anomaly_type = random.choice([
                    'voltage_high', 'voltage_low', 
                    'consumption_spike', 'consumption_drop',
                    'power_factor_low', 'frequency_deviation'
                ])
                
                if anomaly_type == 'voltage_high':
                    voltage = random.uniform(253, 270)  # Over IEEE limit
                    anomalies = 'voltage_high'
                    
                elif anomaly_type == 'voltage_low':
                    voltage = random.uniform(180, 207)  # Under IEEE limit
                    anomalies = 'voltage_low'
                    
                elif anomaly_type == 'consumption_spike':
                    base_consumption *= random.uniform(3.0, 8.0)  # 3-8x spike
                    anomalies = 'consumption_spike'
                    
                elif anomaly_type == 'consumption_drop':
                    base_consumption *= random.uniform(0.05, 0.2)  # Drop to 5-20%
                    anomalies = 'consumption_drop'
                    
                elif anomaly_type == 'power_factor_low':
                    power_factor = random.uniform(0.3, 0.7)  # Low power factor
                    anomalies = 'power_factor_low'
                    
                else:  # frequency_deviation
                    frequency = random.uniform(58.0, 59.4)  # Out of range
                    anomalies = 'frequency_deviation'
                
                statut = 'ALERTE'
            else:
                anomalies = 'none'
                statut = 'NORMAL'
                power_factor = random.uniform(0.85, 0.98)
                frequency = random.uniform(59.5, 60.5)
            
            # Calculate current
            current = (base_consumption * 1000) / (voltage * power_factor)
            
            data.append({
                'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'meter_id': meter_name,
                'zone': zone,
                'type': meter_type,
                'consommation_kw': round(base_consumption, 3),
                'tension_v': round(voltage, 2),
                'courant_a': round(current, 3),
                'facteur_puissance': round(power_factor, 3),
                'frequence_hz': round(frequency, 2),
                'statut': statut,
                'anomalies': anomalies
            })
    
    return pd.DataFrame(data)

# Generate balanced dataset
print("Generating balanced training data...")
df = generate_balanced_smart_meter_data(
    num_meters=100,
    hours=48,  # 48 hours of data
    anomaly_rate=0.30  # 30% anomalies
)

# Save to file
df.to_csv('balanced_training_data.csv', index=False)

print(f"✅ Generated {len(df):,} rows")
print(f"   Normal: {len(df[df['statut']=='NORMAL']):,} ({len(df[df['statut']=='NORMAL'])/len(df)*100:.1f}%)")
print(f"   Anomalies: {len(df[df['statut']=='ALERTE']):,} ({len(df[df['statut']=='ALERTE'])/len(df)*100:.1f}%)")
print(f"\nSaved to: balanced_training_data.csv")
```

**Run this script:**
```bash
py -3.10-64 generate_balanced_data.py
```

This will create a file with **30% anomalies** instead of your current ~5-10%!

---

### STEP 2: Retrain Model with Balanced Data

After generating balanced data, retrain your model:

**Modify `run_ml_pipeline_fast.py` to use the new data:**

```python
# Change this line:
# data_file = 'donnees_smart_meters.csv'
# To:
data_file = 'balanced_training_data.csv'
```

**Then run:**
```bash
py -3.10-64 run_ml_pipeline_fast.py
```

**Expected Improvements:**
- Accuracy: 22% → **60-75%**
- Recall: 5% → **40-60%**
- F1-Score: 9% → **45-65%**

---

### STEP 3: Use Class Weights in Training

This tells the model to pay MORE attention to anomaly samples.

**Modify `ml_pipeline/transformer_model.py`:**

Find the training loop and add weighted loss:

```python
# In the train_epoch function, modify the loss calculation:

def train_epoch(model, train_loader, criterion, optimizer, device):
    model.train()
    total_loss = 0
    
    for batch in train_loader:
        data = batch['data'].to(device)
        labels = batch['label'].to(device)  # 0=normal, 1=anomaly
        
        optimizer.zero_grad()
        reconstructed = model(data)
        
        # Calculate reconstruction loss
        loss = criterion(reconstructed, data)
        
        # Apply class weights: Give 10x more importance to anomalies
        weights = torch.where(labels == 1, 
                             torch.tensor(10.0).to(device),  # Anomaly weight
                             torch.tensor(1.0).to(device))   # Normal weight
        
        weighted_loss = (loss * weights.unsqueeze(1)).mean()
        
        weighted_loss.backward()
        optimizer.step()
        
        total_loss += weighted_loss.item()
    
    return total_loss / len(train_loader)
```

**Expected Improvement:**
- Model will focus more on learning anomaly patterns
- Recall: +10-20%
- F1-Score: +15-25%

---

### STEP 4: Adjust Detection Threshold

Lower the threshold to catch more anomalies:

**In `smart_meters_simulator.py`:**

```python
# Current:
ENHANCED_DETECTION_THRESHOLD = 0.2

# Change to:
ENHANCED_DETECTION_THRESHOLD = 0.1  # More sensitive
# Or even:
ENHANCED_DETECTION_THRESHOLD = 0.05  # Very sensitive
```

**Trade-off:**
- Lower threshold = More anomalies detected (higher recall)
- But also = More false alarms (lower precision)

**Recommended:** Start with 0.1, then adjust based on results.

---

### STEP 5: Ensemble Multiple Models

Train multiple models and combine their predictions:

```python
# Train 3 different models:
# 1. Transformer (current)
# 2. Autoencoder
# 3. Isolation Forest

# Combine predictions:
final_prediction = (
    transformer_score * 0.5 +
    autoencoder_score * 0.3 +
    isolation_forest_score * 0.2
)
```

**Expected Improvement:**
- More robust detection
- Better generalization
- Accuracy: +5-10%

---

## 📊 COMPLETE WORKFLOW TO ACHIEVE GOOD ACCURACY

### Phase 1: Data Preparation (1-2 hours)

1. **Generate Balanced Data**
   ```bash
   py -3.10-64 generate_balanced_data.py
   ```
   - Creates `balanced_training_data.csv`
   - 30% anomalies, 70% normal
   - 288,000 rows (100 meters × 48 hours × 60 minutes)

2. **Verify Data Quality**
   ```bash
   py -3.10-64 -c "import pandas as pd; df=pd.read_csv('balanced_training_data.csv'); print(df['statut'].value_counts())"
   ```

### Phase 2: Model Training (20-30 minutes)

3. **Train with Balanced Data**
   ```bash
   py -3.10-64 run_ml_pipeline_fast.py
   ```
   - Uses balanced data
   - Trains for 50 epochs
   - Saves best model

4. **Check Results**
   - Look at `ml_pipeline/results/enhanced_evaluation_report.txt`
   - Target: Accuracy > 60%, Recall > 40%, F1 > 45%

### Phase 3: Fine-Tuning (30 minutes)

5. **Adjust Threshold**
   - Edit `smart_meters_simulator.py`
   - Set `ENHANCED_DETECTION_THRESHOLD = 0.1`

6. **Test Detection**
   ```bash
   py -3.10-64 smart_meters_simulator.py
   ```
   - Run for 10 minutes
   - Check detection rate
   - Should see 25-35% anomalies detected

### Phase 4: Validation (1 hour)

7. **Run Long Test**
   - Run simulator for 1 hour
   - Monitor detection statistics
   - Verify false alarm rate is acceptable

8. **Adjust if Needed**
   - Too many false alarms? Increase threshold to 0.15
   - Too few detections? Decrease threshold to 0.05

---

## 🎯 EXPECTED FINAL RESULTS

After following all steps:

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **Accuracy** | 22.85% | **65-75%** | +42-52% |
| **Precision** | 82.42% | **70-80%** | -2 to -12% (acceptable) |
| **Recall** | 5.08% | **45-60%** | +40-55% |
| **F1-Score** | 9.56% | **50-65%** | +40-55% |
| **ROC-AUC** | 68.29% | **80-90%** | +12-22% |

---

## 🔧 QUICK START: BEST APPROACH

If you want the **fastest improvement** with **least effort**:

### Option A: Quick Fix (5 minutes)
1. Lower threshold to 0.1
2. Restart simulator
3. **Expected**: Recall 15-25%, F1 20-30%

### Option B: Balanced Data (2 hours)
1. Generate balanced data (30% anomalies)
2. Retrain model
3. Lower threshold to 0.1
4. **Expected**: Recall 45-60%, F1 50-65%

### Option C: Full Optimization (4 hours)
1. Generate balanced data
2. Add class weights to training
3. Retrain model
4. Fine-tune threshold
5. **Expected**: Recall 55-70%, F1 60-75%

---

## 📝 IMPLEMENTATION CHECKLIST

- [ ] **Step 1**: Create `generate_balanced_data.py` script
- [ ] **Step 2**: Run script to generate balanced data
- [ ] **Step 3**: Verify data has 30% anomalies
- [ ] **Step 4**: Modify training script to use new data
- [ ] **Step 5**: Retrain model (20-30 minutes)
- [ ] **Step 6**: Check new accuracy metrics
- [ ] **Step 7**: Lower detection threshold to 0.1
- [ ] **Step 8**: Test with simulator
- [ ] **Step 9**: Fine-tune threshold based on results
- [ ] **Step 10**: Deploy to production

---

## 🎓 WHY THIS WORKS

### Problem: Imbalanced Data
- Model sees 95% NORMAL, 5% ANOMALY
- Learns: "Just predict NORMAL most of the time"
- Result: High precision, low recall

### Solution: Balanced Data
- Model sees 70% NORMAL, 30% ANOMALY
- Learns: "Anomalies are common, I need to detect them"
- Result: Balanced precision and recall

### Additional Boost: Class Weights
- Tell model: "Anomalies are 10x more important"
- Model focuses more on learning anomaly patterns
- Result: Even better recall

### Fine-Tuning: Threshold Adjustment
- Lower threshold = More sensitive
- Catches more anomalies
- Result: Higher recall, slightly lower precision

---

## 🚀 READY TO START?

I can create the `generate_balanced_data.py` script for you right now!

Just say "yes" and I'll:
1. Create the script
2. Run it to generate balanced data
3. Modify the training script
4. Start retraining your model

**Estimated time to better accuracy: 2-3 hours**

---

**Last Updated**: May 11, 2026 5:10 PM
