"""
Generate complete datasets (CLEAN and ATTACK)
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
import json
from datetime import datetime
import os
from tqdm import tqdm

from config import Config
from simulation.complete_smart_grid_simulator import CompleteSmartGridSimulator


class DatasetGenerator:
    """
    Generates CLEAN and ATTACK datasets
    """
    def __init__(self):
        self.config = Config()
        self.simulator = CompleteSmartGridSimulator()
        
        # Create directories
        os.makedirs(self.config.CLEAN_DIR, exist_ok=True)
        os.makedirs(self.config.ATTACK_DIR, exist_ok=True)
        os.makedirs(self.config.METADATA_DIR, exist_ok=True)
        os.makedirs(self.config.IMAGES_DIR, exist_ok=True)
    
    def generate_clean_dataset(self, hours: int = 24) -> pd.DataFrame:
        """
        Generate clean dataset (normal operation)
        """
        print("\n" + "="*60)
        print("📊 GENERATING CLEAN DATASET")
        print("="*60)
        
        grid_df, meters_df = self.simulator.generate_clean_dataset(hours)
        
        # Save to CSV
        clean_path = os.path.join(self.config.CLEAN_DIR, f"smartgrid_clean_{hours}h.csv")
        meters_df.to_csv(clean_path, index=False)
        print(f"\n✅ Clean dataset saved to: {clean_path}")
        print(f"   • {len(meters_df):,} meter readings")
        
        return meters_df
    
    def generate_attack_datasets(self) -> pd.DataFrame:
        """
        Generate all attack scenarios
        """
        print("\n" + "="*60)
        print("⚔️ GENERATING ATTACK DATASETS")
        print("="*60)
        
        all_attacks = []
        
        for scenario in self.config.ATTACK_SCENARIOS:
            # Reset simulator
            self.simulator = CompleteSmartGridSimulator()
            
            # Generate attack
            grid_df, meters_df = self.simulator.generate_attack_scenario(scenario)
            
            if not meters_df.empty:
                all_attacks.append(meters_df)
            
            # Save individual scenario
            attack_path = os.path.join(self.config.ATTACK_DIR, f"attack_{scenario['name']}.csv")
            meters_df.to_csv(attack_path, index=False)
            print(f"   💾 Saved: {attack_path}")
        
        # Combine all attacks
        if all_attacks:
            combined_df = pd.concat(all_attacks, ignore_index=True)
            combined_path = os.path.join(self.config.ATTACK_DIR, "attacks_complete.csv")
            combined_df.to_csv(combined_path, index=False)
            print(f"\n✅ Combined attacks saved to: {combined_path}")
            print(f"   • {len(combined_df):,} total attack readings")
            return combined_df
        
        return pd.DataFrame()
    
    def generate_metadata(self, clean_df: pd.DataFrame, attack_df: pd.DataFrame):
        """
        Generate metadata about datasets
        """
        metadata = {
            "project": "Smart Grid Anomaly Detection",
            "timestamp": datetime.now().isoformat(),
            "config": {
                "sampling_rate_hz": self.config.SAMPLING_RATE_HZ,
                "total_smart_meters": self.config.TOTAL_SMART_METERS,
                "producers": self.config.PRODUCERS,
                "simulation_hours": self.config.SIMULATION_HOURS
            },
            "clean_dataset": {
                "samples": len(clean_df),
                "file": "clean/smartgrid_clean_24h.csv",
                "columns": list(clean_df.columns) if not clean_df.empty else []
            },
            "attack_dataset": {
                "samples": len(attack_df),
                "file": "attacks/attacks_complete.csv",
                "attack_distribution": attack_df['attack_type'].value_counts().to_dict() if not attack_df.empty else {},
                "columns": list(attack_df.columns) if not attack_df.empty else []
            }
        }
        
        metadata_path = os.path.join(self.config.METADATA_DIR, "dataset_metadata.json")
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"\n📋 Metadata saved to: {metadata_path}")
        
        # Print summary
        print("\n" + "="*60)
        print("📊 DATASET SUMMARY")
        print("="*60)
        print(f"Clean samples: {len(clean_df):,}")
        print(f"Attack samples: {len(attack_df):,}")
        if not attack_df.empty:
            print("\nAttack distribution:")
            for attack_type, count in attack_df['attack_type'].value_counts().items():
                print(f"   • {attack_type}: {count:,}")
        print("="*60)
    
    def run(self):
        """
        Run complete dataset generation
        """
        print("\n🚀 STARTING COMPLETE DATASET GENERATION")
        print("="*60)
        
        # Generate clean dataset
        clean_df = self.generate_clean_dataset(hours=self.config.SIMULATION_HOURS)
        
        # Generate attack datasets
        attack_df = self.generate_attack_datasets()
        
        # Generate metadata
        self.generate_metadata(clean_df, attack_df)
        
        print("\n✅ DATASET GENERATION COMPLETE!")
        return clean_df, attack_df


if __name__ == "__main__":
    generator = DatasetGenerator()
    clean_df, attack_df = generator.run()
