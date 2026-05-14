"""
Generate Balanced Training Data for Smart Meter Anomaly Detection
Creates dataset with 30% anomalies (instead of current 5-10%)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

def generate_balanced_smart_meter_data(
    num_meters=100,
    hours=48,
    anomaly_rate=0.30
):
    """
    Generate balanced dataset with specified anomaly rate
    
    Args:
        num_meters: Number of smart meters (default: 100)
        hours: Hours of data to generate (default: 48)
        anomaly_rate: Percentage of anomalies (default: 0.30 = 30%)
    
    Returns:
        DataFrame with balanced normal and anomaly samples
    """
    
    print(f"🔄 Generating balanced training data...")
    print(f"   Meters: {num_meters}")
    print(f"   Duration: {hours} hours")
    print(f"   Target anomaly rate: {anomaly_rate*100:.1f}%")
    print()
    
    data = []
    start_time = datetime.now()
    
    zones = ['Zone A', 'Zone B', 'Zone C', 'Zone D']
    types = ['residentiel', 'commercial', 'industriel']
    
    # Generate readings every minute
    total_readings = hours * 60 * num_meters
    progress_step = total_readings // 20  # Show progress 20 times
    
    reading_count = 0
    
    for minute in range(hours * 60):
        timestamp = start_time + timedelta(minutes=minute)
        
        for meter_id in range(1, num_meters + 1):
            reading_count += 1
            
            # Show progress
            if reading_count % progress_step == 0:
                progress = (reading_count / total_readings) * 100
                print(f"   Progress: {progress:.0f}% ({reading_count:,}/{total_readings:,})")
            
            meter_name = f"SM_{meter_id:04d}"
            zone = random.choice(zones)
            meter_type = random.choice(types)
            
            # Base consumption by type
            if meter_type == 'residentiel':
                base_consumption = random.uniform(0.5, 5.0)
            elif meter_type == 'commercial':
                base_consumption = random.uniform(3.0, 12.0)
            else:  # industriel
                base_consumption = random.uniform(10.0, 40.0)
            
            # Normal values
            voltage = random.uniform(220, 240)
            power_factor = random.uniform(0.85, 0.98)
            frequency = random.uniform(59.5, 60.5)
            
            # Decide if this is an anomaly
            is_anomaly = random.random() < anomaly_rate
            
            if is_anomaly:
                # Generate different types of anomalies
                anomaly_type = random.choice([
                    'voltage_high', 'voltage_low', 
                    'consumption_spike', 'consumption_drop',
                    'power_factor_low', 'frequency_deviation',
                    'combined'  # Multiple anomalies at once
                ])
                
                if anomaly_type == 'voltage_high':
                    voltage = random.uniform(253, 270)  # Over IEEE limit
                    anomalies = 'voltage_high'
                    
                elif anomaly_type == 'voltage_low':
                    voltage = random.uniform(180, 207)  # Under IEEE limit
                    anomalies = 'voltage_low'
                    
                elif anomaly_type == 'consumption_spike':
                    base_consumption *= random.uniform(3.0, 8.0)  # 3-8x spike
                    anomalies = 'consumption_spike'
                    
                elif anomaly_type == 'consumption_drop':
                    base_consumption *= random.uniform(0.05, 0.2)  # Drop to 5-20%
                    anomalies = 'consumption_drop'
                    
                elif anomaly_type == 'power_factor_low':
                    power_factor = random.uniform(0.3, 0.7)  # Low power factor
                    anomalies = 'power_factor_low'
                    
                elif anomaly_type == 'frequency_deviation':
                    frequency = random.choice([
                        random.uniform(58.0, 59.4),  # Too low
                        random.uniform(60.6, 62.0)   # Too high
                    ])
                    anomalies = 'frequency_deviation'
                    
                else:  # combined anomalies
                    voltage = random.uniform(253, 265)
                    base_consumption *= random.uniform(2.5, 5.0)
                    power_factor = random.uniform(0.4, 0.75)
                    anomalies = 'combined'
                
                statut = 'ALERTE'
            else:
                anomalies = 'none'
                statut = 'NORMAL'
            
            # Calculate current (I = P / (V * PF))
            current = (base_consumption * 1000) / (voltage * power_factor)
            
            data.append({
                'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'meter_id': meter_name,
                'zone': zone,
                'type': meter_type,
                'consommation_kw': round(base_consumption, 3),
                'tension_v': round(voltage, 2),
                'courant_a': round(current, 3),
                'facteur_puissance': round(power_factor, 3),
                'frequence_hz': round(frequency, 2),
                'statut': statut,
                'anomalies': anomalies
            })
    
    print(f"   Progress: 100% ({total_readings:,}/{total_readings:,})")
    print()
    
    return pd.DataFrame(data)


if __name__ == "__main__":
    print("=" * 70)
    print("BALANCED TRAINING DATA GENERATOR")
    print("=" * 70)
    print()
    
    # Generate balanced dataset
    df = generate_balanced_smart_meter_data(
        num_meters=100,
        hours=48,  # 48 hours of data
        anomaly_rate=0.30  # 30% anomalies
    )
    
    # Save to file
    output_file = 'balanced_training_data.csv'
    df.to_csv(output_file, index=False)
    
    # Statistics
    normal_count = len(df[df['statut'] == 'NORMAL'])
    anomaly_count = len(df[df['statut'] == 'ALERTE'])
    
    print("=" * 70)
    print("✅ DATA GENERATION COMPLETE!")
    print("=" * 70)
    print()
    print(f"📊 Statistics:")
    print(f"   Total rows: {len(df):,}")
    print(f"   Normal: {normal_count:,} ({normal_count/len(df)*100:.1f}%)")
    print(f"   Anomalies: {anomaly_count:,} ({anomaly_count/len(df)*100:.1f}%)")
    print()
    
    print(f"📁 File saved: {output_file}")
    print(f"   Size: {df.memory_usage(deep=True).sum() / (1024*1024):.2f} MB")
    print()
    
    # Anomaly type breakdown
    print(f"🔍 Anomaly Type Distribution:")
    anomaly_types = df[df['statut'] == 'ALERTE']['anomalies'].value_counts()
    for anom_type, count in anomaly_types.items():
        print(f"   {anom_type}: {count:,} ({count/anomaly_count*100:.1f}%)")
    print()
    
    # Meter type distribution
    print(f"📊 Meter Type Distribution:")
    meter_types = df['type'].value_counts()
    for meter_type, count in meter_types.items():
        print(f"   {meter_type}: {count:,} ({count/len(df)*100:.1f}%)")
    print()
    
    print("=" * 70)
    print("NEXT STEPS:")
    print("=" * 70)
    print()
    print("1. Verify the data:")
    print(f"   py -3.10-64 -c \"import pandas as pd; df=pd.read_csv('{output_file}'); print(df.head())\"")
    print()
    print("2. Retrain the model:")
    print("   - Edit run_ml_pipeline_fast.py")
    print(f"   - Change data file to: '{output_file}'")
    print("   - Run: py -3.10-64 run_ml_pipeline_fast.py")
    print()
    print("3. Expected improvements:")
    print("   - Accuracy: 22% → 65-75%")
    print("   - Recall: 5% → 45-60%")
    print("   - F1-Score: 9% → 50-65%")
    print()
    print("=" * 70)
