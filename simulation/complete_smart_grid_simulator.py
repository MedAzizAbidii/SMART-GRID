"""
Complete smart grid simulation with producers and smart meters
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
from tqdm import tqdm
import random
from typing import Dict, Tuple

from config import Config
from components.smart_grid_components import Producer, SmartMeter
from components.grid_connection import PyPowSyBlInterface


class CompleteSmartGridSimulator:
    """
    Complete smart grid simulation with producers and smart meters
    """
    def __init__(self):
        self.config = Config()
        self.grid_interface = PyPowSyBlInterface()
        self.producers = []
        self.smart_meters = []
        self.current_time = 0.0
        self.current_hour = 0.0
        
        self._initialize_producers()
        self._initialize_smart_meters()
        
        print(f"✅ Simulator initialized:")
        print(f"   • {len(self.producers)} producers")
        print(f"   • {len(self.smart_meters):,} smart meters")
        print(f"   • {self.config.SAMPLING_RATE_HZ} Hz sampling rate")
    
    def _initialize_producers(self):
        """Initialize producers from configuration"""
        for prod_config in self.config.PRODUCERS:
            producer = Producer(
                producer_id=prod_config["id"],
                name=prod_config["name"],
                bus_id=prod_config["bus"],
                producer_type=prod_config["type"],
                capacity_mw=prod_config["capacity_mw"],
                cost_per_mwh=prod_config["cost_per_mwh"]
            )
            self.producers.append(producer)
    
    def _initialize_smart_meters(self):
        """Initialize all smart meters"""
        meter_counter = 0
        
        for bus_id, num_meters in self.config.SMART_METERS_PER_BUS.items():
            for _ in range(num_meters):
                # Determine consumer type
                rand = random.random()
                if rand < self.config.CONSUMER_TYPES["residential"]:
                    consumer_type = "residential"
                    base_load = random.uniform(1.0, 3.0)
                elif rand < self.config.CONSUMER_TYPES["residential"] + self.config.CONSUMER_TYPES["commercial"]:
                    consumer_type = "commercial"
                    base_load = random.uniform(5.0, 20.0)
                else:
                    consumer_type = "industrial"
                    base_load = random.uniform(20.0, 100.0)
                
                # Determine if prosumer (only residential)
                has_solar = False
                solar_capacity = 0
                if consumer_type == "residential" and random.random() < self.config.PROSUMER_PERCENTAGE:
                    has_solar = True
                    solar_capacity = random.uniform(2.0, 8.0)
                
                meter = SmartMeter(
                    meter_id=f"SMT_{meter_counter:06d}",
                    bus_id=bus_id,
                    consumer_type=consumer_type,
                    base_load_kw=base_load,
                    has_solar=has_solar,
                    solar_capacity_kw=solar_capacity
                )
                self.smart_meters.append(meter)
                meter_counter += 1
    
    def get_producer_outputs(self, hour: float) -> Dict[int, float]:
        """
        Get power output from all producers
        Returns dict {bus_id: output_mw}
        """
        outputs = {}
        for producer in self.producers:
            output = producer.get_output_at_hour(hour)
            producer.current_output_mw = output
            outputs[producer.bus_id] = outputs.get(producer.bus_id, 0) + output
        return outputs
    
    def get_loads_by_bus(self, hour: float) -> Dict[int, float]:
        """
        Aggregate loads from all smart meters by bus
        """
        loads = {bus: 0.0 for bus in range(1, 15)}
        
        for meter in self.smart_meters:
            consumption = meter.get_consumption_at_hour(hour)
            loads[meter.bus_id] += consumption / 1000  # Convert kW to MW
        
        return loads
    
    def run_power_flow(self, hour: float) -> Tuple[pd.DataFrame, Dict, bool]:
        """
        Run power flow calculation for given hour
        """
        # Get producer outputs and loads
        producer_outputs = self.get_producer_outputs(hour)
        loads = self.get_loads_by_bus(hour)
        
        # Set generators and loads in grid interface
        for bus_id, output in producer_outputs.items():
            self.grid_interface.set_generator_output(bus_id, output)
        
        for bus_id, load in loads.items():
            self.grid_interface.set_load_demand(bus_id, load)
        
        # Run power flow
        converged = self.grid_interface.run_power_flow()
        
        if converged:
            buses = self.grid_interface.get_bus_voltages()
            line_flows = self.grid_interface.get_line_power_flows()
            losses = self.grid_interface.get_power_losses()
            
            grid_state = {
                "converged": True,
                "losses_mw": losses[0],
                "producer_outputs": producer_outputs,
                "loads_mw": loads
            }
            
            return buses, grid_state, True
        else:
            return None, {}, False
    
    def collect_meter_readings(self, hour: float, buses: pd.DataFrame) -> pd.DataFrame:
        """
        Collect readings from all smart meters
        """
        readings = []
        
        for meter in self.smart_meters:
            consumption = meter.get_consumption_at_hour(hour)
            
            # Get voltage at the bus
            bus_row = buses[buses.index == f'VL{meter.bus_id}_0']
            voltage = bus_row['v_mag'].values[0] if len(bus_row) > 0 else 1.0
            
            readings.append({
                'timestamp': self.current_time,
                'meter_id': meter.meter_id,
                'bus_id': meter.bus_id,
                'consumer_type': meter.consumer_type,
                'consumption_kw': consumption,
                'voltage_pu': voltage,
                'frequency_hz': self.config.BASE_FREQUENCY_HZ + np.random.normal(0, 0.01),
                'has_solar': meter.has_solar,
                'is_anomalous': meter.is_anomalous,
                'attack_type': 'normal' if not meter.is_anomalous else 'attack'
            })
        
        return pd.DataFrame(readings)
    
    def simulate_timestep(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Simulate one timestep
        """
        self.current_hour = (self.current_time / 3600) % 24
        
        # Run power flow
        buses, grid_state, converged = self.run_power_flow(self.current_hour)
        
        if not converged:
            return pd.DataFrame(), pd.DataFrame()
        
        # Collect meter readings
        meter_readings = self.collect_meter_readings(self.current_hour, buses)
        
        # Collect grid state
        grid_state_df = pd.DataFrame([{
            'timestamp': self.current_time,
            'hour': self.current_hour,
            'converged': converged,
            'losses_mw': grid_state.get('losses_mw', 0),
            'producer_outputs': str(grid_state.get('producer_outputs', {})),
            'total_load_mw': sum(grid_state.get('loads_mw', {}).values())
        }])
        
        self.current_time += 1 / self.config.SAMPLING_RATE_HZ
        
        return grid_state_df, meter_readings
    
    def simulate_period(self, duration_seconds: int, progress_bar: bool = True) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Simulate for a period of time
        """
        num_steps = duration_seconds * self.config.SAMPLING_RATE_HZ
        all_grid_states = []
        all_meter_readings = []
        
        iterator = range(int(num_steps))
        if progress_bar:
            iterator = tqdm(iterator, desc="Simulating", unit="step")
        
        for _ in iterator:
            grid_state, meter_readings = self.simulate_timestep()
            if not grid_state.empty:
                all_grid_states.append(grid_state)
            if not meter_readings.empty:
                all_meter_readings.append(meter_readings)
        
        grid_df = pd.concat(all_grid_states, ignore_index=True) if all_grid_states else pd.DataFrame()
        meters_df = pd.concat(all_meter_readings, ignore_index=True) if all_meter_readings else pd.DataFrame()
        
        return grid_df, meters_df
    
    def generate_clean_dataset(self, hours: int = 24) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Generate clean dataset (normal operation)
        """
        print(f"\n📊 Generating CLEAN dataset ({hours} hours)...")
        
        duration_seconds = hours * 3600
        grid_df, meters_df = self.simulate_period(duration_seconds)
        
        print(f"   ✅ Generated {len(meters_df):,} meter readings")
        print(f"   ✅ Generated {len(grid_df)} grid state records")
        
        return grid_df, meters_df
    
    def generate_attack_scenario(self, scenario: Dict) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Generate attack scenario
        """
        print(f"\n⚔️ Generating attack scenario: {scenario['name']}")
        
        # Reset anomalies
        for meter in self.smart_meters:
            meter.clear_anomaly()
        
        # Set anomalies on target meters
        if scenario['type'] == 'fdia':
            target_buses = scenario.get('target_buses', [5, 8, 11])
            magnitude = scenario.get('magnitude', 0.2)
            
            for meter in self.smart_meters:
                if meter.bus_id in target_buses:
                    meter.set_anomaly(magnitude)
            print(f"   • FDIA attack: {len([m for m in self.smart_meters if m.is_anomalous])} meters affected")
        
        elif scenario['type'] == 'dos':
            packet_loss = scenario.get('packet_loss', 0.3)
            # DoS is simulated by dropping readings later
            print(f"   • DoS attack: {packet_loss*100:.0f}% packet loss")
        
        # Reset time
        self.current_time = 0
        duration = scenario.get('duration', 60)
        
        # Simulate
        grid_df, meters_df = self.simulate_period(duration)
        
        # Add attack metadata
        if not meters_df.empty:
            meters_df['attack_name'] = scenario['name']
            meters_df['attack_type'] = scenario['type']
        
        return grid_df, meters_df
