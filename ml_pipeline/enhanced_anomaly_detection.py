"""
Enhanced Anomaly Detection for Smart Grids
Multiple criteria and domain-specific rules
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class AnomalyScore:
    """Container for anomaly scores from different detectors"""
    reconstruction_error: float = 0.0
    voltage_anomaly: float = 0.0
    consumption_anomaly: float = 0.0
    power_factor_anomaly: float = 0.0
    frequency_anomaly: float = 0.0
    temporal_anomaly: float = 0.0
    rate_change_anomaly: float = 0.0
    total_score: float = 0.0
    is_anomaly: bool = False
    anomaly_type: str = "normal"
    confidence: float = 0.0


class EnhancedSmartGridAnomalyDetector:
    """
    Multi-criteria anomaly detection for smart grids
    
    Detection Criteria:
    1. Voltage anomalies (under/over voltage)
    2. Consumption anomalies (unusual patterns)
    3. Power factor anomalies (reactive power issues)
    4. Frequency deviations (grid instability)
    5. Temporal anomalies (time-based patterns)
    6. Rate of change anomalies (sudden spikes)
    7. Reconstruction error (ML-based)
    """
    
    def __init__(self):
        # Smart grid standards (IEEE, IEC)
        self.VOLTAGE_NOMINAL = 230.0  # V
        self.VOLTAGE_TOLERANCE = 0.10  # ±10%
        self.FREQUENCY_NOMINAL = 60.0  # Hz
        self.FREQUENCY_TOLERANCE = 0.5  # ±0.5 Hz
        self.POWER_FACTOR_MIN = 0.85  # Minimum acceptable
        
        # Thresholds
        self.thresholds = {
            'voltage_min': self.VOLTAGE_NOMINAL * (1 - self.VOLTAGE_TOLERANCE),  # 207V
            'voltage_max': self.VOLTAGE_NOMINAL * (1 + self.VOLTAGE_TOLERANCE),  # 253V
            'voltage_critical_min': 200.0,  # Critical under-voltage
            'voltage_critical_max': 260.0,  # Critical over-voltage
            'frequency_min': self.FREQUENCY_NOMINAL - self.FREQUENCY_TOLERANCE,  # 59.5 Hz
            'frequency_max': self.FREQUENCY_NOMINAL + self.FREQUENCY_TOLERANCE,  # 60.5 Hz
            'consumption_spike_factor': 3.0,  # 3x normal = spike
            'rate_change_threshold': 5.0,  # kW/timestep
        }
        
        # Weights for different anomaly types
        self.weights = {
            'reconstruction': 0.20,
            'voltage': 0.20,
            'consumption': 0.15,
            'power_factor': 0.15,
            'frequency': 0.15,
            'temporal': 0.10,
            'rate_change': 0.05
        }
        
        self.statistics = {}
        
    def compute_statistics(self, data: pd.DataFrame):
        """Compute baseline statistics from normal data"""
        print("📊 Computing baseline statistics...")
        
        self.statistics = {
            'consumption_mean': data['consommation_kw'].mean(),
            'consumption_std': data['consommation_kw'].std(),
            'consumption_q95': data['consommation_kw'].quantile(0.95),
            'voltage_mean': data['tension_v'].mean(),
            'voltage_std': data['tension_v'].std(),
            'current_mean': data['courant_a'].mean(),
            'current_std': data['courant_a'].std(),
        }
        
        # Per consumer type statistics
        for ctype in data['type'].unique():
            type_data = data[data['type'] == ctype]
            self.statistics[f'{ctype}_consumption_mean'] = type_data['consommation_kw'].mean()
            self.statistics[f'{ctype}_consumption_std'] = type_data['consommation_kw'].std()
            self.statistics[f'{ctype}_consumption_q95'] = type_data['consommation_kw'].quantile(0.95)
        
        print(f"   ✅ Baseline statistics computed")
        print(f"      • Avg consumption: {self.statistics['consumption_mean']:.2f} kW")
        print(f"      • Avg voltage: {self.statistics['voltage_mean']:.2f} V")
        
    def detect_voltage_anomaly(self, voltage: float) -> Tuple[float, str]:
        """
        Detect voltage anomalies
        
        Criteria:
        - Under-voltage: < 207V (warning), < 200V (critical)
        - Over-voltage: > 253V (warning), > 260V (critical)
        - Voltage sag/swell
        """
        score = 0.0
        anomaly_type = "normal"
        
        if voltage < self.thresholds['voltage_critical_min']:
            score = 1.0
            anomaly_type = "critical_under_voltage"
        elif voltage < self.thresholds['voltage_min']:
            score = 0.7
            anomaly_type = "under_voltage"
        elif voltage > self.thresholds['voltage_critical_max']:
            score = 1.0
            anomaly_type = "critical_over_voltage"
        elif voltage > self.thresholds['voltage_max']:
            score = 0.7
            anomaly_type = "over_voltage"
        
        # Voltage deviation from nominal
        deviation = abs(voltage - self.VOLTAGE_NOMINAL) / self.VOLTAGE_NOMINAL
        if deviation > 0.05:  # > 5% deviation
            score = max(score, deviation * 2)
        
        return score, anomaly_type
    
    def detect_consumption_anomaly(self, consumption: float, consumer_type: str, hour: int) -> Tuple[float, str]:
        """
        Detect consumption anomalies
        
        Criteria:
        - Unusually high consumption (> 3x normal)
        - Zero consumption during expected usage hours
        - Consumption pattern mismatch
        """
        score = 0.0
        anomaly_type = "normal"
        
        # Get type-specific statistics
        type_mean = self.statistics.get(f'{consumer_type}_consumption_mean', self.statistics['consumption_mean'])
        type_std = self.statistics.get(f'{consumer_type}_consumption_std', self.statistics['consumption_std'])
        type_q95 = self.statistics.get(f'{consumer_type}_consumption_q95', self.statistics['consumption_q95'])
        
        # High consumption spike
        if consumption > type_mean * self.thresholds['consumption_spike_factor']:
            score = 0.9
            anomaly_type = "consumption_spike"
        elif consumption > type_q95:
            score = 0.6
            anomaly_type = "high_consumption"
        
        # Zero consumption during expected hours
        if consumption == 0.0:
            if consumer_type == "industriel" and 6 <= hour <= 22:
                score = 0.8
                anomaly_type = "unexpected_zero_consumption"
            elif consumer_type == "commercial" and 8 <= hour <= 18:
                score = 0.7
                anomaly_type = "unexpected_zero_consumption"
        
        # Statistical outlier (> 3 sigma)
        z_score = abs(consumption - type_mean) / (type_std + 1e-6)
        if z_score > 3:
            score = max(score, min(z_score / 5, 1.0))
            anomaly_type = "statistical_outlier"
        
        return score, anomaly_type
    
    def detect_power_factor_anomaly(self, consumption: float, voltage: float, current: float) -> Tuple[float, str]:
        """
        Detect power factor anomalies
        
        Criteria:
        - Low power factor (< 0.85)
        - Reactive power issues
        - Power triangle inconsistencies
        """
        score = 0.0
        anomaly_type = "normal"
        
        if voltage <= 0 or current <= 0:
            return 0.0, "normal"
        
        # Calculate apparent power
        apparent_power = voltage * current / 1000  # kVA
        
        if apparent_power == 0:
            return 0.0, "normal"
        
        # Calculate power factor
        power_factor = consumption / (apparent_power + 1e-6)
        power_factor = min(power_factor, 1.0)  # Cap at 1.0
        
        if power_factor < self.POWER_FACTOR_MIN:
            score = (self.POWER_FACTOR_MIN - power_factor) / self.POWER_FACTOR_MIN
            anomaly_type = "low_power_factor"
        
        # Impossible power factor (> 1.0 before capping)
        if consumption > apparent_power * 1.05:
            score = 0.9
            anomaly_type = "impossible_power_factor"
        
        return score, anomaly_type
    
    def detect_frequency_anomaly(self, frequency: float) -> Tuple[float, str]:
        """
        Detect frequency anomalies
        
        Criteria:
        - Frequency deviation from 60 Hz
        - Grid instability indicators
        """
        score = 0.0
        anomaly_type = "normal"
        
        if frequency < self.thresholds['frequency_min']:
            deviation = (self.thresholds['frequency_min'] - frequency) / self.FREQUENCY_TOLERANCE
            score = min(deviation, 1.0)
            anomaly_type = "low_frequency"
        elif frequency > self.thresholds['frequency_max']:
            deviation = (frequency - self.thresholds['frequency_max']) / self.FREQUENCY_TOLERANCE
            score = min(deviation, 1.0)
            anomaly_type = "high_frequency"
        
        return score, anomaly_type
    
    def detect_temporal_anomaly(self, consumption: float, consumer_type: str, hour: int, is_weekend: bool) -> Tuple[float, str]:
        """
        Detect temporal pattern anomalies
        
        Criteria:
        - Consumption at unusual hours
        - Weekend/weekday pattern violations
        """
        score = 0.0
        anomaly_type = "normal"
        
        # Residential: high consumption at night (0-5 AM)
        if consumer_type == "residentiel":
            if 0 <= hour <= 5 and consumption > self.statistics['consumption_mean'] * 1.5:
                score = 0.6
                anomaly_type = "unusual_night_consumption"
        
        # Commercial: high consumption on weekend or at night
        elif consumer_type == "commercial":
            if is_weekend and consumption > self.statistics['consumption_mean']:
                score = 0.5
                anomaly_type = "weekend_commercial_activity"
            elif (0 <= hour <= 6 or 20 <= hour <= 23) and consumption > self.statistics['consumption_mean']:
                score = 0.5
                anomaly_type = "off_hours_commercial_activity"
        
        # Industrial: sudden drop during work hours
        elif consumer_type == "industriel":
            if 8 <= hour <= 18 and consumption < self.statistics['consumption_mean'] * 0.3:
                score = 0.6
                anomaly_type = "unexpected_industrial_shutdown"
        
        return score, anomaly_type
    
    def detect_rate_change_anomaly(self, consumption_diff: float, consumption_rate: float) -> Tuple[float, str]:
        """
        Detect sudden rate of change anomalies
        
        Criteria:
        - Sudden spikes or drops
        - Rapid fluctuations
        """
        score = 0.0
        anomaly_type = "normal"
        
        # Sudden change in absolute terms
        if abs(consumption_diff) > self.thresholds['rate_change_threshold']:
            score = min(abs(consumption_diff) / (self.thresholds['rate_change_threshold'] * 2), 1.0)
            anomaly_type = "sudden_change"
        
        # Rapid percentage change
        if abs(consumption_rate) > 2.0:  # > 200% change
            score = max(score, min(abs(consumption_rate) / 5.0, 1.0))
            anomaly_type = "rapid_fluctuation"
        
        return score, anomaly_type
    
    def detect_anomalies(
        self,
        reconstruction_errors: np.ndarray,
        data: pd.DataFrame,
        threshold_percentile: float = 95
    ) -> List[AnomalyScore]:
        """
        Comprehensive anomaly detection using multiple criteria
        
        Returns list of AnomalyScore objects with detailed information
        """
        print(f"\n🔍 Running enhanced anomaly detection...")
        print(f"   • Using {len(self.weights)} detection criteria")
        
        # Compute reconstruction error threshold
        recon_threshold = np.percentile(reconstruction_errors, threshold_percentile)
        
        anomaly_scores = []
        
        for idx, row in data.iterrows():
            score = AnomalyScore()
            
            # 1. Reconstruction error (ML-based)
            recon_error = reconstruction_errors[idx] if idx < len(reconstruction_errors) else 0
            score.reconstruction_error = 1.0 if recon_error > recon_threshold else recon_error / recon_threshold
            
            # 2. Voltage anomaly
            voltage_score, voltage_type = self.detect_voltage_anomaly(row['tension_v'])
            score.voltage_anomaly = voltage_score
            
            # 3. Consumption anomaly
            consumption_score, consumption_type = self.detect_consumption_anomaly(
                row['consommation_kw'], row['type'], row.get('hour', 12)
            )
            score.consumption_anomaly = consumption_score
            
            # 4. Power factor anomaly
            pf_score, pf_type = self.detect_power_factor_anomaly(
                row['consommation_kw'], row['tension_v'], row['courant_a']
            )
            score.power_factor_anomaly = pf_score
            
            # 5. Frequency anomaly (if available)
            if 'frequency_hz' in row:
                freq_score, freq_type = self.detect_frequency_anomaly(row.get('frequency_hz', 60.0))
                score.frequency_anomaly = freq_score
            
            # 6. Temporal anomaly
            temporal_score, temporal_type = self.detect_temporal_anomaly(
                row['consommation_kw'], row['type'], 
                row.get('hour', 12), row.get('is_weekend', False)
            )
            score.temporal_anomaly = temporal_score
            
            # 7. Rate of change anomaly
            rate_score, rate_type = self.detect_rate_change_anomaly(
                row.get('consumption_diff', 0), row.get('consumption_rate_change', 0)
            )
            score.rate_change_anomaly = rate_score
            
            # Compute weighted total score
            score.total_score = (
                score.reconstruction_error * self.weights['reconstruction'] +
                score.voltage_anomaly * self.weights['voltage'] +
                score.consumption_anomaly * self.weights['consumption'] +
                score.power_factor_anomaly * self.weights['power_factor'] +
                score.frequency_anomaly * self.weights['frequency'] +
                score.temporal_anomaly * self.weights['temporal'] +
                score.rate_change_anomaly * self.weights['rate_change']
            )
            
            # Determine if anomaly (threshold = 0.2 for better detection)
            score.is_anomaly = score.total_score > 0.2
            
            # Determine anomaly type (highest scoring criterion)
            scores_dict = {
                'reconstruction': score.reconstruction_error,
                'voltage': score.voltage_anomaly,
                'consumption': score.consumption_anomaly,
                'power_factor': score.power_factor_anomaly,
                'frequency': score.frequency_anomaly,
                'temporal': score.temporal_anomaly,
                'rate_change': score.rate_change_anomaly
            }
            
            if score.is_anomaly:
                max_criterion = max(scores_dict, key=scores_dict.get)
                score.anomaly_type = max_criterion
                score.confidence = scores_dict[max_criterion]
            else:
                score.anomaly_type = "normal"
                score.confidence = 1.0 - score.total_score
            
            anomaly_scores.append(score)
        
        # Summary statistics
        n_anomalies = sum(1 for s in anomaly_scores if s.is_anomaly)
        anomaly_rate = n_anomalies / len(anomaly_scores) * 100
        
        print(f"\n   ✅ Detection complete:")
        print(f"      • Total samples: {len(anomaly_scores):,}")
        print(f"      • Anomalies detected: {n_anomalies:,} ({anomaly_rate:.2f}%)")
        
        # Breakdown by type
        anomaly_types = {}
        for s in anomaly_scores:
            if s.is_anomaly:
                anomaly_types[s.anomaly_type] = anomaly_types.get(s.anomaly_type, 0) + 1
        
        if anomaly_types:
            print(f"\n   📊 Anomaly breakdown:")
            for atype, count in sorted(anomaly_types.items(), key=lambda x: x[1], reverse=True):
                pct = count / n_anomalies * 100
                print(f"      • {atype}: {count} ({pct:.1f}%)")
        
        return anomaly_scores
    
    def get_predictions(self, anomaly_scores: List[AnomalyScore]) -> np.ndarray:
        """Convert anomaly scores to binary predictions"""
        return np.array([1 if s.is_anomaly else 0 for s in anomaly_scores])
    
    def get_confidence_scores(self, anomaly_scores: List[AnomalyScore]) -> np.ndarray:
        """Get confidence scores for each prediction"""
        return np.array([s.total_score for s in anomaly_scores])
    
    def export_detailed_results(self, anomaly_scores: List[AnomalyScore], filepath: str):
        """Export detailed anomaly analysis to CSV"""
        results = []
        for idx, score in enumerate(anomaly_scores):
            results.append({
                'index': idx,
                'is_anomaly': score.is_anomaly,
                'anomaly_type': score.anomaly_type,
                'total_score': score.total_score,
                'confidence': score.confidence,
                'reconstruction_score': score.reconstruction_error,
                'voltage_score': score.voltage_anomaly,
                'consumption_score': score.consumption_anomaly,
                'power_factor_score': score.power_factor_anomaly,
                'frequency_score': score.frequency_anomaly,
                'temporal_score': score.temporal_anomaly,
                'rate_change_score': score.rate_change_anomaly
            })
        
        df = pd.DataFrame(results)
        df.to_csv(filepath, index=False)
        print(f"\n   💾 Detailed results exported to: {filepath}")
