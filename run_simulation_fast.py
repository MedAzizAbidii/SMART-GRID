#!/usr/bin/env python3
"""
Fast smart grid simulation - optimized for quick testing
Collects hourly readings instead of per-timestep
"""
import sys
import os
import argparse
import pandas as pd
import numpy as np
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import Config
from components.smart_grid_components import Producer, SmartMeter


def generate_fast_dataset(hours=2):
    """
    Fast dataset generation - hourly readings instead of per-sample
    """
    print("="*70)
    print("🚀 FAST SMART GRID SIMULATION FOR ANOMALY DETECTION")
    print("="*70)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Simulation: {hours} hours (HOURLY READINGS)")
    print("="*70)
    
    config = Config()
    
    # Initialize producers
    producers = []
    for prod_config in config.PRODUCERS:
        producer = Producer(
            producer_id=prod_config["id"],
            name=prod_config["name"],
            bus_id=prod_config["bus"],
            producer_type=prod_config["type"],
            capacity_mw=prod_config["capacity_mw"],
            cost_per_mwh=prod_config["cost_per_mwh"]
        )
        producers.append(producer)
    
    # Initialize smart meters (full)
    smart_meters = []
    meter_counter = 0
    
    for bus_id, num_meters in config.SMART_METERS_PER_BUS.items():
        for _ in range(num_meters):
            rand = np.random.random()
            if rand < config.CONSUMER_TYPES["residential"]:
                consumer_type = "residential"
                base_load = np.random.uniform(1.0, 3.0)
            elif rand < config.CONSUMER_TYPES["residential"] + config.CONSUMER_TYPES["commercial"]:
                consumer_type = "commercial"
                base_load = np.random.uniform(5.0, 20.0)
            else:
                consumer_type = "industrial"
                base_load = np.random.uniform(20.0, 100.0)
            
            has_solar = False
            solar_capacity = 0
            if consumer_type == "residential" and np.random.random() < config.PROSUMER_PERCENTAGE:
                has_solar = True
                solar_capacity = np.random.uniform(2.0, 8.0)
            
            meter = SmartMeter(
                meter_id=f"SMT_{meter_counter:06d}",
                bus_id=bus_id,
                consumer_type=consumer_type,
                base_load_kw=base_load,
                has_solar=has_solar,
                solar_capacity_kw=solar_capacity
            )
            smart_meters.append(meter)
            meter_counter += 1
    
    print(f"\n✅ Initialized: {len(producers)} producers, {len(smart_meters):,} smart meters")
    
    # ============ CLEAN DATASET ============
    print("\n" + "="*70)
    print("📊 GENERATING CLEAN DATASET")
    print("="*70)
    
    clean_data = []
    
    for hour in range(hours):
        for producer in producers:
            producer.current_output_mw = producer.get_output_at_hour(float(hour))
        
        # Sample meters (take 10% for faster processing, or ~2400 meters)
        sample_size = max(100, len(smart_meters) // 10)
        sampled_meters = np.random.choice(smart_meters, size=min(sample_size, len(smart_meters)), replace=False)
        
        for meter in sampled_meters:
            consumption = meter.get_consumption_at_hour(float(hour))
            voltage = 1.0 + np.random.normal(0, 0.01)
            
            clean_data.append({
                'timestamp': hour,
                'hour': hour,
                'meter_id': meter.meter_id,
                'bus_id': meter.bus_id,
                'consumer_type': meter.consumer_type,
                'consumption_kw': consumption,
                'voltage_pu': voltage,
                'frequency_hz': 60.0 + np.random.normal(0, 0.01),
                'has_solar': meter.has_solar,
                'is_anomalous': False,
                'attack_type': 'normal'
            })
        
        print(f"  Hour {hour+1}/{hours} - {len(sampled_meters):,} meter readings")
    
    clean_df = pd.DataFrame(clean_data)
    print(f"\n✅ Clean dataset: {len(clean_df):,} total readings")
    
    # Save clean dataset
    os.makedirs(config.CLEAN_DIR, exist_ok=True)
    clean_path = os.path.join(config.CLEAN_DIR, "smartgrid_clean_fast.csv")
    clean_df.to_csv(clean_path, index=False)
    print(f"💾 Saved: {clean_path}")
    
    # ============ ATTACK DATASET ============
    print("\n" + "="*70)
    print("⚔️ GENERATING ATTACK DATASETS")
    print("="*70)
    
    attack_data = []
    target_buses = [5, 8, 11]  # FDIA targets
    sample_size = max(100, len(smart_meters) // 10)
    
    for scenario in config.ATTACK_SCENARIOS:
        print(f"\n🔴 {scenario['name']}:")
        
        for hour in range(hours):
            for producer in producers:
                producer.current_output_mw = producer.get_output_at_hour(float(hour))
            
            # Sample meters
            sampled_meters = np.random.choice(smart_meters, size=min(sample_size, len(smart_meters)), replace=False)
            
            for meter in sampled_meters:
                consumption = meter.get_consumption_at_hour(float(hour))
                voltage = 1.0 + np.random.normal(0, 0.01)
                
                # Apply attack
                is_attack = False
                if scenario['type'] == 'fdia' and meter.bus_id in target_buses:
                    magnitude = scenario.get('magnitude', 0.2)
                    consumption *= (1 + magnitude)
                    is_attack = True
                    voltage *= (1 + magnitude * 0.05)
                
                elif scenario['type'] == 'dos' and np.random.random() < scenario.get('packet_loss', 0.3):
                    # Skip this reading (packet loss)
                    continue
                
                attack_data.append({
                    'timestamp': hour,
                    'hour': hour,
                    'meter_id': meter.meter_id,
                    'bus_id': meter.bus_id,
                    'consumer_type': meter.consumer_type,
                    'consumption_kw': consumption,
                    'voltage_pu': voltage,
                    'frequency_hz': 60.0 + np.random.normal(0, 0.01),
                    'has_solar': meter.has_solar,
                    'is_anomalous': is_attack,
                    'attack_type': scenario['type'],
                    'attack_name': scenario['name']
                })
        
        print(f"   ✅ Generated readings")
    
    attack_df = pd.DataFrame(attack_data)
    print(f"\n✅ Attack dataset: {len(attack_df):,} total readings")
    
    # Save attack dataset
    os.makedirs(config.ATTACK_DIR, exist_ok=True)
    attack_path = os.path.join(config.ATTACK_DIR, "attacks_fast.csv")
    attack_df.to_csv(attack_path, index=False)
    print(f"💾 Saved: {attack_path}")
    
    # Save metadata
    import json
    os.makedirs(config.METADATA_DIR, exist_ok=True)
    metadata = {
        "project": "Smart Grid Anomaly Detection (FAST VERSION)",
        "timestamp": datetime.now().isoformat(),
        "hours": hours,
        "smart_meters": len(smart_meters),
        "sampling": "10% per hour",
        "clean_samples": len(clean_df),
        "attack_samples": len(attack_df),
        "files": {
            "clean": clean_path,
            "attacks": attack_path
        }
    }
    metadata_path = os.path.join(config.METADATA_DIR, "metadata_fast.json")
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"📋 Saved: {metadata_path}")
    
    print("\n" + "="*70)
    print("✅ FAST SIMULATION COMPLETE!")
    print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    return clean_df, attack_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run fast smart-grid dataset generation")
    parser.add_argument("--hours", type=int, default=2, help="Number of hours to simulate")
    args = parser.parse_args()

    clean_df, attack_df = generate_fast_dataset(hours=args.hours)
