"""
Step 11: Evaluation Metrics
"""
import numpy as np
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report
)
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict


class ModelEvaluator:
    """
    Comprehensive evaluation of anomaly detection model
    """
    
    def __init__(self):
        self.metrics = {}
        
    def compute_metrics(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        y_scores: np.ndarray = None
    ) -> Dict:
        """
        Compute all evaluation metrics
        
        Args:
            y_true: True labels
            y_pred: Predicted labels
            y_scores: Anomaly scores (for ROC-AUC)
        
        Returns:
            metrics: Dictionary of all metrics
        """
        metrics = {
            'accuracy': accuracy_score(y_true, y_pred),
            'precision': precision_score(y_true, y_pred, zero_division=0),
            'recall': recall_score(y_true, y_pred, zero_division=0),
            'f1_score': f1_score(y_true, y_pred, zero_division=0),
        }
        
        # ROC-AUC (requires scores)
        if y_scores is not None:
            try:
                metrics['roc_auc'] = roc_auc_score(y_true, y_scores)
            except:
                metrics['roc_auc'] = None
        
        # Confusion matrix
        cm = confusion_matrix(y_true, y_pred)
        metrics['confusion_matrix'] = cm
        
        if cm.shape == (2, 2):
            tn, fp, fn, tp = cm.ravel()
            metrics['true_negatives'] = int(tn)
            metrics['false_positives'] = int(fp)
            metrics['false_negatives'] = int(fn)
            metrics['true_positives'] = int(tp)
            
            # Additional metrics
            metrics['specificity'] = tn / (tn + fp) if (tn + fp) > 0 else 0
            metrics['false_positive_rate'] = fp / (fp + tn) if (fp + tn) > 0 else 0
        
        self.metrics = metrics
        return metrics
    
    def print_metrics(self, metrics: Dict = None):
        """
        Pretty print evaluation metrics
        """
        if metrics is None:
            metrics = self.metrics
        
        print("\n" + "=" * 60)
        print("📊 EVALUATION METRICS")
        print("=" * 60)
        
        print(f"\n🎯 Classification Metrics:")
        print(f"   • Accuracy:  {metrics['accuracy']:.4f}")
        print(f"   • Precision: {metrics['precision']:.4f}")
        print(f"   • Recall:    {metrics['recall']:.4f}")
        print(f"   • F1-Score:  {metrics['f1_score']:.4f}")
        
        if 'roc_auc' in metrics and metrics['roc_auc'] is not None:
            print(f"   • ROC-AUC:   {metrics['roc_auc']:.4f}")
        
        if 'true_positives' in metrics:
            print(f"\n📈 Confusion Matrix:")
            print(f"   • True Positives:  {metrics['true_positives']}")
            print(f"   • True Negatives:  {metrics['true_negatives']}")
            print(f"   • False Positives: {metrics['false_positives']}")
            print(f"   • False Negatives: {metrics['false_negatives']}")
            print(f"   • Specificity:     {metrics['specificity']:.4f}")
            print(f"   • FPR:             {metrics['false_positive_rate']:.4f}")
        
        print("=" * 60)
    
    def plot_confusion_matrix(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        save_path: str = None
    ):
        """
        Visualize confusion matrix
        """
        cm = confusion_matrix(y_true, y_pred)
        
        plt.figure(figsize=(8, 6))
        sns.heatmap(
            cm,
            annot=True,
            fmt='d',
            cmap='Blues',
            xticklabels=['Normal', 'Anomaly'],
            yticklabels=['Normal', 'Anomaly'],
            cbar_kws={'label': 'Count'}
        )
        
        plt.title('Confusion Matrix', fontsize=14, fontweight='bold')
        plt.ylabel('True Label', fontsize=12)
        plt.xlabel('Predicted Label', fontsize=12)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"   💾 Saved confusion matrix to {save_path}")
        
        plt.close()
    
    def plot_roc_curve(
        self,
        y_true: np.ndarray,
        y_scores: np.ndarray,
        save_path: str = None
    ):
        """
        Plot ROC curve
        """
        from sklearn.metrics import roc_curve, auc
        
        fpr, tpr, thresholds = roc_curve(y_true, y_scores)
        roc_auc = auc(fpr, tpr)
        
        plt.figure(figsize=(8, 6))
        plt.plot(fpr, tpr, color='darkorange', lw=2, label=f'ROC curve (AUC = {roc_auc:.3f})')
        plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--', label='Random')
        
        plt.xlim([0.0, 1.0])
        plt.ylim([0.0, 1.05])
        plt.xlabel('False Positive Rate', fontsize=12)
        plt.ylabel('True Positive Rate', fontsize=12)
        plt.title('ROC Curve', fontsize=14, fontweight='bold')
        plt.legend(loc="lower right")
        plt.grid(alpha=0.3)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"   💾 Saved ROC curve to {save_path}")
        
        plt.close()
    
    def plot_reconstruction_error_distribution(
        self,
        errors_normal: np.ndarray,
        errors_anomaly: np.ndarray,
        threshold: float,
        save_path: str = None
    ):
        """
        Plot distribution of reconstruction errors
        """
        plt.figure(figsize=(10, 6))
        
        plt.hist(errors_normal, bins=50, alpha=0.6, label='Normal', color='green', density=True)
        plt.hist(errors_anomaly, bins=50, alpha=0.6, label='Anomaly', color='red', density=True)
        plt.axvline(threshold, color='black', linestyle='--', linewidth=2, label=f'Threshold={threshold:.4f}')
        
        plt.xlabel('Reconstruction Error', fontsize=12)
        plt.ylabel('Density', fontsize=12)
        plt.title('Reconstruction Error Distribution', fontsize=14, fontweight='bold')
        plt.legend()
        plt.grid(alpha=0.3)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"   💾 Saved error distribution to {save_path}")
        
        plt.close()
