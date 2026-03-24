# Smart Grid Simulation for Anomaly Detection

## Project Overview
This project simulates a complete smart grid with:
- IEEE 14-bus power system
- 5 electricity producers (gas, solar, wind, hydro)
- 35,000 smart meters
- Realistic load profiles (residential, commercial, industrial)
- Prosumers with solar panels
- Attack scenarios (FDIA, DoS)

## Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or .\venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Generate datasets only
```bash
python run_simulation.py --hours 24 --sampling_rate 50
```

### Skip visualization
```bash
python run_simulation.py --hours 24 --no_visualize
```

### Custom output directory
```bash
python run_simulation.py --hours 24 --output_dir ./my_data
```

## Output Structure
```
data/
├── clean/
│   └── smartgrid_clean_24h.csv
├── attacks/
│   ├── attack_FDIA_subtle.csv
│   ├── attack_FDIA_aggressive.csv
│   ├── attack_DoS_light.csv
│   ├── attack_DoS_heavy.csv
│   └── attacks_complete.csv
├── metadata/
│   └── dataset_metadata.json
images/
├── voltage_distribution.png
├── consumption_by_type.png
├── attack_distribution.png
├── timeseries_bus_5.png
└── correlation_matrix.png
```

## Dataset Features
- **timestamp**: Simulation time
- **meter_id**: Unique meter identifier
- **bus_id**: Bus connection (1-14)
- **consumer_type**: residential/commercial/industrial
- **consumption_kw**: Power consumption in kW
- **voltage_pu**: Voltage in per unit
- **frequency_hz**: Grid frequency
- **has_solar**: Whether meter has solar panels
- **is_anomalous**: Attack flag
- **attack_type**: Type of attack (normal/fdia/dos)

## Project Components

### 1. Config (`config.py`)
- Network parameters (IEEE 14-bus)
- Producer configurations
- Smart meter distribution
- Attack scenarios
- Output directories

### 2. Smart Grid Components (`components/`)
- **Producer**: Gas, solar, wind, hydro generators
- **SmartMeter**: Consumption modeling with anomalies
- **LoadProfileGenerator**: Realistic load patterns

### 3. Power Flow Solver (`components/grid_connection.py`)
- PyPowSyBl integration
- Power flow calculations
- Bus voltage and line flow analysis

### 4. Simulation Engine (`simulation/complete_smart_grid_simulator.py`)
- Complete grid simulation
- Producer output calculation
- Load aggregation
- Meter reading collection
- Attack scenario generation

### 5. Data Generation (`data_generation/generate_datasets.py`)
- Clean dataset generation
- Attack scenario generation
- Metadata creation

### 6. Visualization (`visualization/visualize_data.py`)
- Voltage distributions
- Consumption analysis
- Attack patterns
- Time series visualization
- Correlation analysis

## Features

### Realistic Load Profiles
- **Residential**: Morning (7-9) and evening (18-22) peaks
- **Commercial**: Midday peaks (10-16)
- **Industrial**: Constant working hours (6-22)

### Producer Models
- **Gas Plants**: Base load with peaking capability
- **Solar**: Sun-position dependent with cloud effects
- **Wind**: Weibull distribution pattern
- **Hydro**: Constant with seasonal variations

### Attack Scenarios
- **FDIA (False Data Injection)**: Subtle and aggressive variants
- **DoS (Denial of Service)**: Light and heavy packet loss

### Prosumers
- 15% of residential consumers with solar panels
- 2-8 kW solar capacity per household

## Use Cases
- Machine learning model training
- Anomaly detection algorithm evaluation
- Grid stability analysis
- Attack resilience testing
- Load forecasting

---

For your thesis project on "Anomaly Detection in Smart Grids using AI and Blockchain", this simulation provides:
- **35,000 smart meters** for training AI models
- **Multiple attack scenarios** for detection algorithm testing
- **Realistic grid dynamics** for validation
- **Comprehensive metadata** for blockchain integration
- **Visualization tools** for result analysis

Run `python run_simulation.py` to generate the complete dataset.
