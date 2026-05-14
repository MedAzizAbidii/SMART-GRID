"""
🔥 COMPLETE END-TO-END ML PIPELINE
Implements all 11 steps from the XAI-Transformer document
"""
import os
import torch
import numpy as np
from torch.utils.data import DataLoader, TensorDataset
import warnings
warnings.filterwarnings('ignore')

# Import pipeline components
from ml_pipeline.config_ml import MLConfig
from ml_pipeline.data_preprocessing import SmartGridDataPreprocessor
from ml_pipeline.transformer_model import TransformerAutoencoder, TransformerTrainer
from ml_pipeline.anomaly_detection import AnomalyDetector
from ml_pipeline.attention_explainer import AttentionExplainer
from ml_pipeline.shap_explainer import SHAPExplainer
from ml_pipeline.explanation_fusion import ExplanationFusion
from ml_pipeline.evaluation import ModelEvaluator


def create_dataloaders(X, y, batch_size=64, shuffle=True):
    """Create PyTorch DataLoader"""
    X_tensor = torch.FloatTensor(X)
    y_tensor = torch.LongTensor(y)
    dataset = TensorDataset(X_tensor, y_tensor)
    return DataLoader(dataset, batch_size=batch_size, shuffle=shuffle)


def main():
    print("=" * 80)
    print("🔥 SMART GRID ANOMALY DETECTION - XAI TRANSFORMER PIPELINE")
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
    # STEP 1-3: Data Collection, Preprocessing, Feature Engineering
    # ========================================================================
    print("\n" + "=" * 80)
    print("STEP 1-3: DATA PREPROCESSING & FEATURE ENGINEERING")
    print("=" * 80)
    
    preprocessor = SmartGridDataPreprocessor(sequence_length=config.SEQUENCE_LENGTH)
    
    # Load data
    data_path = "donnees_smart_meters.csv"
    if not os.path.exists(data_path):
        print(f"❌ Error: {data_path} not found!")
        print("   Please run smart_meters_simulator.py first to generate data.")
        return
    
    # Prepare dataset
    dataset = preprocessor.prepare_dataset(data_path, config.FEATURES)
    
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
    # STEP 4: Transformer Autoencoder Model
    # ========================================================================
    print("\n" + "=" * 80)
    print("STEP 4: TRANSFORMER AUTOENCODER MODEL")
    print("=" * 80)
    
    n_features = X_train.shape[2]
    
    model = TransformerAutoencoder(
        n_features=n_features,
        d_model=config.D_MODEL,
        n_heads=config.N_HEADS,
        n_encoder_layers=config.N_ENCODER_LAYERS,
        d_ff=config.D_FF,
        dropout=config.DROPOUT,
        max_seq_length=config.MAX_SEQ_LENGTH
    )
    
    print(f"\n📐 Model Architecture:")
    print(f"   • Input features: {n_features}")
    print(f"   • Embedding dimension: {config.D_MODEL}")
    print(f"   • Attention heads: {config.N_HEADS}")
    print(f"   • Encoder layers: {config.N_ENCODER_LAYERS}")
    print(f"   • Total parameters: {sum(p.numel() for p in model.parameters()):,}")
    
    # Train model
    trainer = TransformerTrainer(model, device=device)
    trainer.fit(
        train_loader,
        val_loader,
        epochs=config.EPOCHS,
        learning_rate=config.LEARNING_RATE,
        patience=config.EARLY_STOPPING_PATIENCE
    )
    
    # ========================================================================
    # STEP 5: Anomaly Detection
    # ========================================================================
    print("\n" + "=" * 80)
    print("STEP 5: ANOMALY DETECTION")
    print("=" * 80)
    
    detector = AnomalyDetector(model, device=device)
    
    # Compute reconstruction errors on validation set
    print("\n🔍 Computing reconstruction errors...")
    val_errors = detector.compute_reconstruction_errors(val_loader)
    
    # Set threshold (using percentile method)
    print("\n📊 Setting anomaly threshold...")
    detector.set_threshold_percentile(val_errors, config.RECONSTRUCTION_THRESHOLD_PERCENTILE)
    
    # Predict on test set
    print("\n🎯 Detecting anomalies on test set...")
    y_pred, test_errors = detector.predict(test_loader)
    
    print(f"   • Detected {y_pred.sum()} anomalies out of {len(y_pred)} samples")
    print(f"   • Detection rate: {y_pred.mean()*100:.2f}%")
    
    # ========================================================================
    # STEP 11: Evaluation
    # ========================================================================
    print("\n" + "=" * 80)
    print("STEP 11: MODEL EVALUATION")
    print("=" * 80)
    
    evaluator = ModelEvaluator()
    metrics = evaluator.compute_metrics(y_test, y_pred, test_errors)
    evaluator.print_metrics(metrics)
    
    # Save visualizations
    evaluator.plot_confusion_matrix(
        y_test, y_pred,
        save_path=os.path.join(config.PLOTS_PATH, 'confusion_matrix.png')
    )
    
    evaluator.plot_roc_curve(
        y_test, test_errors,
        save_path=os.path.join(config.PLOTS_PATH, 'roc_curve.png')
    )
    
    # Plot error distribution
    normal_errors = test_errors[y_test == 0]
    anomaly_errors = test_errors[y_test == 1]
    evaluator.plot_reconstruction_error_distribution(
        normal_errors, anomaly_errors, detector.threshold,
        save_path=os.path.join(config.PLOTS_PATH, 'error_distribution.png')
    )
    
    # ========================================================================
    # STEP 6: Attention Explainability
    # ========================================================================
    print("\n" + "=" * 80)
    print("STEP 6: ATTENTION EXPLAINABILITY (WHERE)")
    print("=" * 80)
    
    attention_explainer = AttentionExplainer(model, device=device)
    
    # Get anomalous samples
    anomaly_indices = np.where(y_test == 1)[0][:5]  # First 5 anomalies
    
    if len(anomaly_indices) > 0:
        print(f"\n🔦 Analyzing attention for {len(anomaly_indices)} anomalous samples...")
        
        # Visualize attention for first anomaly
        sample_idx = 0
        X_sample = torch.FloatTensor(X_test[anomaly_indices[:10]])
        attention = attention_explainer.extract_attention_weights(X_sample)
        
        attention_explainer.visualize_attention_heatmap(
            attention, sample_idx=0,
            save_path=os.path.join(config.PLOTS_PATH, 'attention_heatmap.png')
        )
        
        attention_explainer.visualize_timestep_importance(
            attention, sample_idx=0,
            save_path=os.path.join(config.PLOTS_PATH, 'timestep_importance.png')
        )
    
    # ========================================================================
    # STEP 7: SHAP Explainability
    # ========================================================================
    print("\n" + "=" * 80)
    print("STEP 7: SHAP EXPLAINABILITY (WHY)")
    print("=" * 80)
    
    shap_explainer = SHAPExplainer(model, device=device)
    
    # Initialize SHAP with background data
    print("\n🔧 Initializing SHAP explainer...")
    shap_explainer.initialize_kernel_shap(
        X_train,
        n_samples=config.SHAP_BACKGROUND_SAMPLES
    )
    
    # Compute SHAP values for test samples
    print("\n🔍 Computing SHAP values...")
    shap_values = shap_explainer.compute_shap_values(
        X_test,
        n_samples=config.SHAP_TEST_SAMPLES
    )
    
    # Get feature importance
    feature_importance = shap_explainer.get_feature_importance(
        shap_values,
        feature_names,
        config.SEQUENCE_LENGTH
    )
    
    print("\n📊 Top 10 Feature Importance (SHAP):")
    for i, (feature, importance) in enumerate(list(feature_importance.items())[:10], 1):
        print(f"   {i}. {feature}: {importance:.4f}")
    
    # Visualize feature importance
    shap_explainer.visualize_feature_importance(
        feature_importance,
        top_k=10,
        save_path=os.path.join(config.PLOTS_PATH, 'shap_feature_importance.png')
    )
    
    # ========================================================================
    # STEP 8: Fusion of Explanations
    # ========================================================================
    print("\n" + "=" * 80)
    print("STEP 8: FUSION OF EXPLANATIONS (WHERE + WHY)")
    print("=" * 80)
    
    fusion = ExplanationFusion(attention_explainer, shap_explainer)
    
    # Generate complete explanations for anomalies
    if len(anomaly_indices) > 0:
        print(f"\n🔍 Generating complete explanations for {min(3, len(anomaly_indices))} anomalies...")
        
        explanations = []
        for i, idx in enumerate(anomaly_indices[:3]):
            metadata = dataset['meta_test'][idx]
            
            explanation = fusion.generate_complete_explanation(
                sample_idx=i,
                x=X_test[anomaly_indices[:10]],
                feature_names=feature_names,
                metadata=metadata,
                top_k_features=5,
                top_k_timesteps=3
            )
            
            explanations.append(explanation)
            fusion.print_explanation(explanation)
        
        # Export explanations
        fusion.export_explanations_to_json(
            explanations,
            os.path.join(config.RESULTS_PATH, 'anomaly_explanations.json')
        )
    
    # ========================================================================
    # FINAL SUMMARY
    # ========================================================================
    print("\n" + "=" * 80)
    print("✅ PIPELINE COMPLETE")
    print("=" * 80)
    
    print(f"\n📁 Results saved to:")
    print(f"   • Models: {config.MODEL_SAVE_PATH}")
    print(f"   • Plots: {config.PLOTS_PATH}")
    print(f"   • Results: {config.RESULTS_PATH}")
    
    print(f"\n📊 Final Performance:")
    print(f"   • Accuracy: {metrics['accuracy']:.4f}")
    print(f"   • Precision: {metrics['precision']:.4f}")
    print(f"   • Recall: {metrics['recall']:.4f}")
    print(f"   • F1-Score: {metrics['f1_score']:.4f}")
    if metrics.get('roc_auc'):
        print(f"   • ROC-AUC: {metrics['roc_auc']:.4f}")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
