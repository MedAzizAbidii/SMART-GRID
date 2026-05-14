"""
Step 1-3: Data Collection, Preprocessing, and Feature Engineering
"""
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from typing import Tuple, Dict
import warnings
warnings.filterwarnings('ignore')


class SmartGridDataPreprocessor:
    """
    Handles data loading, cleaning, feature engineering, and sequence creation
    """
    
    def __init__(self, sequence_length: int = 20):
        self.sequence_length = sequence_length
        self.scaler = StandardScaler()
        self.zone_encoder = LabelEncoder()
        self.type_encoder = LabelEncoder()
        self.feature_names = []
        
    def load_data(self, filepath: str) -> pd.DataFrame:
        """Load smart meter data from CSV"""
        print(f"📂 Loading data from {filepath}...")
        df = pd.read_csv(filepath)
        print(f"   ✅ Loaded {len(df):,} records")
        return df
    
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean missing values and outliers"""
        print("🧹 Cleaning data...")
        
        # Remove duplicates
        df = df.drop_duplicates()
        
        # Handle missing values
        df = df.dropna(subset=['consommation_kw', 'tension_v', 'courant_a'])
        
        # Remove extreme outliers (beyond 5 std)
        for col in ['consommation_kw', 'tension_v', 'courant_a']:
            mean = df[col].mean()
            std = df[col].std()
            df = df[(df[col] >= mean - 5*std) & (df[col] <= mean + 5*std)]
        
        print(f"   ✅ Cleaned data: {len(df):,} records remaining")
        return df
    
    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Feature Engineering - Step 3
        Creates temporal, statistical, and behavioral features
        """
        print("🔢 Engineering features...")
        
        df = df.copy()
        
        # Parse timestamp
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Temporal features
        df['hour'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
        
        # Cyclical encoding for hour (important for temporal patterns)
        df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
        df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
        
        # Encode categorical features
        df['zone_encoded'] = self.zone_encoder.fit_transform(df['zone'].astype(str))
        df['type_encoded'] = self.type_encoder.fit_transform(df['type'].astype(str))
        
        # Sort by meter and time for rolling features
        df = df.sort_values(['meter_id', 'timestamp'])
        
        # Rolling statistics (per meter)
        df['consumption_rolling_mean'] = df.groupby('meter_id')['consommation_kw'].transform(
            lambda x: x.rolling(window=5, min_periods=1).mean()
        )
        df['consumption_rolling_std'] = df.groupby('meter_id')['consommation_kw'].transform(
            lambda x: x.rolling(window=5, min_periods=1).std().fillna(0)
        )
        df['voltage_rolling_mean'] = df.groupby('meter_id')['tension_v'].transform(
            lambda x: x.rolling(window=5, min_periods=1).mean()
        )
        
        # Difference features (rate of change)
        df['consumption_diff'] = df.groupby('meter_id')['consommation_kw'].diff().fillna(0)
        df['consumption_rate_change'] = df.groupby('meter_id')['consommation_kw'].pct_change().fillna(0)
        
        # Replace inf values
        df = df.replace([np.inf, -np.inf], 0)
        
        # Create anomaly label (1 if ALERTE, 0 if NORMAL)
        if 'statut' in df.columns:
            df['is_anomaly'] = (df['statut'] == 'ALERTE').astype(int)
        else:
            df['is_anomaly'] = 0
        
        print(f"   ✅ Created {len(df.columns)} features")
        return df
    
    def create_sequences(self, df: pd.DataFrame, feature_cols: list) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Transform data into temporal sequences
        [evt1, evt2, evt3, ..., evt_n] → one sequence
        """
        print(f"📊 Creating sequences (length={self.sequence_length})...")
        
        sequences = []
        labels = []
        metadata = []
        
        # Group by meter_id to create sequences per meter
        for meter_id, group in df.groupby('meter_id'):
            group = group.sort_values('timestamp')
            
            # Skip if not enough data
            if len(group) < self.sequence_length:
                continue
            
            # Create sliding windows
            for i in range(len(group) - self.sequence_length + 1):
                window = group.iloc[i:i + self.sequence_length]
                
                # Extract features
                seq_features = window[feature_cols].values
                sequences.append(seq_features)
                
                # Label: 1 if ANY timestep in sequence has anomaly
                label = window['is_anomaly'].max()
                labels.append(label)
                
                # Store metadata for later analysis
                metadata.append({
                    'meter_id': meter_id,
                    'start_time': window['timestamp'].iloc[0],
                    'end_time': window['timestamp'].iloc[-1],
                    'zone': window['zone'].iloc[0],
                    'type': window['type'].iloc[0]
                })
        
        sequences = np.array(sequences, dtype=np.float32)
        labels = np.array(labels, dtype=np.int32)
        
        print(f"   ✅ Created {len(sequences):,} sequences")
        print(f"   • Normal sequences: {(labels == 0).sum():,}")
        print(f"   • Anomaly sequences: {(labels == 1).sum():,}")
        
        return sequences, labels, metadata
    
    def normalize_features(self, X_train: np.ndarray, X_val: np.ndarray, X_test: np.ndarray) -> Tuple:
        """Normalize features using StandardScaler"""
        print("📏 Normalizing features...")
        
        # Reshape for scaling
        n_train, seq_len, n_features = X_train.shape
        X_train_flat = X_train.reshape(-1, n_features)
        
        # Fit scaler on training data only
        self.scaler.fit(X_train_flat)
        
        # Transform all sets
        X_train_scaled = self.scaler.transform(X_train_flat).reshape(n_train, seq_len, n_features)
        
        n_val = X_val.shape[0]
        X_val_flat = X_val.reshape(-1, n_features)
        X_val_scaled = self.scaler.transform(X_val_flat).reshape(n_val, seq_len, n_features)
        
        n_test = X_test.shape[0]
        X_test_flat = X_test.reshape(-1, n_features)
        X_test_scaled = self.scaler.transform(X_test_flat).reshape(n_test, seq_len, n_features)
        
        print("   ✅ Normalization complete")
        return X_train_scaled, X_val_scaled, X_test_scaled
    
    def prepare_dataset(self, filepath: str, feature_cols: list) -> Dict:
        """
        Complete preprocessing pipeline
        Returns train/val/test splits with metadata
        """
        # Load and clean
        df = self.load_data(filepath)
        df = self.clean_data(df)
        
        # Engineer features
        df = self.engineer_features(df)
        
        # Create sequences
        X, y, metadata = self.create_sequences(df, feature_cols)
        
        # Split data (stratified by anomaly label)
        X_temp, X_test, y_temp, y_test, meta_temp, meta_test = train_test_split(
            X, y, metadata, test_size=0.15, random_state=42, stratify=y
        )
        
        X_train, X_val, y_train, y_val, meta_train, meta_val = train_test_split(
            X_temp, y_temp, meta_temp, test_size=0.176, random_state=42, stratify=y_temp  # 0.176 * 0.85 ≈ 0.15
        )
        
        # Normalize
        X_train, X_val, X_test = self.normalize_features(X_train, X_val, X_test)
        
        print("\n📦 Dataset prepared:")
        print(f"   • Training: {len(X_train):,} sequences")
        print(f"   • Validation: {len(X_val):,} sequences")
        print(f"   • Test: {len(X_test):,} sequences")
        
        self.feature_names = feature_cols
        
        return {
            'X_train': X_train, 'y_train': y_train, 'meta_train': meta_train,
            'X_val': X_val, 'y_val': y_val, 'meta_val': meta_val,
            'X_test': X_test, 'y_test': y_test, 'meta_test': meta_test,
            'feature_names': feature_cols,
            'scaler': self.scaler,
            'preprocessor': self
        }
