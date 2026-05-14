"""
Step 8: Fusion of Explanations
Combines Attention (WHERE) + SHAP (WHY) for complete explainability
"""
from typing import Dict, List
import numpy as np


class ExplanationFusion:
    """
    Fuses attention-based and SHAP-based explanations
    
    Provides complete answer:
    - WHERE: Which timesteps are critical (Attention)
    - WHY: Which features cause the anomaly (SHAP)
    """
    
    def __init__(self, attention_explainer, shap_explainer):
        self.attention_explainer = attention_explainer
        self.shap_explainer = shap_explainer
        
    def generate_complete_explanation(
        self,
        sample_idx: int,
        x: np.ndarray,
        feature_names: List[str],
        metadata: Dict = None,
        top_k_features: int = 5,
        top_k_timesteps: int = 3
    ) -> Dict:
        """
        Generate complete explanation combining attention and SHAP
        
        Args:
            sample_idx: Index of sample to explain
            x: Input data [batch_size, seq_len, n_features]
            feature_names: List of feature names
            metadata: Optional metadata about the sample
            top_k_features: Number of top features to show
            top_k_timesteps: Number of critical timesteps to show
        
        Returns:
            complete_explanation: Dictionary with fused explanations
        """
        import torch
        
        seq_len = x.shape[1]
        
        # 1. Get Attention explanation (WHERE)
        x_tensor = torch.FloatTensor(x)
        attention_exp = self.attention_explainer.explain_anomaly_timing(
            x_tensor,
            sample_idx=sample_idx,
            top_k=top_k_timesteps
        )
        
        # 2. Get SHAP explanation (WHY)
        shap_exp = self.shap_explainer.explain_single_prediction(
            sample_idx=sample_idx,
            feature_names=feature_names,
            seq_len=seq_len,
            top_k=top_k_features
        )
        
        # 3. Fuse explanations
        complete_explanation = {
            'sample_idx': sample_idx,
            'metadata': metadata,
            
            # WHERE (Attention)
            'critical_timesteps': attention_exp['critical_timesteps'],
            'max_importance_timestep': attention_exp['max_importance_timestep'],
            'timestep_importance_scores': attention_exp['importance_scores'],
            
            # WHY (SHAP)
            'top_contributing_features': shap_exp['top_features'],
            'feature_contributions': shap_exp['all_contributions'],
            
            # Combined insight
            'summary': self._generate_summary(attention_exp, shap_exp, metadata)
        }
        
        return complete_explanation
    
    def _generate_summary(
        self,
        attention_exp: Dict,
        shap_exp: Dict,
        metadata: Dict = None
    ) -> str:
        """
        Generate human-readable summary
        """
        # Get critical timesteps
        critical_timesteps = attention_exp['critical_timesteps']
        max_timestep = attention_exp['max_importance_timestep']
        
        # Get top features
        top_features = list(shap_exp['top_features'].items())[:3]
        
        # Build summary
        summary = f"Anomalie détectée à t={max_timestep}\n\n"
        
        summary += "CAUSE (Top 3 features):\n"
        for feature, contribution in top_features:
            sign = "+" if contribution > 0 else ""
            summary += f"  - {feature}: {sign}{contribution:.3f}\n"
        
        summary += f"\nZONE CRITIQUE (timesteps):\n"
        summary += f"  - événements: {', '.join([f't{t}' for t in critical_timesteps])}\n"
        
        if metadata:
            summary += f"\nMETADATA:\n"
            summary += f"  - Meter ID: {metadata.get('meter_id', 'N/A')}\n"
            summary += f"  - Zone: {metadata.get('zone', 'N/A')}\n"
            summary += f"  - Type: {metadata.get('type', 'N/A')}\n"
        
        return summary
    
    def explain_batch(
        self,
        x: np.ndarray,
        feature_names: List[str],
        metadata_list: List[Dict] = None,
        anomaly_indices: List[int] = None,
        top_k_features: int = 5,
        top_k_timesteps: int = 3
    ) -> List[Dict]:
        """
        Generate explanations for multiple samples
        
        Args:
            x: Input data [batch_size, seq_len, n_features]
            feature_names: List of feature names
            metadata_list: List of metadata dictionaries
            anomaly_indices: Indices of anomalous samples (if None, explain all)
            top_k_features: Number of top features to show
            top_k_timesteps: Number of critical timesteps to show
        
        Returns:
            explanations: List of explanation dictionaries
        """
        if anomaly_indices is None:
            anomaly_indices = range(len(x))
        
        explanations = []
        
        for idx in anomaly_indices:
            metadata = metadata_list[idx] if metadata_list else None
            
            explanation = self.generate_complete_explanation(
                sample_idx=idx,
                x=x,
                feature_names=feature_names,
                metadata=metadata,
                top_k_features=top_k_features,
                top_k_timesteps=top_k_timesteps
            )
            
            explanations.append(explanation)
        
        return explanations
    
    def print_explanation(self, explanation: Dict):
        """
        Pretty print a single explanation
        """
        print("=" * 60)
        print(f"🔍 EXPLICATION COMPLÈTE - Sample {explanation['sample_idx']}")
        print("=" * 60)
        print(explanation['summary'])
        print("=" * 60)
    
    def export_explanations_to_json(
        self,
        explanations: List[Dict],
        filepath: str
    ):
        """
        Export explanations to JSON file
        """
        import json
        
        # Convert numpy arrays to lists for JSON serialization
        def convert_to_serializable(obj):
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, dict):
                return {k: convert_to_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_to_serializable(item) for item in obj]
            return obj
        
        serializable_explanations = convert_to_serializable(explanations)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(serializable_explanations, f, indent=2, ensure_ascii=False)
        
        print(f"   💾 Exported {len(explanations)} explanations to {filepath}")
