#!/usr/bin/env python3
"""
Main script to run complete smart grid simulation
"""
import sys
import os
import argparse
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import Config
from data_generation.generate_datasets import DatasetGenerator
from visualization.visualize_data import DataVisualizer


def main():
    parser = argparse.ArgumentParser(description='Smart Grid Simulation for Anomaly Detection')
    parser.add_argument('--hours', type=int, default=24, help='Number of hours to simulate')
    parser.add_argument('--sampling_rate', type=int, default=50, help='Sampling rate in Hz')
    parser.add_argument('--no_visualize', action='store_true', help='Skip visualization')
    parser.add_argument('--output_dir', type=str, default='./data', help='Output directory')
    
    args = parser.parse_args()
    
    print("="*70)
    print("🚀 SMART GRID SIMULATION FOR ANOMALY DETECTION")
    print("="*70)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Simulation: {args.hours} hours @ {args.sampling_rate} Hz")
    print(f"Output dir: {args.output_dir}")
    print("="*70)
    
    # Update config
    Config.SIMULATION_HOURS = args.hours
    Config.SAMPLING_RATE_HZ = args.sampling_rate
    Config.DATA_DIR = args.output_dir
    
    # Generate datasets
    generator = DatasetGenerator()
    clean_df, attack_df = generator.run()
    
    # Visualize if requested
    if not args.no_visualize and not clean_df.empty and not attack_df.empty:
        visualizer = DataVisualizer()
        visualizer.load_data()
        visualizer.generate_all_plots()
    
    print("\n" + "="*70)
    print("✅ SIMULATION COMPLETE!")
    print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)


if __name__ == "__main__":
    main()
