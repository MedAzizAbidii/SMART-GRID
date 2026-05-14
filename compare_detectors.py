"""
Compare Basic vs Enhanced Anomaly Detection
Quick comparison script to show the differences
"""
import pandas as pd
import numpy as np

print("=" * 80)
print("🔍 BASIC vs ENHANCED ANOMALY DETECTION COMPARISON")
print("=" * 80)

print("\n" + "=" * 80)
print("BASIC DETECTOR (Previous Model)")
print("=" * 80)
print("""
Detection Method:
  • Single criterion: ML Reconstruction Error only
  • Threshold: 95th percentile of validation errors
  • Binary decision: Error > Threshold = Anomaly

Advantages:
  ✅ Simple and fast
  ✅ Learns from data patterns
  ✅ No manual rule definition needed

Disadvantages:
  ❌ Black box - no explanation WHY anomaly detected
  ❌ May miss domain-specific anomalies
  ❌ No consideration of smart grid standards
  ❌ Single point of failure

Previous Results:
  • Accuracy: 23.75%
  • Precision: 93.64% (very few false alarms)
  • Recall: 5.48% (missed 94.52% of anomalies!)
  • F1-Score: 10.36%
  • Behavior: Too conservative, high precision but very low recall
""")

print("\n" + "=" * 80)
print("ENHANCED DETECTOR (New Multi-Criteria Model)")
print("=" * 80)
print("""
Detection Method:
  • 7 criteria with weighted scoring:
    1. ML Reconstruction Error (20%)
    2. Voltage Anomalies (20%) - IEEE standards
    3. Consumption Anomalies (15%) - Pattern-based
    4. Power Factor Anomalies (15%) - Power quality
    5. Frequency Anomalies (15%) - Grid stability
    6. Temporal Anomalies (10%) - Time patterns
    7. Rate of Change (5%) - Sudden changes
  
  • Weighted total score > 0.5 = Anomaly
  • Anomaly type = Highest scoring criterion
  • Confidence = Score of dominant criterion

Advantages:
  ✅ Explainable - know WHY each anomaly detected
  ✅ Domain-specific rules (IEEE standards)
  ✅ Multiple detection paths (redundancy)
  ✅ Configurable weights and thresholds
  ✅ Detailed breakdown by anomaly type
  ✅ Better recall through multiple criteria

Expected Improvements:
  📈 Higher Recall: Detect more anomalies through multiple criteria
  📈 Better F1-Score: More balanced precision/recall
  📈 Explainability: Detailed anomaly type classification
  📈 Domain Relevance: Based on smart grid standards
  ⚠️  Possible Trade-off: Slightly lower precision (more false positives)
""")

print("\n" + "=" * 80)
print("DETECTION CRITERIA DETAILS")
print("=" * 80)

criteria_table = pd.DataFrame([
    {
        'Criterion': 'ML Reconstruction',
        'Weight': '20%',
        'Detects': 'Deviations from learned patterns',
        'Example': 'Unusual combination of features'
    },
    {
        'Criterion': 'Voltage',
        'Weight': '20%',
        'Detects': 'Under/over voltage (IEEE standards)',
        'Example': 'Voltage = 195V (< 207V normal)'
    },
    {
        'Criterion': 'Consumption',
        'Weight': '15%',
        'Detects': 'Spikes, zero consumption, outliers',
        'Example': '45 kW when normal is 12 kW'
    },
    {
        'Criterion': 'Power Factor',
        'Weight': '15%',
        'Detects': 'Low PF (<0.85), reactive power',
        'Example': 'PF = 0.65 (inefficient equipment)'
    },
    {
        'Criterion': 'Frequency',
        'Weight': '15%',
        'Detects': 'Grid instability (±0.5 Hz)',
        'Example': 'Frequency = 58.9 Hz (< 59.5 Hz)'
    },
    {
        'Criterion': 'Temporal',
        'Weight': '10%',
        'Detects': 'Unusual time patterns',
        'Example': 'Commercial high usage at 3 AM'
    },
    {
        'Criterion': 'Rate of Change',
        'Weight': '5%',
        'Detects': 'Sudden spikes/drops',
        'Example': 'Jump from 10 kW to 40 kW instantly'
    }
])

print(criteria_table.to_string(index=False))

print("\n" + "=" * 80)
print("EXAMPLE DETECTION SCENARIOS")
print("=" * 80)

scenarios = [
    {
        'Scenario': 'Voltage Sag',
        'Basic': '❌ May miss (if pattern is common)',
        'Enhanced': '✅ Detected by voltage criterion (IEEE standard)'
    },
    {
        'Scenario': 'Consumption Fraud',
        'Basic': '❌ May miss (if tampering is subtle)',
        'Enhanced': '✅ Detected by consumption + temporal criteria'
    },
    {
        'Scenario': 'Power Quality Issue',
        'Basic': '❌ Not detected (no power factor check)',
        'Enhanced': '✅ Detected by power factor criterion'
    },
    {
        'Scenario': 'Grid Instability',
        'Basic': '❌ Not detected (no frequency check)',
        'Enhanced': '✅ Detected by frequency criterion'
    },
    {
        'Scenario': 'Novel Attack Pattern',
        'Basic': '✅ May detect (ML learns patterns)',
        'Enhanced': '✅ Detected by ML + rule-based criteria'
    },
    {
        'Scenario': 'Off-Hours Usage',
        'Basic': '❌ Not detected (no time awareness)',
        'Enhanced': '✅ Detected by temporal criterion'
    }
]

scenarios_df = pd.DataFrame(scenarios)
print(scenarios_df.to_string(index=False))

print("\n" + "=" * 80)
print("OUTPUT COMPARISON")
print("=" * 80)

outputs = pd.DataFrame([
    {
        'Output': 'Binary Prediction',
        'Basic': '✅ Yes (0 or 1)',
        'Enhanced': '✅ Yes (0 or 1)'
    },
    {
        'Output': 'Anomaly Score',
        'Basic': '✅ Reconstruction error',
        'Enhanced': '✅ Weighted total score'
    },
    {
        'Output': 'Anomaly Type',
        'Basic': '❌ No',
        'Enhanced': '✅ Yes (7 types)'
    },
    {
        'Output': 'Confidence',
        'Basic': '❌ No',
        'Enhanced': '✅ Yes (0-1 score)'
    },
    {
        'Output': 'Criterion Breakdown',
        'Basic': '❌ No',
        'Enhanced': '✅ Yes (all 7 scores)'
    },
    {
        'Output': 'Explainability',
        'Basic': '❌ Black box',
        'Enhanced': '✅ Full explanation'
    }
])

print(outputs.to_string(index=False))

print("\n" + "=" * 80)
print("WHEN TO USE EACH")
print("=" * 80)

print("""
Use BASIC Detector when:
  • You need maximum speed
  • You want to minimize false positives at all costs
  • You don't need to explain WHY anomalies occur
  • You have limited domain knowledge
  • You want pure data-driven detection

Use ENHANCED Detector when:
  • You need to explain anomalies to stakeholders
  • You want to comply with industry standards (IEEE)
  • You need better recall (detect more anomalies)
  • You have domain expertise to tune criteria
  • You want detailed anomaly classification
  • You need to detect specific types of issues
  
Recommendation: Use ENHANCED for production smart grid systems
""")

print("\n" + "=" * 80)
print("🚀 NEXT STEPS")
print("=" * 80)

print("""
1. Run the enhanced pipeline:
   py -3.10-64 run_ml_pipeline_fast.py

2. Compare results with previous run:
   - Check ml_pipeline/results/enhanced_evaluation_report.txt
   - Review ml_pipeline/plots/anomaly_type_distribution.png
   - Examine ml_pipeline/results/detailed_anomalies.csv

3. Tune parameters if needed:
   - Edit ml_pipeline/enhanced_anomaly_detection.py
   - Adjust weights in self.weights dictionary
   - Adjust thresholds in self.thresholds dictionary

4. Re-run and iterate until satisfied with performance
""")

print("=" * 80)
