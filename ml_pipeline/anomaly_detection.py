"""
Step 5: Anomaly Detection using Reconstruction Error
"""
import torch
import numpy as np
from typing import Tuple, Dict


class AnomalyDetector:
    """
    Detects anomalies using reconstruction error from Transformer Autoencoder
    
    Methods:
    1. Reconstruction Error: ||input - output||
    2. Dynamic Threshold: mean + k*std or percentile-based
    """
    
    def __init__(self, model, device='cpu'):
        self.model = model
        self.device = device
        self.threshold = None
        self.reconstruction_errors = None
        
    def compute_reconstruction_errors(self, dataloader) -> np.ndarray:
        """
        Compute reconstruction errors for all samples
        """
        self.model.eval()
        errors = []
        
        with torch.no_grad():
            for batch_x, _ in dataloader:
                batch_x = batch_x.to(self.device)
                reconstructed = self.model(batch_x)
                
                # Compute MSE per sequence
                batch_errors = torch.mean((batch_x - reconstructed) ** 2, dim=(1, 2))
                errors.extend(batch_errors.cpu().numpy())
        
        self.reconstruction_errors = np.array(errors)
        return self.reconstruction_errors
    
    def set_threshold_percentile(self, errors: np.ndarray, percentile: float = 95):
        """
        Set threshold based on percentile of reconstruction errors
        
        Args:
            errors: Reconstruction errors from training/validation data
            percentile: Percentile value (e.g., 95 means top 5% are anomalies)
        """
        self.threshold = np.percentile(errors, percentile)
        print(f"   📊 Threshold set at {percentile}th percentile: {self.threshold:.6f}")
        return self.threshold
    
    def set_threshold_dynamic(self, errors: np.ndarray, multiplier: float = 2.0):
        """
        Set dynamic threshold: mean + k*std
        
        Args:
            errors: Reconstruction errors from training/validation data
            multiplier: Number of standard deviations above mean
        """
        mean_error = np.mean(errors)
        std_error = np.std(errors)
        self.threshold = mean_error + multiplier * std_error
        
        print(f"   📊 Dynamic threshold: {self.threshold:.6f}")
        print(f"      (mean={mean_error:.6f}, std={std_error:.6f})")
        return self.threshold
    
    def detect_anomalies(self, errors: np.ndarray) -> np.ndarray:
        """
        Detect anomalies based on threshold
        
        Returns:
            predictions: Binary array (1=anomaly, 0=normal)
        """
        if self.threshold is None:
            raise ValueError("Threshold not set. Call set_threshold_* first.")
        
        predictions = (errors > self.threshold).astype(int)
        return predictions
    
    def predict(self, dataloader) -> Tuple[np.ndarray, np.ndarray]:
        """
        Predict anomalies for a dataset
        
        Returns:
            predictions: Binary predictions (1=anomaly, 0=normal)
            errors: Reconstruction errors
        """
        errors = self.compute_reconstruction_errors(dataloader)
        predictions = self.detect_anomalies(errors)
        
        return predictions, errors
    
    def get_anomaly_scores(self, dataloader) -> Dict:
        """
        Get detailed anomaly scores and statistics
        """
        errors = self.compute_reconstruction_errors(dataloader)
        predictions = self.detect_anomalies(errors)
        
        return {
            'errors': errors,
            'predictions': predictions,
            'threshold': self.threshold,
            'n_anomalies': predictions.sum(),
            'anomaly_rate': predictions.mean(),
            'mean_error': errors.mean(),
            'std_error': errors.std(),
            'max_error': errors.max(),
            'min_error': errors.min()
        }
