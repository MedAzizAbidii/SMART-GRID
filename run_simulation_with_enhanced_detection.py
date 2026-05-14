"""
🔥 SMART GRID SIMULATION WITH ENHANCED ANOMALY DETECTION
Complete simulation integrating smart meters with real-time anomaly detection
"""
import os
import sys
import time
import torch
import numpy as np
import pandas as pd
from datetime import datetime
from torch.utils.data import DataLoader, TensorDataset
import warnings
warnings.filterwarnings('ignore')

# Import smart grid components
from components.smart_grid_components import SmartMeter, Producer

# Import ML pipeline components
from ml_pipeline.config_ml import MLConfig
from ml_pipeline.data_preprocessing import SmartGridDataPreprocessor
from ml_pipeline.transformer_model import TransformerAutoencoder, TransformerTrainer
from ml_pipeline.anomaly_detection import AnomalyDetector
from ml_pipeline.enhanced_anomaly_detection import EnhancedSmartGridAnomalyDetector
from ml_pipeline.evaluation import ModelEvaluator
from ml_pipeline.enhanced_evaluation import EnhancedEvaluator


def print_header(text):
    """Print formatted header"""
    print("\n" + "=" * 80)
    print(text)
    print("=" * 80)


def create_dataloaders(X, y, batch_size=64, shuffle=True):
    """Create PyTorch DataLoader"""
    X_tensor = torch.FloatTensor(X)
    y_tensor = torch.LongTensor(y)
    dataset = TensorDataset(X_tensor, y_tensor)
    return DataLoader(dataset, batch_size=batch_size, shuffle=shuffle)


def load_or_train_model(config, X_train, y_train, X_val, y_val, device='cpu'):
    """Load existing model or train new one"""
    model_path = os.path.join(config.MODEL_SAVE_PATH, 'best_transformer.pth')
    
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
    
    if os.path.exists(model_path):
        print(f"\n✅ Loading existing model from: {model_path}")
        model.load_state_dict(torch.load(model_path, map_location=device))
        model.to(device)
        model.eval()
        return model
    else:
        print(f"\n⚠️ No existing model found. Training new model...")
        train_loader = create_dataloaders(X_train, y_train, config.BATCH_SIZE, shuffle=True)
        val_loader = create_dataloaders(X_val, y_val, config.BATCH_SIZE, shuffle=False)
        
        trainer = TransformerTrainer(model, device=device)
        trainer.fit(
            train_loader,
            val_loader,
            epochs=min(20, config.EPOCHS),
            learning_rate=config.LEARNING_RATE,
            patience=5
        )
        return model


def simulate_smart_meters(n_meters=100, duration_hours=24):
    """
    Simulate smart meter data generation
    
    Args:
        n_meters: Number of smart meters to simulate
        duration_hours: Duration of simulation in hours
    
    Returns:
        DataFrame with simulated data
    """
    print(f"\n🏭 Simulating {n_meters} smart meters for {duration_hours} hours...")
    
    # Create smart meters
    meters = []
    meter_types = ['residentiel', 'commercial', 'industriel']
    zones = ['zone_A', 'zone_B', 'zone_C', 'zone_D']
    
    for i in range(n_meters):
        meter_id = f"SM_{i+1:04d}"
        meter_type = np.random.choice(meter_types)
        zone = np.random.choice(zones)
        bus_id = np.random.randint(1, 15)  # IEEE 14-bus system
        
        # Base load varies by type
        if meter_type == 'residentiel':
            base_load = np.random.uniform(3, 8)  # 3-8 kW
        elif meter_type == 'commercial':
            base_load = np.random.uniform(15, 40)  # 15-40 kW
        else:  # industriel
            base_load = np.random.uniform(50, 150)  # 50-150 kW
        
        # Some meters have solar
        has_solar = np.random.random() < 0.2  # 20% have solar
        solar_capacity = np.random.uniform(2, 5) if has_solar else 0
        
        meter = SmartMeter(
            meter_id=meter_id,
            bus_id=bus_id,
            consumer_type=meter_type,
            base_load_kw=base_load,
            has_solar=has_solar,
            solar_capacity_kw=solar_capacity
        )
        
        # Randomly inject anomalies (20% of meters with more severe anomalies)
        if np.random.random() < 0.2:
            meter.set_anomaly(magnitude=np.random.uniform(0.5, 1.2))
        
        meters.append((meter, zone))
    
    # Simulate data collection
    simulated_data = []
    timesteps = duration_hours * 4  # 15-minute intervals
    
    print(f"   • Generating {timesteps} timesteps (15-min intervals)...")
    
    for t in range(timesteps):
        hour = (t // 4) % 24
        minute = (t % 4) * 15
        timestamp = f"2026-05-11 {hour:02d}:{minute:02d}:00"
        
        for meter, zone in meters:
            # Get consumption
            consumption = meter.get_consumption_at_hour(hour)
            
            # Generate voltage (230V ± variations)
            voltage = np.random.normal(230, 5)
            
            # Add anomalies
            if meter.is_anomalous:
                # Voltage anomalies
                if np.random.random() < 0.3:
                    voltage = np.random.choice([
                        np.random.uniform(190, 205),  # Under-voltage
                        np.random.uniform(255, 270)   # Over-voltage
                    ])
            
            # Calculate current (I = P / V)
            current = (consumption * 1000) / voltage if voltage > 0 else 0
            
            # Power factor (typically 0.85-0.95)
            power_factor = np.random.uniform(0.85, 0.95)
            if meter.is_anomalous and np.random.random() < 0.2:
                power_factor = np.random.uniform(0.6, 0.8)  # Low power factor
            
            # Frequency (60 Hz ± small variations)
            frequency = np.random.normal(60.0, 0.2)
            if meter.is_anomalous and np.random.random() < 0.1:
                frequency = np.random.uniform(58.5, 61.5)  # Frequency deviation
            
            # Status
            status = 'anomalie' if meter.is_anomalous else 'normal'
            
            # Add to dataset
            simulated_data.append({
                'timestamp': timestamp,
                'meter_id': meter.meter_id,
                'type': meter.consumer_type,
                'zone': zone,
                'consommation_kw': consumption,
                'tension_v': voltage,
                'courant_a': current,
                'facteur_puissance': power_factor,
                'frequency_hz': frequency,
                'status': status
            })
        
        # Progress indicator
        if (t + 1) % 24 == 0:
            progress = (t + 1) / timesteps * 100
            print(f"   • Progress: {progress:.1f}% ({t+1}/{timesteps} timesteps)")
    
    df = pd.DataFrame(simulated_data)
    print(f"\n   ✅ Simulation complete: {len(df):,} readings generated")
    
    return df


def detect_anomalies_realtime(df, model, enhanced_detector, config, device='cpu'):
    """
    Detect anomalies in simulated data using enhanced detector
    
    Args:
        df: Simulated data DataFrame
        model: Trained Transformer model
        enhanced_detector: Enhanced anomaly detector
        config: ML configuration
        device: Computing device
    
    Returns:
        DataFrame with anomaly predictions
    """
    print_header("REAL-TIME ANOMALY DETECTION")
    
    # Prepare data for detection
    print("\n📊 Preparing data for detection...")
    
    # Add derived features
    df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
    df['day_of_week'] = pd.to_datetime(df['timestamp']).dt.dayofweek
    df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
    
    # Calculate rate of change
    df = df.sort_values(['meter_id', 'timestamp'])
    df['consumption_diff'] = df.groupby('meter_id')['consommation_kw'].diff().fillna(0)
    df['consumption_rate_change'] = df.groupby('meter_id')['consommation_kw'].pct_change().fillna(0)
    
    # Compute baseline statistics
    enhanced_detector.compute_statistics(df)
    
    # Prepare sequences for ML model
    print("\n🔍 Computing ML reconstruction errors...")
    preprocessor = SmartGridDataPreprocessor(sequence_length=config.SEQUENCE_LENGTH)
    
    # Create temporary file
    temp_file = "temp_simulation_data.csv"
    df.to_csv(temp_file, index=False)
    
    # Prepare dataset
    dataset = preprocessor.prepare_dataset(temp_file, config.FEATURES)
    X_test = dataset['X_test']
    y_test = dataset['y_test']
    
    # Create DataLoader
    test_loader = create_dataloaders(X_test, y_test, config.BATCH_SIZE, shuffle=False)
    
    # Compute reconstruction errors
    basic_detector = AnomalyDetector(model, device=device)
    test_errors = basic_detector.compute_reconstruction_errors(test_loader)
    
    # Get test data subset
    test_size = len(X_test)
    test_data = df.tail(test_size).reset_index(drop=True)
    
    # Run enhanced detection
    print("\n🎯 Running enhanced multi-criteria detection...")
    anomaly_scores = enhanced_detector.detect_anomalies(
        test_errors,
        test_data,
        threshold_percentile=config.RECONSTRUCTION_THRESHOLD_PERCENTILE
    )
    
    # Get predictions
    y_pred = enhanced_detector.get_predictions(anomaly_scores)
    confidence_scores = enhanced_detector.get_confidence_scores(anomaly_scores)
    
    # Add predictions to DataFrame
    test_data['is_anomaly'] = y_pred
    test_data['anomaly_type'] = [s.anomaly_type for s in anomaly_scores]
    test_data['confidence'] = confidence_scores
    test_data['reconstruction_score'] = [s.reconstruction_error for s in anomaly_scores]
    test_data['voltage_score'] = [s.voltage_anomaly for s in anomaly_scores]
    test_data['consumption_score'] = [s.consumption_anomaly for s in anomaly_scores]
    test_data['power_factor_score'] = [s.power_factor_anomaly for s in anomaly_scores]
    test_data['frequency_score'] = [s.frequency_anomaly for s in anomaly_scores]
    test_data['temporal_score'] = [s.temporal_anomaly for s in anomaly_scores]
    test_data['rate_change_score'] = [s.rate_change_anomaly for s in anomaly_scores]
    
    # Clean up
    if os.path.exists(temp_file):
        os.remove(temp_file)
    
    return test_data, anomaly_scores, y_test


def generate_simulation_report(results_df, anomaly_scores, y_true, output_dir):
    """Generate comprehensive simulation report"""
    print_header("GENERATING SIMULATION REPORT")
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Get predictions
    y_pred = results_df['is_anomaly'].values
    
    # Basic metrics
    print("\n📊 Computing performance metrics...")
    evaluator = ModelEvaluator()
    metrics = evaluator.compute_metrics(y_true, y_pred, results_df['confidence'].values)
    evaluator.print_metrics(metrics)
    
    # Enhanced evaluation
    print("\n📊 Generating enhanced evaluation...")
    enhanced_evaluator = EnhancedEvaluator()
    
    # Analyze by type
    type_analysis = enhanced_evaluator.analyze_by_type(anomaly_scores, y_true)
    print("\n" + type_analysis.to_string(index=False))
    
    # Analyze criterion contribution
    criterion_analysis = enhanced_evaluator.analyze_criterion_contribution(anomaly_scores)
    print("\n" + criterion_analysis.to_string(index=False))
    
    # Generate visualizations
    print("\n📈 Generating visualizations...")
    plots_dir = os.path.join(output_dir, 'plots')
    os.makedirs(plots_dir, exist_ok=True)
    
    evaluator.plot_confusion_matrix(
        y_true, y_pred,
        save_path=os.path.join(plots_dir, 'confusion_matrix.png')
    )
    
    evaluator.plot_roc_curve(
        y_true, results_df['confidence'].values,
        save_path=os.path.join(plots_dir, 'roc_curve.png')
    )
    
    enhanced_evaluator.plot_criterion_heatmap(
        anomaly_scores,
        save_path=os.path.join(plots_dir, 'criterion_heatmap.png')
    )
    
    enhanced_evaluator.plot_anomaly_type_distribution(
        anomaly_scores,
        save_path=os.path.join(plots_dir, 'anomaly_type_distribution.png')
    )
    
    enhanced_evaluator.plot_confidence_distribution(
        anomaly_scores, y_true,
        save_path=os.path.join(plots_dir, 'confidence_distribution.png')
    )
    
    # Save detailed results
    print("\n💾 Saving detailed results...")
    results_file = os.path.join(output_dir, 'simulation_results.csv')
    results_df.to_csv(results_file, index=False)
    print(f"   • Results saved to: {results_file}")
    
    # Save anomaly details
    anomaly_details_file = os.path.join(output_dir, 'anomaly_details.csv')
    enhanced_detector.export_detailed_results(anomaly_scores, anomaly_details_file)
    
    # Generate comprehensive report
    report_file = os.path.join(output_dir, 'simulation_report.txt')
    enhanced_evaluator.generate_report(anomaly_scores, y_true, report_file)
    
    # Generate summary report
    summary_file = os.path.join(output_dir, 'simulation_summary.txt')
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("SMART GRID SIMULATION WITH ENHANCED ANOMALY DETECTION\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Simulation Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("SIMULATION PARAMETERS\n")
        f.write("-" * 80 + "\n")
        f.write(f"Total samples: {len(results_df):,}\n")
        f.write(f"Unique meters: {results_df['meter_id'].nunique()}\n")
        f.write(f"Time range: {results_df['timestamp'].min()} to {results_df['timestamp'].max()}\n\n")
        
        f.write("DETECTION RESULTS\n")
        f.write("-" * 80 + "\n")
        f.write(f"Anomalies detected: {y_pred.sum():,} ({y_pred.mean()*100:.2f}%)\n")
        f.write(f"True anomalies: {y_true.sum():,} ({y_true.mean()*100:.2f}%)\n\n")
        
        f.write("PERFORMANCE METRICS\n")
        f.write("-" * 80 + "\n")
        f.write(f"Accuracy:  {metrics['accuracy']*100:.2f}%\n")
        f.write(f"Precision: {metrics['precision']*100:.2f}%\n")
        f.write(f"Recall:    {metrics['recall']*100:.2f}%\n")
        f.write(f"F1-Score:  {metrics['f1_score']*100:.2f}%\n")
        if metrics.get('roc_auc'):
            f.write(f"ROC-AUC:   {metrics['roc_auc']*100:.2f}%\n")
        
        f.write("\n" + "=" * 80 + "\n")
    
    print(f"   • Summary saved to: {summary_file}")
    
    return metrics


def main():
    """Main simulation function"""
    print("=" * 80)
    print("🔥 SMART GRID SIMULATION WITH ENHANCED ANOMALY DETECTION")
    print("=" * 80)
    print(f"\n⏰ Simulation started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Configuration
    config = MLConfig()
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"⚙️ Device: {device}")
    
    # Create directories
    output_dir = "simulation_results"
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(config.MODEL_SAVE_PATH, exist_ok=True)
    
    # ========================================================================
    # STEP 1: Load or Train Model
    # ========================================================================
    print_header("STEP 1: LOAD/TRAIN ANOMALY DETECTION MODEL")
    
    # Check if we have existing data and model
    data_path = "donnees_smart_meters.csv"
    if not os.path.exists(data_path):
        print(f"\n⚠️ Warning: {data_path} not found!")
        print("   Using simulation data only (no pre-trained model)")
        model = None
    else:
        # Load sample data for training
        print(f"\n📂 Loading training data from {data_path}...")
        df_train = pd.read_csv(data_path, nrows=50000)
        
        # Prepare dataset
        preprocessor = SmartGridDataPreprocessor(sequence_length=config.SEQUENCE_LENGTH)
        sample_path = "temp_training_sample.csv"
        df_train.to_csv(sample_path, index=False)
        
        dataset = preprocessor.prepare_dataset(sample_path, config.FEATURES)
        X_train = dataset['X_train']
        y_train = dataset['y_train']
        X_val = dataset['X_val']
        y_val = dataset['y_val']
        
        # Load or train model
        model = load_or_train_model(config, X_train, y_train, X_val, y_val, device)
        
        # Clean up
        if os.path.exists(sample_path):
            os.remove(sample_path)
    
    # ========================================================================
    # STEP 2: Initialize Enhanced Detector
    # ========================================================================
    print_header("STEP 2: INITIALIZE ENHANCED ANOMALY DETECTOR")
    
    global enhanced_detector
    enhanced_detector = EnhancedSmartGridAnomalyDetector()
    print("\n✅ Enhanced detector initialized with 7 detection criteria:")
    print("   1. ML Reconstruction Error (20%)")
    print("   2. Voltage Anomalies (20%)")
    print("   3. Consumption Anomalies (15%)")
    print("   4. Power Factor Anomalies (15%)")
    print("   5. Frequency Anomalies (15%)")
    print("   6. Temporal Anomalies (10%)")
    print("   7. Rate of Change Anomalies (5%)")
    
    # ========================================================================
    # STEP 3: Simulate Smart Meters
    # ========================================================================
    print_header("STEP 3: SIMULATE SMART METER DATA")
    
    # Simulation parameters
    n_meters = 100  # Number of smart meters
    duration_hours = 24  # 24 hours of simulation
    
    simulated_df = simulate_smart_meters(n_meters, duration_hours)
    
    # Save simulated data
    sim_data_file = os.path.join(output_dir, 'simulated_meter_data.csv')
    simulated_df.to_csv(sim_data_file, index=False)
    print(f"\n   💾 Simulated data saved to: {sim_data_file}")
    
    # ========================================================================
    # STEP 4: Detect Anomalies
    # ========================================================================
    if model is not None:
        results_df, anomaly_scores, y_true = detect_anomalies_realtime(
            simulated_df, model, enhanced_detector, config, device
        )
        
        # ========================================================================
        # STEP 5: Generate Report
        # ========================================================================
        metrics = generate_simulation_report(results_df, anomaly_scores, y_true, output_dir)
    else:
        print("\n⚠️ Skipping anomaly detection (no trained model available)")
        print("   Run 'py -3.10-64 run_ml_pipeline_fast.py' first to train the model")
    
    # ========================================================================
    # FINAL SUMMARY
    # ========================================================================
    print_header("✅ SIMULATION COMPLETE")
    
    print(f"\n📁 Results saved to: {output_dir}/")
    print(f"   • Simulated data: simulation_results/simulated_meter_data.csv")
    if model is not None:
        print(f"   • Detection results: simulation_results/simulation_results.csv")
        print(f"   • Anomaly details: simulation_results/anomaly_details.csv")
        print(f"   • Summary report: simulation_results/simulation_summary.txt")
        print(f"   • Full report: simulation_results/simulation_report.txt")
        print(f"   • Visualizations: simulation_results/plots/")
        
        print(f"\n📊 Final Performance:")
        print(f"   • Accuracy:  {metrics['accuracy']*100:.2f}%")
        print(f"   • Precision: {metrics['precision']*100:.2f}%")
        print(f"   • Recall:    {metrics['recall']*100:.2f}%")
        print(f"   • F1-Score:  {metrics['f1_score']*100:.2f}%")
    
    print(f"\n⏰ Simulation completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Simulation interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Error during simulation: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
