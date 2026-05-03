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

### Live terminal diagram

```bash
python run_live_network_diagram.py --frames 12 --delay 0.8
```

This prints a live terminal view of:

- electricity providers
- the IEEE 14-bus grid
- smart meters and devices
- the detector action that marks `NORMAL` or `ALERTE`

### Real-time monitor mode

```bash
python run_live_network_diagram.py --monitor --delay 1 --no-clear
```

Run `smart_meters_simulator.py` in another terminal first. This mode follows the CSV output as it grows and updates the workflow view live.

## Silicon Apocalypse Integration

This project is now integrated with the Cisco Packet Tracer project from:

- `https://github.com/gowtham2thrive/Silicon-Apocalypse`

The integration maps Silicon Apocalypse zones to smart-grid buses and injects
live attack/safe telemetry into the Smart Grid API.

### Zone Mapping

- `sector_a -> bus 5`
- `sector_b -> bus 8`
- `sector_c -> bus 11`
- `sector_d -> bus 14`
- `perimeter -> bus 6`
- `garage -> bus 4`
- `entrance -> bus 3`

### Run Integrated Demo

```bash
# 1) Start API + dashboard
python run_demo.py

# 2) Send one Code Red event (motion detected)
python silicon_apocalypse_bridge.py --zone sector_a --motion --severity 0.85

# 3) Send SAFE event (motion cleared)
python silicon_apocalypse_bridge.py --zone sector_a --safe

# 4) Continuous random event stream
python silicon_apocalypse_bridge.py --loop --interval 5
```

### API Endpoint

- `POST /api/integrations/silicon-apocalypse/event`

Example payload:

```json
{
	"zone": "sector_a",
	"motion_detected": true,
	"sensor_id": "sector_a_sensor",
	"severity": 0.82,
	"consumption_kw": 8.6,
	"voltage_v": 227.4,
	"timestamp": 1760000000.0
}
```

## Blockchain Layer: Proof of Authority

The smart-meter CSV data can be anchored into a private Proof-of-Authority ledger. In this project, the blockchain is used for integrity and traceability: each CSV row is hashed, grouped into blocks, and sealed by an authorized validator. This is not public mining.

### Git-safe private data workflow

- Keep the raw CSV outside the repository if it contains private data.
- Pass the absolute path to `--input` when you build the ledger.
- Keep the generated blockchain outputs under `data/` or another ignored folder.
- Do not commit `donnees_smart_meters.csv`, `alertes_smart_meters.csv`, `logs_smart_meters.txt`, or `smart_meters_state.json`.

### Build the ledger

```bash
python run_blockchain_poa.py --input donnees_smart_meters.csv --output data/blockchain/smart_meter_chain.json --block-size 100
```

### Quick test on a sample

```bash
python run_blockchain_poa.py --input donnees_smart_meters.csv --output data/blockchain/test_chain.json --block-size 50 --max-rows 200
```

### One-command private workflow

```bash
python run_private_blockchain.py --source donnees_smart_meters.csv
```

This copies the CSV into a private folder under your home directory, then writes the ledger JSON and per-block files there too. If your source CSV is elsewhere, pass its full path with `--source`.

Each blockchain run also writes `block_hashes.csv` inside the block folder. The file is structured to show the block type, block file name, row range, counts, hashes, and proposer in a single table.

### Full smart-meter workflow

Run the simulator, dashboard, blockchain export, and Pinata uploads together:

```bash
python run_smart_meters_workflow.py
```

This launcher starts `smart_meters_simulator.py`, opens the dashboard through `run_demo.py`, watches `smart_meters_state.json` for each completed simulator iteration, rebuilds the PoA ledger from `donnees_smart_meters.csv`, and uploads both the CSV and `block_hashes.csv` to Pinata when the required passphrase and credentials are available.

Every new blockchain block JSON is uploaded too, using the raw upload mode, so each block created by the ledger gets its own Pinata record.

The hash summary file is now `block_hashes.csv`, and it is uploaded raw as well.

The workflow polls the simulator state file every 0.5 seconds by default, so the hash CSV is regenerated and uploaded as soon as a new simulator iteration is detected.

Required environment variables for uploads:

- `SMARTGRID_IPFS_PASSPHRASE`
- `PINATA_JWT` or `PINATA_API_KEY` plus `PINATA_API_SECRET`

To watch the upload activity, run `python show_pinata_upload_logs.py --follow` and tail the log stored at `SMARTGRID_PRIVATE/smartgrid_simulation/ipfs/pinata_upload.log`.

### Encrypted IPFS workflow

Use this when you want decentralized storage without exposing the raw CSV:

1. Keep the raw CSV outside the public repo, or at least keep it ignored by git.
2. Choose a storage backend:
	- Local IPFS: start a node with `ipfs daemon`
	- Pinata: set `PINATA_JWT` or `PINATA_API_KEY` plus `PINATA_API_SECRET`
3. Put the passphrase and credentials in a local `.env` file, or set them in PowerShell:

```ini
SMARTGRID_IPFS_PASSPHRASE=your-strong-passphrase
PINATA_JWT=your-jwt
PINATA_API_KEY=your-api-key
PINATA_API_SECRET=your-api-secret
```

4. Encrypt and upload the file:

```bash
python run_private_ipfs.py --source C:\path\to\donnees_smart_meters.csv --upload --provider pinata
```

If you want to use a custom env file, pass it with `--env-file`.

For local IPFS instead, use `--provider local`.

The script writes only the encrypted blob and a private manifest under `SMARTGRID_PRIVATE` in your home folder. The CID points to the encrypted file, not the raw CSV.

If the CSV was already committed to git, remove it from tracking before publishing:

```bash
git rm --cached donnees_smart_meters.csv
```

If the file was already pushed publicly, you also need to rewrite history before making the repo public.

### What is stored in the chain

- CSV row index and source file
- Meter ID, zone, meter type, consumption, voltage, current
- Detection status and anomaly text
- Row hash, block hash, and authority signature
- Block trace fields such as row range and alert count
