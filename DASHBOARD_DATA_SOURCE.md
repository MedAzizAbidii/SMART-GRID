# Dashboard Data Source Explanation

## ❌ CURRENT SITUATION

### What the Dashboard Shows:
The dashboard at **http://127.0.0.1:8000/dashboard** is displaying:
- **OLD grid simulation data** from `data/clean/smartgrid_clean_fast.csv`
- 14-bus IEEE power system data
- Attack simulation data from `data/attacks/attacks_fast.csv`
- **NOT your real-time smart meter data**
- **NOT your enhanced anomaly detection results**

### What Your Smart Meter Simulator Generates:
Your `smart_meters_simulator.py` is generating:
- ✅ Real-time smart meter readings (100 meters)
- ✅ Enhanced anomaly detection with 7 criteria
- ✅ ML-based detection (Transformer model)
- ✅ Saved to `donnees_smart_meters.csv`
- ✅ Enhanced results in `enhanced_detection_results.csv`

## 🔍 THE PROBLEM

**Two Different Systems:**

1. **Grid Simulation System** (Old)
   - 14-bus IEEE power system
   - Voltage, frequency, power flow
   - Dashboard: `/dashboard`
   - Data: `data/clean/` and `data/attacks/`

2. **Smart Meter System** (Your Current Work)
   - 100 smart meters
   - Enhanced anomaly detection
   - Dashboard: **NONE** (not connected)
   - Data: `donnees_smart_meters.csv` + `enhanced_detection_results.csv`

## ✅ SOLUTION OPTIONS

### Option 1: View Smart Meter Data via API (Current)
You can access your real smart meter data through the API:

**API Endpoint:**
```
http://127.0.0.1:8000/api/smart-meters/status
```

**What it shows:**
- Total readings count
- Total alerts count
- Alert rate percentage
- Latest reading with all fields
- Recent alerts (last 8)
- Meter type distribution
- Status counts (NORMAL vs ALERTE)

**Example Response:**
```json
{
  "source": {
    "data_file": "donnees_smart_meters.csv",
    "available": true,
    "last_update": "2026-05-11 16:47:55"
  },
  "summary": {
    "total_readings": 700000,
    "total_alerts": 85000,
    "alert_rate": 12.14,
    "status_counts": {
      "NORMAL": 615000,
      "ALERTE": 85000
    }
  },
  "latest_reading": {
    "timestamp": "2026-05-11 16:47:55",
    "meter_id": "SM_0050",
    "zone": "Zone B",
    "type": "industriel",
    "consommation_kw": 16.52,
    "tension_v": 238.9,
    "courant_a": 69.15,
    "statut": "NORMAL",
    "anomalies": "none"
  }
}
```

### Option 2: Create Dedicated Smart Meter Dashboard (Recommended)
Create a new HTML dashboard specifically for smart meter data that shows:
- Real-time meter readings
- Enhanced detection results
- All 7 criteria scores
- Anomaly type breakdown
- Confidence scores
- Live updates via WebSocket

### Option 3: Modify Existing Dashboard
Modify the current dashboard to switch between:
- Grid simulation view (14 buses)
- Smart meter view (100 meters)

## 📊 CURRENT DATA ACCESS

### To View Your Smart Meter Data:

**1. Via API (JSON format):**
```bash
curl http://127.0.0.1:8000/api/smart-meters/status
```

**2. Via CSV Files:**
- Main data: `donnees_smart_meters.csv`
- Enhanced results: `enhanced_detection_results.csv`

**3. Via Console Output:**
- Watch the simulator terminal for real-time alerts
- Green `[BASIC]` alerts
- Red `[ENHANCED]` alerts with type and confidence

### To View Enhanced Detection Results:
```python
import pandas as pd

# Load enhanced results
df = pd.read_csv('enhanced_detection_results.csv')

# Show only anomalies
anomalies = df[df['is_anomaly'] == 1]
print(f"Total anomalies: {len(anomalies)}")
print(f"Anomaly rate: {len(anomalies)/len(df)*100:.2f}%")

# Show anomaly types
print("\nAnomaly types:")
print(anomalies['anomaly_type'].value_counts())

# Show recent anomalies
print("\nRecent anomalies:")
print(anomalies[['timestamp', 'meter_id', 'anomaly_type', 'confidence']].tail(10))
```

## 🎯 RECOMMENDATION

**For your project, I recommend creating a dedicated Smart Meter Dashboard** that:

1. **Connects to your real data:**
   - Reads from `donnees_smart_meters.csv`
   - Reads from `enhanced_detection_results.csv`
   - Uses WebSocket for live updates

2. **Shows enhanced detection:**
   - All 7 criteria scores
   - Anomaly type classification
   - Confidence levels
   - Real-time alerts

3. **Visualizations:**
   - Meter status grid (100 meters)
   - Anomaly timeline
   - Detection criteria breakdown
   - Alert rate trends
   - Zone-based analysis

Would you like me to create this dedicated dashboard for you?

## 📝 SUMMARY

**Question:** Is the dashboard showing data from the real enhanced detection script?

**Answer:** **NO** - The current dashboard (`/dashboard`) shows old grid simulation data, NOT your smart meter data with enhanced detection.

**Your enhanced detection data is:**
- ✅ Being generated correctly
- ✅ Being saved to CSV files
- ✅ Available via API endpoint `/api/smart-meters/status`
- ❌ NOT displayed in the visual dashboard yet

**To see your enhanced detection results visually, you need:**
- A dedicated smart meter dashboard (I can create this)
- OR use the API endpoint to view JSON data
- OR read the CSV files directly
