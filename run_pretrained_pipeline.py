"""
🚀 PRE-TRAINED TRANSFORMER PIPELINE
Uses transfer learning with BERT-style encoder for improved performance
"""
import os
import torch
import numpy as np
import pandas as pd
from torch.utils.data import DataLoader, TensorDataset
import warnings
warnings.filterwarnings('ignore')

# Import pipeline components
from ml_pipeline.config_ml import MLConfig
from ml_pipeline.data_preprocessing import SmartGridDataPreprocessor
from ml_pipeline.pretrained_transformer import (
    PretrainedTransformerAutoencoder,
    PretrainedTransformerTrainer,
    create_pretrained_model
)
from ml_pipeline.anomaly_detection import AnomalyDetector
from ml_pipeline.enhanced_anomaly_detection import EnhancedSmartGridAnomalyDetector
from ml_pipeline.evaluation import ModelEvaluator
from ml_pipeline.enhanced_evaluation import EnhancedEvaluator


def create_dataloaders(X, y, batch_size=64, shuffle=True):
    """Create PyTorch DataLoader"""
    X_tensor = torch.FloatTensor(X)
    y_tensor = torch.LongTensor(y)
    dataset = TensorDataset(X_tensor, y_tensor)
    return DataLoader(dataset, batch_size=batch_size, shuffle=shuffle)


def main():
    print("=" * 80)
    print("🚀 SMART GRID ANOMALY DETECTION - PRE-TRAINED TRANSFORMER")
    print("=" * 80)
    
    # Configuration
    config = MLConfig()
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"\n⚙️ Device: {device}")
    
    # Create directories
    os.makedirs(config.MODEL_SAVE_PATH, exist_ok=True)
    os.makedirs(config.RESULTS_PATH, exist_ok=True)
    os.makedirs(config.PLOTS_PATH, exist_ok=True)
    
    # ========================================================================
    # STEP 1-3: Data Preprocessing
    # ========================================================================
    print("\n" + "=" * 80)
    print("STEP 1-3: DATA PREPROCESSING")
    print("=" * 80)
    
    # Load balanced training data
    data_path = "balanced_training_data.csv"
    if not os.path.exists(data_path):
        print(f"❌ Error: {data_path} not found!")
        print(f"   Run: py -3.10-64 generate_balanced_data.py")
        return
    
    print(f"\n📂 Loading balanced data from {data_path}...")
    df = pd.read_csv(data_path, nrows=100000)  # Load 100k rows
    print(f"   ✅ Loaded {len(df):,} records")
    print(f"   📊 Anomaly rate: {(df['statut']=='ALERTE').sum()/len(df)*100:.1f}%")
    
    # Save sample
    sample_path = "donnees_smart_meters_sample.csv"
    df.to_csv(sample_path, index=False)
    
    # Prepare dataset
    preprocessor = SmartGridDataPreprocessor(sequence_length=config.SEQUENCE_LENGTH)
    dataset = preprocessor.prepare_dataset(sample_path, config.FEATURES)
    
    X_train = dataset['X_train']
    y_train = dataset['y_train']
    X_val = dataset['X_val']
    y_val = dataset['y_val']
    X_test = dataset['X_test']
    y_test = dataset['y_test']
    feature_names = dataset['feature_names']
    
    # Create DataLoaders
    train_loader = create_dataloaders(X_train, y_train, config.BATCH_SIZE, shuffle=True)
    val_loader = create_dataloaders(X_val, y_val, config.BATCH_SIZE, shuffle=False)
    test_loader = create_dataloaders(X_test, y_test, config.BATCH_SIZE, shuffle=False)
    
    # ========================================================================
    # STEP 4: Pre-trained Transformer Model
    # ========================================================================
    print("\n" + "=" * 80)
    print("STEP 4: PRE-TRAINED TRANSFORMER AUTOENCODER MODEL")
    print("=" * 80)
    
    n_features = X_train.shape[2]
    
    # Create pre-trained model
    model = create_pretrained_model(n_features, config)
    
    print(f"\n📐 Model Architecture:")
    print(f"   • Input features: {n_features}")
    print(f"   • Embedding dimension: {config.D_MODEL}")
    print(f"   • Attention heads: {config.N_HEADS}")
    print(f"   • BERT encoder layers: 4 (pre-trained style)")
    print(f"   • Decoder layers: {config.N_ENCODER_LAYERS}")
    print(f"   • Total parameters: {sum(p.numel() for p in model.parameters()):,}")
    print(f"   • Trainable parameters: {sum(p.numel() for p in model.parameters() if p.requires_grad):,}")
    
    # Train model
    trainer = PretrainedTransformerTrainer(
        model,
        device=device,
        learning_rate=config.LEARNING_RATE
    )
    
    history = trainer.train(
        train_loader,
        val_loader,
        epochs=min(30, config.EPOCHS),  # Max 30 epochs
        patience=10
    )
    
    # Load best model
    model.load_state_dict(torch.load('ml_pipeline/models/best_pretrained_transformer.pth'))
    model.eval()
    
    # ========================================================================
    # STEP 5: Enhanced Anomaly Detection
    # ========================================================================
    print("\n" + "=" * 80)
    print("STEP 5: ENHANCED MULTI-CRITERIA ANOMALY DETECTION")
    print("=" * 80)
    
    # Create anomaly detector wrapper for pre-trained model
    class PretrainedAnomalyDetector:
        def __init__(self, model, device='cpu'):
            self.model = model
            self.device = device
            
        def compute_reconstruction_errors(self, data_loader):
            """Compute reconstruction errors"""
            self.model.eval()
            errors = []
            
            with torch.no_grad():
                for batch_data, _ in data_loader:
                    batch_data = batch_data.to(self.device)
                    reconstructed = self.model(batch_data)
                    
                    # Compute MSE per sample
                    mse = torch.mean((batch_data - reconstructed) ** 2, dim=(1, 2))
                    errors.extend(mse.cpu().numpy())
            
            return np.array(errors)
    
    # Initialize detector
    pretrained_detector = PretrainedAnomalyDetector(model, device=device)
    
    print("\n🔍 Computing reconstruction errors...")
    val_errors = pretrained_detector.compute_reconstruction_errors(val_loader)
    test_errors = pretrained_detector.compute_reconstruction_errors(test_loader)
    
    # Initialize enhanced detector
    enhanced_detector = EnhancedSmartGridAnomalyDetector()
    
    # Get test data as DataFrame for enhanced detection
    print("\n📊 Preparing data for enhanced detection...")
    test_data = pd.read_csv(sample_path)
    test_size = len(X_test)
    test_data = test_data.tail(test_size).reset_index(drop=True)
    
    # Compute baseline statistics from validation data
    val_size = len(X_val)
    val_data = test_data.head(val_size)
    enhanced_detector.compute_statistics(val_data)
    
    # Run enhanced detection on test set
    anomaly_scores = enhanced_detector.detect_anomalies(
        test_errors, 
        test_data,
        threshold_percentile=config.RECONSTRUCTION_THRESHOLD_PERCENTILE
    )
    
    # Get predictions
    y_pred = enhanced_detector.get_predictions(anomaly_scores)
    confidence_scores = enhanced_detector.get_confidence_scores(anomaly_scores)
    
    print(f"\n   ✅ Enhanced detection complete:")
    print(f"      • Detected {y_pred.sum()} anomalies out of {len(y_pred)} samples")
    print(f"      • Detection rate: {y_pred.mean()*100:.2f}%")
    
    # Export detailed results
    detailed_results_path = os.path.join(config.RESULTS_PATH, 'pretrained_detailed_anomalies.csv')
    enhanced_detector.export_detailed_results(anomaly_scores, detailed_results_path)
    
    # ========================================================================
    # STEP 11: Model Evaluation
    # ========================================================================
    print("\n" + "=" * 80)
    print("STEP 11: MODEL EVALUATION")
    print("=" * 80)
    
    # Basic evaluation
    evaluator = ModelEvaluator()
    metrics = evaluator.compute_metrics(y_test, y_pred, confidence_scores)
    evaluator.print_metrics(metrics)
    
    # Save basic visualizations
    evaluator.plot_confusion_matrix(
        y_test, y_pred,
        save_path=os.path.join(config.PLOTS_PATH, 'pretrained_confusion_matrix.png')
    )
    
    evaluator.plot_roc_curve(
        y_test, confidence_scores,
        save_path=os.path.join(config.PLOTS_PATH, 'pretrained_roc_curve.png')
    )
    
    # Plot error distribution
    normal_scores = confidence_scores[y_test == 0]
    anomaly_scores_array = confidence_scores[y_test == 1]
    evaluator.plot_reconstruction_error_distribution(
        normal_scores, anomaly_scores_array, 0.5,
        save_path=os.path.join(config.PLOTS_PATH, 'pretrained_error_distribution.png')
    )
    
    # ========================================================================
    # Enhanced Evaluation - Anomaly Type Breakdown
    # ========================================================================
    print("\n" + "=" * 80)
    print("ENHANCED EVALUATION - ANOMALY TYPE ANALYSIS")
    print("=" * 80)
    
    enhanced_evaluator = EnhancedEvaluator()
    
    # Analyze by type
    print("\n📊 Analyzing performance by anomaly type...")
    type_analysis = enhanced_evaluator.analyze_by_type(anomaly_scores, y_test)
    print("\n" + type_analysis.to_string(index=False))
    
    # Analyze criterion contribution
    print("\n\n📊 Analyzing detection criterion contribution...")
    criterion_analysis = enhanced_evaluator.analyze_criterion_contribution(anomaly_scores)
    print("\n" + criterion_analysis.to_string(index=False))
    
    # Generate enhanced visualizations
    print("\n\n📈 Generating enhanced visualizations...")
    enhanced_evaluator.plot_criterion_heatmap(
        anomaly_scores,
        save_path=os.path.join(config.PLOTS_PATH, 'pretrained_criterion_heatmap.png')
    )
    
    enhanced_evaluator.plot_anomaly_type_distribution(
        anomaly_scores,
        save_path=os.path.join(config.PLOTS_PATH, 'pretrained_anomaly_type_distribution.png')
    )
    
    enhanced_evaluator.plot_confidence_distribution(
        anomaly_scores, y_test,
        save_path=os.path.join(config.PLOTS_PATH, 'pretrained_confidence_distribution.png')
    )
    
    # Generate comprehensive report
    report_path = os.path.join(config.RESULTS_PATH, 'pretrained_evaluation_report.txt')
    enhanced_evaluator.generate_report(anomaly_scores, y_test, report_path)
    
    # ========================================================================
    # COMPARISON WITH BASELINE
    # ========================================================================
    print("\n" + "=" * 80)
    print("📊 COMPARISON WITH BASELINE MODEL")
    print("=" * 80)
    
    # Try to load baseline results for comparison
    baseline_results_path = os.path.join(config.RESULTS_PATH, 'detailed_anomalies.csv')
    if os.path.exists(baseline_results_path):
        print("\n📈 Comparing with baseline (from-scratch) model...")
        baseline_df = pd.read_csv(baseline_results_path)
        
        # Load baseline metrics (if available)
        print("\n   Pre-trained Model vs Baseline:")
        print(f"   • Accuracy: {metrics['accuracy']:.4f}")
        print(f"   • Precision: {metrics['precision']:.4f}")
        print(f"   • Recall: {metrics['recall']:.4f}")
        print(f"   • F1-Score: {metrics['f1_score']:.4f}")
        if metrics.get('roc_auc'):
            print(f"   • ROC-AUC: {metrics['roc_auc']:.4f}")
    else:
        print("\n   ℹ️ No baseline results found for comparison")
        print("   Run 'py -3.10-64 run_ml_pipeline_fast.py' to generate baseline")
    
    # ========================================================================
    # FINAL SUMMARY
    # ========================================================================
    print("\n" + "=" * 80)
    print("✅ PRE-TRAINED PIPELINE COMPLETE")
    print("=" * 80)
    
    print(f"\n📁 Results saved to:")
    print(f"   • Model: {config.MODEL_SAVE_PATH}best_pretrained_transformer.pth")
    print(f"   • Plots: {config.PLOTS_PATH}pretrained_*.png")
    print(f"   • Report: {config.RESULTS_PATH}pretrained_evaluation_report.txt")
    
    print(f"\n📊 Final Performance:")
    print(f"   • Accuracy: {metrics['accuracy']:.4f}")
    print(f"   • Precision: {metrics['precision']:.4f}")
    print(f"   • Recall: {metrics['recall']:.4f}")
    print(f"   • F1-Score: {metrics['f1_score']:.4f}")
    if metrics.get('roc_auc'):
        print(f"   • ROC-AUC: {metrics['roc_auc']:.4f}")
    
    print("\n" + "=" * 80)
    print("💡 Next Steps:")
    print("   1. Compare results with baseline model")
    print("   2. Update smart_meters_simulator.py to use pre-trained model")
    print("   3. Generate comparison report for academic presentation")
    print("=" * 80)


if __name__ == "__main__":
    main()
