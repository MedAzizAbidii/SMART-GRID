"""
Configuration file for smart grid simulation
"""
class Config:
    # Network configuration
    NUM_BUSES = 14
    BASE_VOLTAGE_KV = 230
    BASE_FREQUENCY_HZ = 60
    SAMPLING_RATE_HZ = 50
    
    # Producer configuration
    PRODUCERS = [
        {"id": "G1", "name": "Gas Plant 1", "bus": 1, "type": "gas", "capacity_mw": 100, "cost_per_mwh": 50},
        {"id": "G2", "name": "Gas Plant 2", "bus": 2, "type": "gas", "capacity_mw": 80, "cost_per_mwh": 55},
        {"id": "SOLAR", "name": "Solar Farm", "bus": 3, "type": "solar", "capacity_mw": 50, "cost_per_mwh": 30},
        {"id": "WIND", "name": "Wind Farm", "bus": 6, "type": "wind", "capacity_mw": 80, "cost_per_mwh": 35},
        {"id": "HYDRO", "name": "Hydro Plant", "bus": 8, "type": "hydro", "capacity_mw": 30, "cost_per_mwh": 40}
    ]
    
    # Smart meters distribution per bus
    SMART_METERS_PER_BUS = {
        1: 500, 2: 2150, 3: 2600, 4: 3080, 5: 2000,
        6: 2500, 7: 1050, 8: 1270, 9: 1590, 10: 2920,
        11: 1160, 12: 1380, 13: 940, 14: 730
    }
    TOTAL_SMART_METERS = sum(SMART_METERS_PER_BUS.values())
    
    # Consumer type distribution (percentage)
    CONSUMER_TYPES = {
        "residential": 0.60,  # 60%
        "commercial": 0.25,   # 25%
        "industrial": 0.15    # 15%
    }
    
    # Prosumer configuration
    PROSUMER_PERCENTAGE = 0.15  # 15% of residential have solar panels
    SOLAR_CAPACITY_KW = 5.0     # 5 kW per prosumer
    
    # Attack configuration
    ATTACK_SCENARIOS = [
        {"name": "FDIA_subtle", "type": "fdia", "magnitude": 0.1, "duration": 60},
        {"name": "FDIA_aggressive", "type": "fdia", "magnitude": 0.3, "duration": 30},
        {"name": "DoS_light", "type": "dos", "packet_loss": 0.3, "duration": 60},
        {"name": "DoS_heavy", "type": "dos", "packet_loss": 0.6, "duration": 30}
    ]
    
    # Output directories
    DATA_DIR = "./data"
    CLEAN_DIR = f"{DATA_DIR}/clean"
    ATTACK_DIR = f"{DATA_DIR}/attacks"
    METADATA_DIR = f"{DATA_DIR}/metadata"
    IMAGES_DIR = "./images"
    
    # Simulation parameters
    SIMULATION_HOURS = 24
    SIMULATION_STEPS = int(SAMPLING_RATE_HZ * 3600 * SIMULATION_HOURS)  # 50Hz * 3600s * 24h
