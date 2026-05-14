"""
Step 7: SHAP (Shapley Additive Explanations) for Feature Importance
Shows WHY anomalies occur (which features contribute most)
"""
import torch
import numpy as np
import shap
import matplotlib.pyplot as plt
from typing import Dict, List


class SHAPExplainer:
    """
    SHAP-based explainability for Transformer Autoencoder
    
    Purpose: Show WHY anomalies occur (feature contributions)
    
    Methods:
    - KernelSHAP: Model-agnostic approach
    - DeepSHAP: Deep learning specific (faster)
    """
    
    def __init__(self, model, device='cpu'):
        self.model = model
        self.device = device
        self.explainer = None
        self.shap_values = None
        
    def create_prediction_function(self):
        """
        Create a prediction function that returns reconstruction error
        This is what SHAP will explain
        """
        def predict_fn(x):
            """
            Args:
                x: numpy array [n_samples, seq_len, n_features]
            Returns:
                errors: reconstruction errors [n_samples]
            """
            self.model.eval()
            with torch.no_grad():
                x_tensor = torch.FloatTensor(x).to(self.device)
                reconstructed = self.model(x_tensor)
                
                # Compute reconstruction error per sample
                errors = torch.mean((x_tensor - reconstructed) ** 2, dim=(1, 2))
                
            return errors.cpu().numpy()
        
        return predict_fn
    
    def initialize_kernel_shap(self, background_data: np.ndarray, n_samples: int = 100):
        """
        Initialize KernelSHAP explainer
        
        Args:
            background_data: Background dataset for SHAP [n_samples, seq_len, n_features]
            n_samples: Number of background samples to use
        """
        print(f"🔧 Initializing KernelSHAP with {n_samples} background samples...")
        
        # Sample background data
        if len(background_data) > n_samples:
            indices = np.random.choice(len(background_data), n_samples, replace=False)
            background_data = background_data[indices]
        
        # Flatten sequences for SHAP (treat as tabular data)
        # Shape: [n_samples, seq_len * n_features]
        background_flat = background_data.reshape(len(background_data), -1)
        
        # Create prediction function
        predict_fn = self.create_prediction_function()
        
        # Wrapper to handle flattened input
        def predict_flat(x_flat):
            seq_len = background_data.shape[1]
            n_features = background_data.shape[2]
            x_reshaped = x_flat.reshape(-1, seq_len, n_features)
            return predict_fn(x_reshaped)
        
        # Initialize SHAP explainer
        self.explainer = shap.KernelExplainer(predict_flat, background_flat)
        print("   ✅ KernelSHAP initialized")
        
    def compute_shap_values(
        self,
        test_data: np.ndarray,
        n_samples: int = 50
    ) -> np.ndarray:
        """
        Compute SHAP values for test samples
        
        Args:
            test_data: Test dataset [n_samples, seq_len, n_features]
            n_samples: Number of test samples to explain
        
        Returns:
            shap_values: SHAP values [n_samples, seq_len * n_features]
        """
        if self.explainer is None:
            raise ValueError("Explainer not initialized. Call initialize_kernel_shap first.")
        
        print(f"🔍 Computing SHAP values for {n_samples} samples...")
        
        # Sample test data
        if len(test_data) > n_samples:
            indices = np.random.choice(len(test_data), n_samples, replace=False)
            test_data = test_data[indices]
        
        # Flatten
        test_flat = test_data.reshape(len(test_data), -1)
        
        # Compute SHAP values
        self.shap_values = self.explainer.shap_values(test_flat)
        
        print("   ✅ SHAP values computed")
        return self.shap_values
    
    def get_feature_importance(
        self,
        shap_values: np.ndarray,
        feature_names: List[str],
        seq_len: int
    ) -> Dict:
        """
        Aggregate SHAP values to get feature importance
        
        Args:
            shap_values: SHAP values [n_samples, seq_len * n_features]
            feature_names: List of feature names
            seq_len: Sequence length
        
        Returns:
            importance_dict: Feature importance scores
        """
        n_features = len(feature_names)
        
        # Reshape SHAP values: [n_samples, seq_len, n_features]
        shap_reshaped = shap_values.reshape(-1, seq_len, n_features)
        
        # Average absolute SHAP values across samples and timesteps
        feature_importance = np.mean(np.abs(shap_reshaped), axis=(0, 1))
        
        # Create dictionary
        importance_dict = {
            feature_names[i]: float(feature_importance[i])
            for i in range(n_features)
        }
        
        # Sort by importance
        importance_dict = dict(sorted(importance_dict.items(), key=lambda x: x[1], reverse=True))
        
        return importance_dict
    
    def visualize_feature_importance(
        self,
        importance_dict: Dict,
        top_k: int = 10,
        save_path: str = None
    ):
        """
        Visualize top-k feature importance
        """
        # Get top-k features
        top_features = list(importance_dict.items())[:top_k]
        features, importances = zip(*top_features)
        
        plt.figure(figsize=(10, 6))
        plt.barh(range(len(features)), importances, color='steelblue', alpha=0.7)
        plt.yticks(range(len(features)), features)
        plt.xlabel('Mean |SHAP Value|', fontsize=12)
        plt.title(f'Top {top_k} Feature Importance (SHAP)', fontsize=14, fontweight='bold')
        plt.gca().invert_yaxis()
        plt.grid(axis='x', alpha=0.3)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"   💾 Saved feature importance to {save_path}")
        
        plt.close()
    
    def explain_single_prediction(
        self,
        sample_idx: int,
        feature_names: List[str],
        seq_len: int,
        top_k: int = 5
    ) -> Dict:
        """
        Explain a single prediction with SHAP
        
        Returns:
            explanation: Dictionary with feature contributions
        """
        if self.shap_values is None:
            raise ValueError("SHAP values not computed. Call compute_shap_values first.")
        
        # Get SHAP values for this sample
        sample_shap = self.shap_values[sample_idx]
        
        # Reshape
        n_features = len(feature_names)
        sample_shap_reshaped = sample_shap.reshape(seq_len, n_features)
        
        # Average across timesteps
        feature_contributions = np.mean(sample_shap_reshaped, axis=0)
        
        # Create dictionary
        contributions = {
            feature_names[i]: float(feature_contributions[i])
            for i in range(n_features)
        }
        
        # Sort by absolute contribution
        contributions_sorted = dict(sorted(
            contributions.items(),
            key=lambda x: abs(x[1]),
            reverse=True
        ))
        
        # Get top-k
        top_contributions = dict(list(contributions_sorted.items())[:top_k])
        
        explanation = {
            'sample_idx': sample_idx,
            'top_features': top_contributions,
            'all_contributions': contributions_sorted
        }
        
        return explanation
    
    def visualize_shap_summary(
        self,
        shap_values: np.ndarray,
        test_data: np.ndarray,
        feature_names: List[str],
        seq_len: int,
        save_path: str = None
    ):
        """
        Create SHAP summary plot
        """
        n_features = len(feature_names)
        
        # Reshape
        shap_reshaped = shap_values.reshape(-1, seq_len, n_features)
        test_reshaped = test_data.reshape(-1, seq_len, n_features)
        
        # Average across timesteps
        shap_avg = np.mean(shap_reshaped, axis=1)
        test_avg = np.mean(test_reshaped, axis=1)
        
        # Create summary plot
        plt.figure(figsize=(10, 8))
        shap.summary_plot(
            shap_avg,
            test_avg,
            feature_names=feature_names,
            show=False
        )
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"   💾 Saved SHAP summary to {save_path}")
        
        plt.close()
