# Smart Meter Architecture Proposal

## 1. Current project analysis

The project already has strong building blocks:

- `components/` models producers, smart meters and load behavior
- `simulation/` generates grid-wide telemetry
- `data_generation/` exports CSV datasets
- `api_server.py` replays data and streams alerts to a dashboard

The main gap is architectural focus.

The current code is good for grid-level replay, but the business need is now more specific:

- one smart meter must observe multiple end devices
- incidents must be injected in a realistic scenario
- alerts should be raised as if they were sent to a phone
- the collected data must become AI-ready CSV files

## 2. Main issues to fix over time

- The project mixes infrastructure, simulation, dashboard and scenario logic in the same layer.
- The existing smart meter model is mostly aggregate and does not keep a clear per-device trace.
- The AI dataset pipeline is not isolated from the rest of the demo stack.
- Phone alerting exists conceptually, but there was no dedicated scenario pipeline producing alert logs together with CSV data.

## 3. Recommended target architecture

```text
smartgrid_simulation/
|-- components/                # existing grid and producer models
|-- simulation/                # existing grid-level simulator
|-- data_generation/           # existing dataset generation
|-- smart_meter_scenarios/     # new business-scenario layer
|   |-- models.py              # domain objects: device, meter, incident, scenario
|   |-- catalog.py             # reusable scenario definitions
|   `-- simulator.py           # scenario runner + CSV export
|-- run_smart_meter_scenario.py
`-- docs/SMART_METER_ARCHITECTURE.md
```

## 4. Data flow for the AI pipeline

```text
Scenario definition
    ->
Smart meter simulation by timestep
    ->
Multi-device energy aggregation
    ->
Incident injection
    ->
Phone-style alert generation
    ->
CSV export
    ->
AI training / anomaly detection
```

## 5. Suggested first business scenario

Scenario name:

- `residential_block_incident_day`

What it simulates:

- 3 smart meters
- multiple devices per meter
- solar generation on some meters
- 3 incident types:
  - overload
  - power theft
  - voltage sag
- phone-style alerts when an incident starts

Why this scenario is useful:

- it gives normal data and anomalous data in the same timeline
- it produces explainable labels for AI
- it keeps the dataset small enough to inspect manually
- it can later be connected to FastAPI, Packet Tracer, Twilio or a mobile app

## 6. Exported files

- `meter_readings.csv`
  - main dataset for AI training
- `device_readings.csv`
  - detailed per-device trace for debugging and explainability
- `phone_alerts.csv`
  - simulated phone notifications
- `scenario_summary.json`
  - metadata about the generated run

## 7. Command to generate data

```bash
python run_smart_meter_scenario.py --scenario residential_block_incident_day --hours 24 --interval_minutes 15
```

## 8. Next recommended step

After validating the CSV structure, the next layer should be:

1. feature engineering
2. model training
3. live inference on incoming meter data
4. real phone notification integration

## 9. Blockchain / Proof of Authority layer

The next security layer is a private blockchain that anchors the smart-meter CSV rows into immutable blocks.

Flow:

```text
donnees_smart_meters.csv
  ->
row hashing and normalization
  ->
block grouping
  ->
Proof-of-Authority sealing
  ->
block hash + authority signature
  ->
ledger JSON export
```

Command:

```bash
python run_blockchain_poa.py --input donnees_smart_meters.csv --output data/blockchain/smart_meter_chain.json --block-size 100
```

The PoA layer is for integrity and traceability. It does not replace the CSV, but it gives the dataset a verifiable chain of custody.

Privacy note:

- Keep the source CSV outside git if it contains real or sensitive data.
- Commit only the code, schema, and documentation.
- Store the generated ledger JSON and per-block files in ignored output folders.

One-command private workflow:

```bash
python run_private_blockchain.py --source donnees_smart_meters.csv
```

The script copies the CSV into a private folder under your home directory and then builds the PoA ledger there.
