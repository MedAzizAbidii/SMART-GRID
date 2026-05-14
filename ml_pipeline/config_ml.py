"""
Configuration for ML Pipeline
"""

class MLConfig:
    # Data Configuration
    SEQUENCE_LENGTH = 20  # Number of timesteps per sequence
    BATCH_SIZE = 64
    TRAIN_SPLIT = 0.7
    VAL_SPLIT = 0.15
    TEST_SPLIT = 0.15
    
    # Feature Configuration
    FEATURES = [
        'consommation_kw',
        'tension_v',
        'courant_a',
        'hour_sin',
        'hour_cos',
        'day_of_week',
        'is_weekend',
        'zone_encoded',
        'type_encoded',
        'consumption_rolling_mean',
        'consumption_rolling_std',
        'voltage_rolling_mean',
        'consumption_diff',
        'consumption_rate_change'
    ]
    
    # Transformer Configuration
    D_MODEL = 128  # Embedding dimension
    N_HEADS = 8  # Number of attention heads
    N_ENCODER_LAYERS = 4
    D_FF = 512  # Feedforward dimension
    DROPOUT = 0.1
    MAX_SEQ_LENGTH = 100
    
    # Training Configuration
    EPOCHS = 50
    LEARNING_RATE = 0.0001
    WEIGHT_DECAY = 1e-5
    EARLY_STOPPING_PATIENCE = 10
    
    # Anomaly Detection Configuration
    RECONSTRUCTION_THRESHOLD_PERCENTILE = 95
    DYNAMIC_THRESHOLD_MULTIPLIER = 2.0  # mean + 2*std
    
    # SHAP Configuration
    SHAP_BACKGROUND_SAMPLES = 100
    SHAP_TEST_SAMPLES = 50
    
    # Paths
    MODEL_SAVE_PATH = "./ml_pipeline/models/"
    RESULTS_PATH = "./ml_pipeline/results/"
    PLOTS_PATH = "./ml_pipeline/plots/"
