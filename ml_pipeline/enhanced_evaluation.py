"""
Enhanced Evaluation for Multi-Criteria Anomaly Detection
Shows breakdown by anomaly type and criterion
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from typing import List, Dict
from ml_pipeline.enhanced_anomaly_detection import AnomalyScore


class EnhancedEvaluator:
    """
    Enhanced evaluation with anomaly type breakdown
    """
    
    def __init__(self):
        self.criterion_names = {
            'reconstruction': 'ML Reconstruction',
            'voltage': 'Voltage Anomaly',
            'consumption': 'Consumption Anomaly',
            'power_factor': 'Power Factor',
            'frequency': 'Frequency Deviation',
            'temporal': 'Temporal Pattern',
            'rate_change': 'Rate of Change'
        }
    
    def analyze_by_type(self, anomaly_scores: List[AnomalyScore], y_true: np.ndarray) -> pd.DataFrame:
        """
        Analyze detection performance by anomaly type
        """
        results = []
        
        # Get predictions
        y_pred = np.array([1 if s.is_anomaly else 0 for s in anomaly_scores])
        
        # Overall metrics
        tp = np.sum((y_true == 1) & (y_pred == 1))
        fp = np.sum((y_true == 0) & (y_pred == 1))
        tn = np.sum((y_true == 0) & (y_pred == 0))
        fn = np.sum((y_true == 1) & (y_pred == 0))
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        
        results.append({
            'type': 'OVERALL',
            'count': len(y_pred),
            'detected': y_pred.sum(),
            'true_positives': tp,
            'false_positives': fp,
            'false_negatives': fn,
            'precision': precision,
            'recall': recall,
            'f1_score': f1
        })
        
        # By anomaly type
        anomaly_types = {}
        for idx, score in enumerate(anomaly_scores):
            if score.is_anomaly:
                atype = score.anomaly_type
                if atype not in anomaly_types:
                    anomaly_types[atype] = {'indices': [], 'scores': []}
                anomaly_types[atype]['indices'].append(idx)
                anomaly_types[atype]['scores'].append(score)
        
        for atype, data in anomaly_types.items():
            indices = data['indices']
            type_y_true = y_true[indices]
            type_y_pred = np.ones(len(indices))  # All predicted as anomalies
            
            tp_type = np.sum(type_y_true == 1)
            fp_type = np.sum(type_y_true == 0)
            
            precision_type = tp_type / len(indices) if len(indices) > 0 else 0
            
            results.append({
                'type': atype,
                'count': len(indices),
                'detected': len(indices),
                'true_positives': tp_type,
                'false_positives': fp_type,
                'false_negatives': 0,  # Not applicable for this breakdown
                'precision': precision_type,
                'recall': np.nan,  # Not applicable
                'f1_score': np.nan
            })
        
        return pd.DataFrame(results)
    
    def analyze_criterion_contribution(self, anomaly_scores: List[AnomalyScore]) -> pd.DataFrame:
        """
        Analyze contribution of each detection criterion
        """
        criterion_stats = {
            'reconstruction': [],
            'voltage': [],
            'consumption': [],
            'power_factor': [],
            'frequency': [],
            'temporal': [],
            'rate_change': []
        }
        
        for score in anomaly_scores:
            criterion_stats['reconstruction'].append(score.reconstruction_error)
            criterion_stats['voltage'].append(score.voltage_anomaly)
            criterion_stats['consumption'].append(score.consumption_anomaly)
            criterion_stats['power_factor'].append(score.power_factor_anomaly)
            criterion_stats['frequency'].append(score.frequency_anomaly)
            criterion_stats['temporal'].append(score.temporal_anomaly)
            criterion_stats['rate_change'].append(score.rate_change_anomaly)
        
        results = []
        for criterion, scores in criterion_stats.items():
            scores_array = np.array(scores)
            results.append({
                'criterion': self.criterion_names[criterion],
                'mean_score': scores_array.mean(),
                'std_score': scores_array.std(),
                'max_score': scores_array.max(),
                'triggered_count': np.sum(scores_array > 0.5),
                'triggered_pct': np.sum(scores_array > 0.5) / len(scores_array) * 100
            })
        
        return pd.DataFrame(results).sort_values('triggered_count', ascending=False)
    
    def plot_criterion_heatmap(self, anomaly_scores: List[AnomalyScore], save_path: str = None):
        """
        Plot heatmap of criterion scores for detected anomalies
        """
        # Get only detected anomalies
        detected = [s for s in anomaly_scores if s.is_anomaly]
        
        if len(detected) == 0:
            print("⚠️ No anomalies detected, skipping heatmap")
            return
        
        # Limit to first 100 for visualization
        detected = detected[:100]
        
        # Create matrix
        criteria = ['reconstruction', 'voltage', 'consumption', 'power_factor', 
                   'frequency', 'temporal', 'rate_change']
        
        matrix = []
        for score in detected:
            row = [
                score.reconstruction_error,
                score.voltage_anomaly,
                score.consumption_anomaly,
                score.power_factor_anomaly,
                score.frequency_anomaly,
                score.temporal_anomaly,
                score.rate_change_anomaly
            ]
            matrix.append(row)
        
        matrix = np.array(matrix).T
        
        # Plot
        plt.figure(figsize=(14, 6))
        sns.heatmap(
            matrix,
            yticklabels=[self.criterion_names[c] for c in criteria],
            cmap='YlOrRd',
            cbar_kws={'label': 'Anomaly Score'},
            vmin=0,
            vmax=1
        )
        plt.xlabel('Anomaly Sample Index')
        plt.ylabel('Detection Criterion')
        plt.title('Criterion Scores for Detected Anomalies (First 100)')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"   💾 Criterion heatmap saved to: {save_path}")
        else:
            plt.show()
        
        plt.close()
    
    def plot_anomaly_type_distribution(self, anomaly_scores: List[AnomalyScore], save_path: str = None):
        """
        Plot distribution of detected anomaly types
        """
        # Count anomaly types
        type_counts = {}
        for score in anomaly_scores:
            if score.is_anomaly:
                atype = score.anomaly_type
                type_counts[atype] = type_counts.get(atype, 0) + 1
        
        if len(type_counts) == 0:
            print("⚠️ No anomalies detected, skipping distribution plot")
            return
        
        # Sort by count
        types = list(type_counts.keys())
        counts = [type_counts[t] for t in types]
        
        # Plot
        plt.figure(figsize=(12, 6))
        colors = plt.cm.Set3(range(len(types)))
        bars = plt.bar(range(len(types)), counts, color=colors)
        
        plt.xlabel('Anomaly Type')
        plt.ylabel('Count')
        plt.title('Distribution of Detected Anomaly Types')
        plt.xticks(range(len(types)), types, rotation=45, ha='right')
        plt.grid(axis='y', alpha=0.3)
        
        # Add count labels on bars
        for bar, count in zip(bars, counts):
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height,
                    f'{int(count)}',
                    ha='center', va='bottom')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"   💾 Anomaly type distribution saved to: {save_path}")
        else:
            plt.show()
        
        plt.close()
    
    def plot_confidence_distribution(self, anomaly_scores: List[AnomalyScore], y_true: np.ndarray, save_path: str = None):
        """
        Plot confidence score distribution for true vs false positives
        """
        # Separate by prediction correctness
        y_pred = np.array([1 if s.is_anomaly else 0 for s in anomaly_scores])
        
        true_positives = []
        false_positives = []
        true_negatives = []
        false_negatives = []
        
        for idx, score in enumerate(anomaly_scores):
            if y_pred[idx] == 1 and y_true[idx] == 1:
                true_positives.append(score.total_score)
            elif y_pred[idx] == 1 and y_true[idx] == 0:
                false_positives.append(score.total_score)
            elif y_pred[idx] == 0 and y_true[idx] == 0:
                true_negatives.append(score.total_score)
            elif y_pred[idx] == 0 and y_true[idx] == 1:
                false_negatives.append(score.total_score)
        
        # Plot
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        
        # True Positives
        if len(true_positives) > 0:
            axes[0, 0].hist(true_positives, bins=30, color='green', alpha=0.7, edgecolor='black')
            axes[0, 0].axvline(0.5, color='red', linestyle='--', label='Threshold')
            axes[0, 0].set_title(f'True Positives (n={len(true_positives)})')
            axes[0, 0].set_xlabel('Confidence Score')
            axes[0, 0].set_ylabel('Count')
            axes[0, 0].legend()
        
        # False Positives
        if len(false_positives) > 0:
            axes[0, 1].hist(false_positives, bins=30, color='orange', alpha=0.7, edgecolor='black')
            axes[0, 1].axvline(0.5, color='red', linestyle='--', label='Threshold')
            axes[0, 1].set_title(f'False Positives (n={len(false_positives)})')
            axes[0, 1].set_xlabel('Confidence Score')
            axes[0, 1].set_ylabel('Count')
            axes[0, 1].legend()
        
        # True Negatives
        if len(true_negatives) > 0:
            axes[1, 0].hist(true_negatives, bins=30, color='blue', alpha=0.7, edgecolor='black')
            axes[1, 0].axvline(0.5, color='red', linestyle='--', label='Threshold')
            axes[1, 0].set_title(f'True Negatives (n={len(true_negatives)})')
            axes[1, 0].set_xlabel('Confidence Score')
            axes[1, 0].set_ylabel('Count')
            axes[1, 0].legend()
        
        # False Negatives
        if len(false_negatives) > 0:
            axes[1, 1].hist(false_negatives, bins=30, color='red', alpha=0.7, edgecolor='black')
            axes[1, 1].axvline(0.5, color='red', linestyle='--', label='Threshold')
            axes[1, 1].set_title(f'False Negatives (n={len(false_negatives)})')
            axes[1, 1].set_xlabel('Confidence Score')
            axes[1, 1].set_ylabel('Count')
            axes[1, 1].legend()
        
        plt.suptitle('Confidence Score Distribution by Prediction Type', fontsize=14, fontweight='bold')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"   💾 Confidence distribution saved to: {save_path}")
        else:
            plt.show()
        
        plt.close()
    
    def generate_report(self, anomaly_scores: List[AnomalyScore], y_true: np.ndarray, save_path: str):
        """
        Generate comprehensive evaluation report
        """
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("ENHANCED ANOMALY DETECTION - EVALUATION REPORT\n")
            f.write("=" * 80 + "\n\n")
            
            # Performance by type
            f.write("1. PERFORMANCE BY ANOMALY TYPE\n")
            f.write("-" * 80 + "\n")
            type_analysis = self.analyze_by_type(anomaly_scores, y_true)
            f.write(type_analysis.to_string(index=False))
            f.write("\n\n")
            
            # Criterion contribution
            f.write("2. DETECTION CRITERION CONTRIBUTION\n")
            f.write("-" * 80 + "\n")
            criterion_analysis = self.analyze_criterion_contribution(anomaly_scores)
            f.write(criterion_analysis.to_string(index=False))
            f.write("\n\n")
            
            # Summary statistics
            f.write("3. SUMMARY STATISTICS\n")
            f.write("-" * 80 + "\n")
            y_pred = np.array([1 if s.is_anomaly else 0 for s in anomaly_scores])
            total_scores = np.array([s.total_score for s in anomaly_scores])
            
            f.write(f"Total samples: {len(anomaly_scores):,}\n")
            f.write(f"Detected anomalies: {y_pred.sum():,} ({y_pred.mean()*100:.2f}%)\n")
            f.write(f"True anomalies: {y_true.sum():,} ({y_true.mean()*100:.2f}%)\n")
            f.write(f"\nConfidence scores:\n")
            f.write(f"  • Mean: {total_scores.mean():.4f}\n")
            f.write(f"  • Std: {total_scores.std():.4f}\n")
            f.write(f"  • Min: {total_scores.min():.4f}\n")
            f.write(f"  • Max: {total_scores.max():.4f}\n")
            
            f.write("\n" + "=" * 80 + "\n")
        
        print(f"\n   📄 Evaluation report saved to: {save_path}")
