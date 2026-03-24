"""
Smart grid components: Producers, Smart Meters, Load Profiles
"""
import numpy as np
import pandas as pd
from datetime import datetime
import random
from typing import Dict, List, Optional
import json

class Producer:
    """
    Represents an electricity producer (power plant, solar farm, wind farm)
    """
    def __init__(self, producer_id: str, name: str, bus_id: int, producer_type: str,
                 capacity_mw: float, cost_per_mwh: float):
        self.id = producer_id
        self.name = name
        self.bus_id = bus_id
        self.type = producer_type
        self.capacity_mw = capacity_mw
        self.cost_per_mwh = cost_per_mwh
        self.current_output_mw = 0.0
        
    def get_output_at_hour(self, hour: float) -> float:
        """
        Returns power output based on hour of day and producer type
        """
        if self.type == "gas":
            # Gas plants provide base load with peaking capability
            base = self.capacity_mw * 0.7
            # Peak hours (18-22): increase output
            if 18 <= hour <= 22:
                peak_factor = 1 + (hour - 18) * 0.05
                return min(self.capacity_mw, base * peak_factor)
            return base
            
        elif self.type == "solar":
            # Solar follows sun position
            if 6 <= hour <= 18:
                # Peak at solar noon (12-14)
                peak_hour = 12 + (hour - 12) * 0.1
                factor = max(0, np.sin(np.pi * (hour - 6) / 12))
                # Add cloud effects
                cloud_factor = max(0.5, 1 - random.random() * 0.3)
                return self.capacity_mw * factor * cloud_factor
            return 0
            
        elif self.type == "wind":
            # Wind with Weibull distribution pattern
            base_factor = 0.3 + 0.4 * np.sin(np.pi * (hour - 4) / 24)
            random_factor = np.random.weibull(2) * 0.5
            return min(self.capacity_mw, self.capacity_mw * (base_factor + random_factor))
            
        elif self.type == "hydro":
            # Hydro relatively constant with seasonal variations
            seasonal = 0.8 + 0.2 * np.sin(2 * np.pi * (hour / 24) * 0.1)
            return self.capacity_mw * seasonal
            
        return 0
    
    def to_dict(self):
        return {
            "id": self.id, "name": self.name, "bus_id": self.bus_id,
            "type": self.type, "capacity_mw": self.capacity_mw,
            "current_output_mw": self.current_output_mw
        }


class SmartMeter:
    """
    Represents a smart meter connected to a specific bus
    """
    def __init__(self, meter_id: str, bus_id: int, consumer_type: str,
                 base_load_kw: float, has_solar: bool = False, solar_capacity_kw: float = 0):
        self.meter_id = meter_id
        self.bus_id = bus_id
        self.consumer_type = consumer_type
        self.base_load_kw = base_load_kw
        self.has_solar = has_solar
        self.solar_capacity_kw = solar_capacity_kw
        self.is_anomalous = False
        self.anomaly_magnitude = 0.0
        
    def get_consumption_at_hour(self, hour: float) -> float:
        """
        Returns consumption based on consumer type and hour
        """
        # Base load factor by consumer type
        if self.consumer_type == "residential":
            # Residential: peaks morning (7-9) and evening (18-22)
            if 7 <= hour <= 9:
                factor = 1.2 + (hour - 7) * 0.1
            elif 18 <= hour <= 22:
                factor = 1.3 + (hour - 18) * 0.05
            elif 0 <= hour <= 5:
                factor = 0.4
            else:
                factor = 0.7
                
        elif self.consumer_type == "commercial":
            # Commercial: peaks midday (10-16)
            if 10 <= hour <= 16:
                factor = 1.2
            elif 0 <= hour <= 6:
                factor = 0.2
            else:
                factor = 0.6
                
        elif self.consumer_type == "industrial":
            # Industrial: constant during working hours
            if 6 <= hour <= 22:
                factor = 0.9
            else:
                factor = 0.3
        else:
            factor = 0.7
        
        # Add random variations
        random_variation = np.random.normal(1, 0.05)
        
        consumption = self.base_load_kw * factor * random_variation
        
        # Apply anomaly if flagged
        if self.is_anomalous:
            consumption = consumption * (1 + self.anomaly_magnitude)
        
        # Apply prosumer solar production
        if self.has_solar and 6 <= hour <= 18:
            solar_output = self.solar_capacity_kw * np.sin(np.pi * (hour - 6) / 12)
            consumption = max(0, consumption - solar_output)
        
        return max(0, consumption)
    
    def set_anomaly(self, magnitude: float = 0.2):
        """Set this meter as anomalous for attack simulation"""
        self.is_anomalous = True
        self.anomaly_magnitude = magnitude
    
    def clear_anomaly(self):
        """Clear anomaly flag"""
        self.is_anomalous = False
        self.anomaly_magnitude = 0.0
    
    def to_dict(self):
        return {
            "meter_id": self.meter_id, "bus_id": self.bus_id,
            "consumer_type": self.consumer_type, "base_load_kw": self.base_load_kw,
            "has_solar": self.has_solar, "is_anomalous": self.is_anomalous
        }


class LoadProfileGenerator:
    """
    Generates realistic load profiles for different consumer types
    """
    @staticmethod
    def residential_profile(hour: float) -> float:
        """Residential consumption pattern"""
        if 7 <= hour <= 9:
            return 1.2 + (hour - 7) * 0.1
        elif 18 <= hour <= 22:
            return 1.3 + (hour - 18) * 0.05
        elif 0 <= hour <= 5:
            return 0.4
        return 0.7
    
    @staticmethod
    def commercial_profile(hour: float) -> float:
        """Commercial consumption pattern"""
        if 10 <= hour <= 16:
            return 1.2
        elif 0 <= hour <= 6:
            return 0.2
        return 0.6
    
    @staticmethod
    def industrial_profile(hour: float) -> float:
        """Industrial consumption pattern"""
        if 6 <= hour <= 22:
            return 0.9
        return 0.3
    
    @staticmethod
    def weekend_adjustment(profile: float, is_weekend: bool, consumer_type: str) -> float:
        """Adjust consumption for weekends"""
        if is_weekend and consumer_type == "commercial":
            return profile * 0.3
        elif is_weekend and consumer_type == "residential":
            return profile * 1.1
        return profile
