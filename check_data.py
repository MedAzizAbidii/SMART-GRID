import pandas as pd

# Load the data
df = pd.read_csv('donnees_smart_meters.csv')

print("=" * 60)
print("SMART METER DATA ANALYSIS")
print("=" * 60)
print(f"\nTotal rows: {len(df):,}")
print(f"File size: 56.9 MB")
print(f"\nColumns: {list(df.columns)}")
print(f"\nDate range:")
print(f"  From: {df['timestamp'].min()}")
print(f"  To:   {df['timestamp'].max()}")

print(f"\nData types:")
for col in df.columns:
    print(f"  {col}: {df[col].dtype}")

print(f"\nMissing values:")
print(df.isnull().sum())

print(f"\nStatus distribution:")
if 'statut' in df.columns:
    print(df['statut'].value_counts())

print(f"\nMeter type distribution:")
if 'type' in df.columns:
    print(df['type'].value_counts())

print("\n" + "=" * 60)
print("MODEL STATUS")
print("=" * 60)

import os
model_path = 'ml_pipeline/models/best_transformer.pth'
if os.path.exists(model_path):
    model_size = os.path.getsize(model_path) / (1024 * 1024)
    model_time = os.path.getmtime(model_path)
    from datetime import datetime
    model_date = datetime.fromtimestamp(model_time)
    
    print(f"\n✅ Model exists: {model_path}")
    print(f"   Size: {model_size:.2f} MB")
    print(f"   Last trained: {model_date}")
    
    data_time = os.path.getmtime('donnees_smart_meters.csv')
    data_date = datetime.fromtimestamp(data_time)
    
    print(f"\n📊 Data file:")
    print(f"   Last modified: {data_date}")
    
    if data_time > model_time:
        print(f"\n⚠️  DATA IS NEWER THAN MODEL!")
        print(f"   Model trained: {model_date}")
        print(f"   Data updated:  {data_date}")
        print(f"   Recommendation: RETRAIN THE MODEL with new data")
    else:
        print(f"\n✅ Model is up-to-date with current data")
else:
    print(f"\n❌ Model not found: {model_path}")
    print(f"   Recommendation: TRAIN THE MODEL")

print("\n" + "=" * 60)
print("RECOMMENDATION")
print("=" * 60)

# Check if we have enough data
if len(df) >= 50000:
    print(f"\n✅ You have {len(df):,} rows - EXCELLENT for training!")
    print(f"   Recommended: Use 80% for training, 20% for validation")
    print(f"   Training samples: ~{int(len(df) * 0.8):,}")
    print(f"   Validation samples: ~{int(len(df) * 0.2):,}")
else:
    print(f"\n⚠️  You have {len(df):,} rows")
    print(f"   Minimum recommended: 50,000 rows")
    print(f"   Current: {len(df):,} rows")

print("\n" + "=" * 60)
