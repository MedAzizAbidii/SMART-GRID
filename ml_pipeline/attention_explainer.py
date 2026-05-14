"""
Step 6: Attention Mechanism for Explainability
Extracts attention weights to show WHEN anomalies occur
"""
import torch
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import List, Dict


class AttentionExplainer:
    """
    Extracts and visualizes attention weights from Transformer
    
    Purpose: Show WHEN (which timesteps) anomalies occur
    """
    
    def __init__(self, model, device='cpu'):
        self.model = model
        self.device = device
        self.attention_maps = []
        
    def extract_attention_weights(self, x: torch.Tensor) -> np.ndarray:
        """
        Extract attention weights from transformer encoder
        
        Args:
            x: Input tensor [batch_size, seq_len, n_features]
        
        Returns:
            attention: Attention weights [batch_size, seq_len, seq_len]
        """
        self.model.eval()
        
        with torch.no_grad():
            x = x.to(self.device)
            
            # Forward pass with attention extraction
            _, attention = self.model(x, return_attention=True)
            
        return attention.cpu().numpy()
    
    def get_timestep_importance(self, attention: np.ndarray) -> np.ndarray:
        """
        Compute importance score for each timestep
        
        Args:
            attention: Attention weights [batch_size, seq_len, seq_len]
        
        Returns:
            importance: Importance scores [batch_size, seq_len]
        """
        # Average attention received by each timestep
        importance = attention.mean(axis=1)  # Average over query dimension
        return importance
    
    def identify_critical_timesteps(
        self,
        attention: np.ndarray,
        top_k: int = 3
    ) -> List[int]:
        """
        Identify the most critical timesteps based on attention
        
        Returns:
            critical_timesteps: Indices of top-k important timesteps
        """
        importance = self.get_timestep_importance(attention)
        
        # Get top-k timesteps
        critical_timesteps = []
        for seq_importance in importance:
            top_indices = np.argsort(seq_importance)[-top_k:][::-1]
            critical_timesteps.append(top_indices.tolist())
        
        return critical_timesteps
    
    def visualize_attention_heatmap(
        self,
        attention: np.ndarray,
        sample_idx: int = 0,
        save_path: str = None
    ):
        """
        Visualize attention heatmap for a single sequence
        
        Args:
            attention: Attention weights [batch_size, seq_len, seq_len]
            sample_idx: Index of sample to visualize
            save_path: Path to save figure
        """
        plt.figure(figsize=(10, 8))
        
        # Get attention for single sample
        attn_map = attention[sample_idx]
        
        # Create heatmap
        sns.heatmap(
            attn_map,
            cmap='YlOrRd',
            cbar_kws={'label': 'Attention Weight'},
            xticklabels=range(attn_map.shape[1]),
            yticklabels=range(attn_map.shape[0])
        )
        
        plt.title(f'Attention Heatmap - Sample {sample_idx}', fontsize=14, fontweight='bold')
        plt.xlabel('Key Position (Timestep)', fontsize=12)
        plt.ylabel('Query Position (Timestep)', fontsize=12)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"   💾 Saved attention heatmap to {save_path}")
        
        plt.close()
    
    def visualize_timestep_importance(
        self,
        attention: np.ndarray,
        sample_idx: int = 0,
        metadata: Dict = None,
        save_path: str = None
    ):
        """
        Visualize importance of each timestep
        """
        importance = self.get_timestep_importance(attention)
        
        plt.figure(figsize=(12, 4))
        
        timesteps = range(importance.shape[1])
        plt.bar(timesteps, importance[sample_idx], color='steelblue', alpha=0.7)
        plt.axhline(y=importance[sample_idx].mean(), color='red', linestyle='--', 
                   label=f'Mean: {importance[sample_idx].mean():.3f}')
        
        plt.title(f'Timestep Importance - Sample {sample_idx}', fontsize=14, fontweight='bold')
        plt.xlabel('Timestep', fontsize=12)
        plt.ylabel('Importance Score', fontsize=12)
        plt.legend()
        plt.grid(axis='y', alpha=0.3)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"   💾 Saved timestep importance to {save_path}")
        
        plt.close()
    
    def explain_anomaly_timing(
        self,
        x: torch.Tensor,
        sample_idx: int = 0,
        top_k: int = 3
    ) -> Dict:
        """
        Provide explanation of WHEN anomaly occurs
        
        Returns:
            explanation: Dictionary with timing information
        """
        attention = self.extract_attention_weights(x)
        importance = self.get_timestep_importance(attention)
        critical_timesteps = self.identify_critical_timesteps(attention, top_k)
        
        explanation = {
            'sample_idx': sample_idx,
            'critical_timesteps': critical_timesteps[sample_idx],
            'importance_scores': importance[sample_idx].tolist(),
            'max_importance_timestep': int(np.argmax(importance[sample_idx])),
            'mean_importance': float(importance[sample_idx].mean()),
            'attention_map': attention[sample_idx]
        }
        
        return explanation
