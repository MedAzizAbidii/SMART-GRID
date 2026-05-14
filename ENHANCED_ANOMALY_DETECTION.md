# 🔍 Enhanced Multi-Criteria Anomaly Detection for Smart Grids

## Overview

The enhanced anomaly detection system uses **7 different criteria** to detect anomalies in smart grid data, going beyond simple ML-based reconstruction error to include domain-specific rules based on IEEE standards and smart grid best practices.

---

## 🎯 Detection Criteria

### 1. **ML Reconstruction Error** (Weight: 20%)
- Uses Transformer Autoencoder to learn normal patterns
- Detects deviations from learned behavior
- **Threshold**: 95th percentile of validation errors

### 2. **Voltage Anomalies** (Weight: 20%)
Based on IEEE voltage standards:
- **Normal range**: 207V - 253V (±10% of 230V nominal)
- **Warning levels**:
  - Under-voltage: < 207V (score: 0.7)
  - Over-voltage: > 253V (score: 0.7)
- **Critical levels**:
  - Critical under-voltage: < 200V (score: 1.0)
  - Critical over-voltage: > 260V (score: 1.0)
- **Deviation detection**: > 5% from nominal voltage

**Detects**: Voltage sags, swells, under/over voltage conditions

### 3. **Consumption Anomalies** (Weight: 15%)
- **Consumption spikes**: > 3x normal consumption (score: 0.9)
- **High consumption**: > 95th percentile (score: 0.6)
- **Unexpected zero consumption**:
  - Industrial: 6 AM - 10 PM (score: 0.8)
  - Commercial: 8 AM - 6 PM (score: 0.7)
- **Statistical outliers**: > 3 standard deviations from mean

**Detects**: Unusual consumption patterns, meter tampering, equipment failures

### 4. **Power Factor Anomalies** (Weight: 15%)
- **Low power factor**: < 0.85 (IEEE standard)
- **Reactive power issues**: Excessive reactive power consumption
- **Impossible power factor**: Active power > Apparent power

**Detects**: Inefficient equipment, power quality issues, measurement errors

### 5. **Frequency Anomalies** (Weight: 15%)
Based on grid frequency standards:
- **Normal range**: 59.5 Hz - 60.5 Hz (±0.5 Hz tolerance)
- **Low frequency**: < 59.5 Hz (grid underload)
- **High frequency**: > 60.5 Hz (grid overload)

**Detects**: Grid instability, generation-load imbalance

### 6. **Temporal Anomalies** (Weight: 10%)
Pattern-based detection by consumer type:
- **Residential**:
  - High consumption at night (0-5 AM): score 0.6
- **Commercial**:
  - Weekend activity: score 0.5
  - Off-hours activity (0-6 AM, 8-11 PM): score 0.5
- **Industrial**:
  - Unexpected shutdown during work hours (8 AM - 6 PM): score 0.6

**Detects**: Unusual usage patterns, unauthorized access, scheduling issues

### 7. **Rate of Change Anomalies** (Weight: 5%)
- **Sudden changes**: > 5 kW per timestep
- **Rapid fluctuations**: > 200% change rate

**Detects**: Equipment switching, sudden load changes, measurement glitches

---

## 📊 Scoring System

### Weighted Total Score
```
Total Score = 
  0.20 × Reconstruction Score +
  0.20 × Voltage Score +
  0.15 × Consumption Score +
  0.15 × Power Factor Score +
  0.15 × Frequency Score +
  0.10 × Temporal Score +
  0.05 × Rate Change Score
```

### Anomaly Classification
- **Total Score > 0.5**: Classified as anomaly
- **Total Score ≤ 0.5**: Classified as normal
- **Anomaly Type**: Determined by highest-scoring criterion
- **Confidence**: Score of the dominant criterion

---

## 🔧 Configuration

### Adjustable Weights
You can modify the weights in `enhanced_anomaly_detection.py`:

```python
self.weights = {
    'reconstruction': 0.20,  # ML-based detection
    'voltage': 0.20,         # Voltage standards
    'consumption': 0.15,     # Consumption patterns
    'power_factor': 0.15,    # Power quality
    'frequency': 0.15,       # Grid stability
    'temporal': 0.10,        # Time-based patterns
    'rate_change': 0.05      # Sudden changes
}
```

### Adjustable Thresholds
```python
self.thresholds = {
    'voltage_min': 207.0,                    # Minimum acceptable voltage
    'voltage_max': 253.0,                    # Maximum acceptable voltage
    'voltage_critical_min': 200.0,           # Critical under-voltage
    'voltage_critical_max': 260.0,           # Critical over-voltage
    'frequency_min': 59.5,                   # Minimum frequency
    'frequency_max': 60.5,                   # Maximum frequency
    'consumption_spike_factor': 3.0,         # Spike = 3x normal
    'rate_change_threshold': 5.0,            # kW/timestep
}
```

---

## 📈 Output Files

### 1. Detailed Anomaly Results
**File**: `ml_pipeline/results/detailed_anomalies.csv`

Contains for each sample:
- `is_anomaly`: Binary flag (True/False)
- `anomaly_type`: Type of anomaly detected
- `total_score`: Weighted total score
- `confidence`: Confidence in the prediction
- Individual scores for each criterion

### 2. Enhanced Evaluation Report
**File**: `ml_pipeline/results/enhanced_evaluation_report.txt`

Contains:
- Performance breakdown by anomaly type
- Detection criterion contribution analysis
- Summary statistics

### 3. Visualizations
**Directory**: `ml_pipeline/plots/`

- `criterion_heatmap.png`: Heatmap showing which criteria triggered for each anomaly
- `anomaly_type_distribution.png`: Bar chart of detected anomaly types
- `confidence_distribution.png`: Confidence scores for TP/FP/TN/FN
- Standard plots: confusion matrix, ROC curve, error distribution

---

## 🚀 Usage

### Run Enhanced Detection
```bash
py -3.10-64 run_ml_pipeline_fast.py
```

### Customize Detection
1. **Adjust weights**: Edit `ml_pipeline/enhanced_anomaly_detection.py` → `self.weights`
2. **Adjust thresholds**: Edit `ml_pipeline/enhanced_anomaly_detection.py` → `self.thresholds`
3. **Add new criteria**: Implement new `detect_*_anomaly()` method
4. **Re-run pipeline**: `py -3.10-64 run_ml_pipeline_fast.py`

---

## 📊 Expected Improvements

### Previous Model (Basic Detection)
- **Accuracy**: 23.75%
- **Precision**: 93.64%
- **Recall**: 5.48%
- **F1-Score**: 10.36%
- **Issue**: Too conservative, missed many anomalies

### Enhanced Model (Multi-Criteria)
Expected improvements:
- ✅ **Higher Recall**: More anomalies detected through multiple criteria
- ✅ **Better Balance**: F1-score improvement through balanced precision/recall
- ✅ **Explainability**: Know WHY each anomaly was detected
- ✅ **Domain Relevance**: Detection based on smart grid standards
- ⚠️ **Possible Trade-off**: Slightly lower precision (more false positives)

---

## 🔍 Anomaly Type Examples

### Voltage Anomaly
```
Sample #1234
- Voltage: 195V (Critical under-voltage)
- Voltage Score: 1.0
- Total Score: 0.72
- Type: voltage
- Confidence: 1.0
```

### Consumption Anomaly
```
Sample #5678
- Consumption: 45 kW (Normal: 12 kW)
- Consumption Score: 0.9 (3.75x spike)
- Total Score: 0.68
- Type: consumption
- Confidence: 0.9
```

### Temporal Anomaly
```
Sample #9012
- Type: Commercial
- Time: 2:30 AM Sunday
- Consumption: 18 kW
- Temporal Score: 0.5
- Total Score: 0.55
- Type: temporal
- Confidence: 0.5
```

---

## 🎓 References

### Standards
- **IEEE 1159-2019**: Recommended Practice for Monitoring Electric Power Quality
- **IEEE C84.1-2020**: Electric Power Systems and Equipment—Voltage Ratings
- **IEC 61000-4-30**: Power quality measurement methods

### Smart Grid Best Practices
- Voltage tolerance: ±10% of nominal
- Frequency tolerance: ±0.5 Hz
- Power factor minimum: 0.85
- Consumer type usage patterns

---

## 💡 Tips for Optimization

### If Too Many False Positives
1. Increase anomaly threshold from 0.5 to 0.6 or 0.7
2. Reduce weights for sensitive criteria (temporal, rate_change)
3. Tighten thresholds (e.g., voltage_min from 207V to 200V)

### If Missing Anomalies (Low Recall)
1. Decrease anomaly threshold from 0.5 to 0.4
2. Increase weights for important criteria
3. Loosen thresholds to catch more edge cases

### For Specific Use Cases
- **Focus on voltage quality**: Increase voltage weight to 0.30
- **Focus on consumption fraud**: Increase consumption weight to 0.25
- **Focus on grid stability**: Increase frequency weight to 0.25

---

## 📞 Next Steps

1. ✅ **Run the enhanced pipeline**: `py -3.10-64 run_ml_pipeline_fast.py`
2. 📊 **Review results**: Check `ml_pipeline/results/` and `ml_pipeline/plots/`
3. 🔧 **Tune parameters**: Adjust weights and thresholds based on results
4. 🔄 **Iterate**: Re-run and compare performance
5. 🚀 **Deploy**: Use the best configuration for production

---

**Created**: May 11, 2026  
**Version**: 1.0  
**Author**: Kiro AI Assistant
