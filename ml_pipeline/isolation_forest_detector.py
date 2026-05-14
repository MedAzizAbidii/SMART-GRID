"""
Isolation Forest Anomaly Detector with Zone-Based Segmentation
Recommended approach for structured smart meter data
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import pickle
import os
from typing import Dict, List, Tuple


class SegmentedIsolationForestDetector:
    """
    Anomaly detector using Isolation Forest with zone-based segmentation
    
    Key Features:
    - Separate model per zone + meter type combination
    - Fast training (~30 seconds total)
    - High interpretability
    - Expected 40-60% recall
    """
    
    def __init__(self, contamination=0.1, n_estimators=100):
        """
        Args:
            contamination: Expected proportion of anomalies (default: 0.1 = 10%)
            n_estimators: Number of trees in forest (default: 100)
        """
        self.contamination = contamination
        self.n_estimators = n_estimators
        self.models = {}  # One model per segment
        self.scalers = {}  # One scaler per segment
        self.segments = []  # List of segment names
        
        # Features to use for detection
        self.features = [
            'consommation_kw',
            'tension_v',
            'courant_a',
            'facteur_puissance',
            'frequence_hz'
        ]
        
        # IEEE standards for domain rules
        self.thresholds = {
            'voltage_min': 207.0,  # IEEE 1547
            'voltage_max': 253.0,  # IEEE 1547
            'frequency_min': 59.5,
            'frequency_max': 60.5,
            'power_factor_min': 0.85
        }
    
    def _get_segment_key(self, zone: str, meter_type: str) -> str:
        """Create segment identifier"""
        return f"{zone}_{meter_type}"
    
    def train(self, data: pd.DataFrame):
        """
        Train separate Isolation Forest model for each segment
        
        Args:
            data: DataFrame with columns: zone, type, consommation_kw, tension_v, etc.
        """
        print("\n" + "=" * 70)
        print("🌲 TRAINING SEGMENTED ISOLATION FOREST DETECTOR")
        print("=" * 70)
        
        # Get unique zones and types
        zones = data['zone'].unique()
        meter_types = data['type'].unique()
        
        print(f"\n📊 Data Overview:")
        print(f"   Total samples: {len(data):,}")
        print(f"   Zones: {list(zones)}")
        print(f"   Meter types: {list(meter_types)}")
        print(f"   Features: {self.features}")
        print()
        
        total_segments = 0
        total_samples = 0
        
        # Train model for each segment
        for zone in zones:
            for meter_type in meter_types:
                segment_key = self._get_segment_key(zone, meter_type)
                
                # Filter data for this segment
                segment_data = data[
                    (data['zone'] == zone) & 
                    (data['type'] == meter_type)
                ]
                
                if len(segment_data) < 10:
                    print(f"   ⚠️ Skipping {segment_key}: insufficient data ({len(segment_data)} samples)")
                    continue
                
                # Extract features
                X = segment_data[self.features].values
                
                # Normalize features
                scaler = StandardScaler()
                X_scaled = scaler.fit_transform(X)
                
                # Train Isolation Forest
                model = IsolationForest(
                    contamination=self.contamination,
                    n_estimators=self.n_estimators,
                    max_samples='auto',
                    random_state=42,
                    n_jobs=-1  # Use all CPU cores
                )
                model.fit(X_scaled)
                
                # Save model and scaler
                self.models[segment_key] = model
                self.scalers[segment_key] = scaler
                self.segments.append(segment_key)
                
                total_segments += 1
                total_samples += len(segment_data)
                
                print(f"   ✅ {segment_key:25s} | {len(segment_data):6,} samples | Model trained")
        
        print()
        print(f"📈 Training Summary:")
        print(f"   Segments trained: {total_segments}")
        print(f"   Total samples: {total_samples:,}")
        print(f"   Average per segment: {total_samples // total_segments:,}")
        print()
        print("=" * 70)
    
    def predict(self, reading: Dict) -> Dict:
        """
        Predict if a single reading is anomalous
        
        Args:
            reading: Dictionary with keys: zone, type, consommation_kw, tension_v, etc.
        
        Returns:
            Dictionary with prediction results
        """
        segment_key = self._get_segment_key(reading['zone'], reading['type'])
        
        # Check if model exists for this segment
        if segment_key not in self.models:
            return {
                'is_anomaly': False,
                'anomaly_score': 0.0,
                'anomalies': ['Unknown segment'],
                'segment': segment_key,
                'method': 'unknown'
            }
        
        # Extract features
        features = np.array([[
            reading['consommation_kw'],
            reading['tension_v'],
            reading['courant_a'],
            reading.get('facteur_puissance', 0.9),
            reading.get('frequency_hz', 60.0)
        ]])
        
        # Normalize
        model = self.models[segment_key]
        scaler = self.scalers[segment_key]
        features_scaled = scaler.transform(features)
        
        # Predict with Isolation Forest
        prediction = model.predict(features_scaled)[0]  # 1 = normal, -1 = anomaly
        anomaly_score = model.score_samples(features_scaled)[0]  # Lower = more anomalous
        
        # Combine ML with domain rules
        anomalies = []
        
        # ML detection
        if prediction == -1:
            anomalies.append(f"ML_isolation (score: {anomaly_score:.3f})")
        
        # Domain rules (IEEE standards)
        if reading['tension_v'] < self.thresholds['voltage_min']:
            anomalies.append("Voltage_too_low")
        elif reading['tension_v'] > self.thresholds['voltage_max']:
            anomalies.append("Voltage_too_high")
        
        if reading.get('frequency_hz', 60.0) < self.thresholds['frequency_min']:
            anomalies.append("Frequency_too_low")
        elif reading.get('frequency_hz', 60.0) > self.thresholds['frequency_max']:
            anomalies.append("Frequency_too_high")
        
        if reading.get('facteur_puissance', 0.9) < self.thresholds['power_factor_min']:
            anomalies.append("Low_power_factor")
        
        return {
            'is_anomaly': len(anomalies) > 0,
            'anomaly_score': anomaly_score,
            'anomalies': anomalies,
            'segment': segment_key,
            'method': 'isolation_forest'
        }
    
    def predict_batch(self, data: pd.DataFrame) -> List[Dict]:
        """
        Predict anomalies for multiple readings
        
        Args:
            data: DataFrame with readings
        
        Returns:
            List of prediction dictionaries
        """
        results = []
        for _, row in data.iterrows():
            reading = row.to_dict()
            result = self.predict(reading)
            results.append(result)
        return results
    
    def evaluate(self, data: pd.DataFrame, true_labels: np.ndarray) -> Dict:
        """
        Evaluate model performance
        
        Args:
            data: DataFrame with readings
            true_labels: True labels (0 = normal, 1 = anomaly)
        
        Returns:
            Dictionary with metrics
        """
        predictions = self.predict_batch(data)
        y_pred = np.array([1 if p['is_anomaly'] else 0 for p in predictions])
        
        # Calculate metrics
        tp = np.sum((y_pred == 1) & (true_labels == 1))
        tn = np.sum((y_pred == 0) & (true_labels == 0))
        fp = np.sum((y_pred == 1) & (true_labels == 0))
        fn = np.sum((y_pred == 0) & (true_labels == 1))
        
        accuracy = (tp + tn) / len(true_labels) if len(true_labels) > 0 else 0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        return {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1_score': f1_score,
            'tp': tp,
            'tn': tn,
            'fp': fp,
            'fn': fn
        }
    
    def save(self, filepath: str):
        """Save models to file"""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'wb') as f:
            pickle.dump({
                'models': self.models,
                'scalers': self.scalers,
                'segments': self.segments,
                'features': self.features,
                'thresholds': self.thresholds,
                'contamination': self.contamination,
                'n_estimators': self.n_estimators
            }, f)
        print(f"✅ Models saved to {filepath}")
    
    def load(self, filepath: str):
        """Load models from file"""
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
            self.models = data['models']
            self.scalers = data['scalers']
            self.segments = data['segments']
            self.features = data['features']
            self.thresholds = data['thresholds']
            self.contamination = data['contamination']
            self.n_estimators = data['n_estimators']
        print(f"✅ Models loaded from {filepath}")


def train_isolation_forest_detector(data_path: str, output_path: str = None):
    """
    Convenience function to train detector from CSV file
    
    Args:
        data_path: Path to CSV file with smart meter data
        output_path: Path to save trained models (optional)
    
    Returns:
        Trained detector
    """
    print(f"\n📂 Loading data from {data_path}...")
    df = pd.read_csv(data_path)
    
    # Initialize detector
    detector = SegmentedIsolationForestDetector(
        contamination=0.1,  # Expect 10% anomalies
        n_estimators=100
    )
    
    # Train
    import time
    start_time = time.time()
    detector.train(df)
    training_time = time.time() - start_time
    
    print(f"\n⏱️ Training completed in {training_time:.2f} seconds")
    
    # Save if output path provided
    if output_path:
        detector.save(output_path)
    
    return detector


if __name__ == "__main__":
    # Example usage
    print("=" * 70)
    print("ISOLATION FOREST DETECTOR - EXAMPLE")
    print("=" * 70)
    
    # Check if data file exists
    data_file = "balanced_training_data.csv"
    if not os.path.exists(data_file):
        print(f"\n❌ Data file not found: {data_file}")
        print("   Run: py -3.10-64 generate_balanced_data.py")
    else:
        # Train detector
        detector = train_isolation_forest_detector(
            data_path=data_file,
            output_path="ml_pipeline/models/isolation_forest_models.pkl"
        )
        
        # Test on sample data
        print("\n" + "=" * 70)
        print("🧪 TESTING ON SAMPLE DATA")
        print("=" * 70)
        
        df = pd.read_csv(data_file, nrows=1000)
        
        # Evaluate
        true_labels = (df['statut'] == 'ALERTE').astype(int).values
        metrics = detector.evaluate(df, true_labels)
        
        print(f"\n📊 Performance Metrics:")
        print(f"   Accuracy:  {metrics['accuracy']:.4f}")
        print(f"   Precision: {metrics['precision']:.4f}")
        print(f"   Recall:    {metrics['recall']:.4f}")
        print(f"   F1-Score:  {metrics['f1_score']:.4f}")
        print()
        print(f"   True Positives:  {metrics['tp']}")
        print(f"   True Negatives:  {metrics['tn']}")
        print(f"   False Positives: {metrics['fp']}")
        print(f"   False Negatives: {metrics['fn']}")
        print()
        print("=" * 70)
