"""
Visualization of smart grid data
"""
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import os

from config import Config


class DataVisualizer:
    """
    Visualize smart grid datasets
    """
    def __init__(self):
        self.config = Config()
        self.clean_df = None
        self.attack_df = None
        
        # Set style
        try:
            plt.style.use('seaborn-v0_8-darkgrid')
        except Exception:
            try:
                plt.style.use('seaborn-darkgrid')
            except Exception:
                plt.style.use('default')
        sns.set_palette("Set2")
        
        # Create images directory
        os.makedirs(self.config.IMAGES_DIR, exist_ok=True)
    
    def load_data(self, clean_path=None, attack_path=None):
        """
        Load datasets
        """
        if clean_path is None:
            clean_path = os.path.join(self.config.CLEAN_DIR, "smartgrid_clean_24h.csv")
        if attack_path is None:
            attack_path = os.path.join(self.config.ATTACK_DIR, "attacks_complete.csv")
        
        self.clean_df = pd.read_csv(clean_path)
        self.attack_df = pd.read_csv(attack_path)
        
        print(f"✅ Loaded clean data: {len(self.clean_df):,} samples")
        print(f"✅ Loaded attack data: {len(self.attack_df):,} samples")
        
        return self.clean_df, self.attack_df
    
    def plot_voltage_distribution(self, save=True):
        """
        Plot voltage distribution comparison
        """
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        
        # Clean data
        axes[0].hist(self.clean_df['voltage_pu'], bins=50, alpha=0.7, color='green', edgecolor='black')
        axes[0].set_xlabel('Voltage (pu)')
        axes[0].set_ylabel('Frequency')
        axes[0].set_title('Clean Data - Voltage Distribution')
        axes[0].axvline(x=1.0, color='red', linestyle='--', label='Nominal (1.0 pu)')
        axes[0].legend()
        
        # Attack data
        axes[1].hist(self.attack_df['voltage_pu'], bins=50, alpha=0.7, color='red', edgecolor='black')
        axes[1].set_xlabel('Voltage (pu)')
        axes[1].set_ylabel('Frequency')
        axes[1].set_title('Attack Data - Voltage Distribution')
        axes[1].axvline(x=1.0, color='green', linestyle='--', label='Nominal (1.0 pu)')
        axes[1].legend()
        
        plt.tight_layout()
        
        if save:
            plt.savefig(os.path.join(self.config.IMAGES_DIR, 'voltage_distribution.png'), dpi=150)
            print(f"💾 Saved: {self.config.IMAGES_DIR}/voltage_distribution.png")
        plt.show()
    
    def plot_consumption_by_type(self, save=True):
        """
        Plot consumption by consumer type
        """
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        
        # Clean data
        clean_by_type = self.clean_df.groupby('consumer_type')['consumption_kw'].mean()
        axes[0].bar(clean_by_type.index, clean_by_type.values, color=['#2ecc71', '#3498db', '#e74c3c'])
        axes[0].set_xlabel('Consumer Type')
        axes[0].set_ylabel('Average Consumption (kW)')
        axes[0].set_title('Clean Data - Average Consumption by Type')
        
        # Attack data
        attack_by_type = self.attack_df.groupby('consumer_type')['consumption_kw'].mean()
        axes[1].bar(attack_by_type.index, attack_by_type.values, color=['#2ecc71', '#3498db', '#e74c3c'])
        axes[1].set_xlabel('Consumer Type')
        axes[1].set_ylabel('Average Consumption (kW)')
        axes[1].set_title('Attack Data - Average Consumption by Type')
        
        plt.tight_layout()
        
        if save:
            plt.savefig(os.path.join(self.config.IMAGES_DIR, 'consumption_by_type.png'), dpi=150)
            print(f"💾 Saved: {self.config.IMAGES_DIR}/consumption_by_type.png")
        plt.show()
    
    def plot_attack_distribution(self, save=True):
        """
        Plot attack type distribution
        """
        fig, ax = plt.subplots(figsize=(10, 6))
        
        attack_counts = self.attack_df['attack_type'].value_counts()
        colors = ['#e74c3c', '#f39c12', '#9b59b6']
        
        bars = ax.bar(attack_counts.index, attack_counts.values, color=colors)
        ax.set_xlabel('Attack Type')
        ax.set_ylabel('Number of Samples')
        ax.set_title('Attack Distribution in Dataset')
        
        # Add value labels on bars
        for bar, count in zip(bars, attack_counts.values):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1000,
                   f'{count:,}', ha='center', va='bottom')
        
        plt.tight_layout()
        
        if save:
            plt.savefig(os.path.join(self.config.IMAGES_DIR, 'attack_distribution.png'), dpi=150)
            print(f"💾 Saved: {self.config.IMAGES_DIR}/attack_distribution.png")
        plt.show()
    
    def plot_time_series(self, bus_id=5, duration_seconds=60, save=True):
        """
        Plot time series for a specific bus
        """
        fig, axes = plt.subplots(2, 1, figsize=(14, 8))
        
        # Filter data for specific bus
        clean_bus = self.clean_df[self.clean_df['bus_id'] == bus_id].head(int(duration_seconds * self.config.SAMPLING_RATE_HZ))
        attack_bus = self.attack_df[self.attack_df['bus_id'] == bus_id].head(int(duration_seconds * self.config.SAMPLING_RATE_HZ))
        
        # Voltage time series
        axes[0].plot(clean_bus['timestamp'].values[:500], clean_bus['voltage_pu'].values[:500],
                    label='Clean', alpha=0.7, linewidth=1)
        axes[0].plot(attack_bus['timestamp'].values[:500], attack_bus['voltage_pu'].values[:500],
                    label='Attack', alpha=0.7, linewidth=1, color='red')
        axes[0].set_ylabel('Voltage (pu)')
        axes[0].set_title(f'Bus {bus_id} - Voltage Time Series')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)
        
        # Consumption time series
        axes[1].plot(clean_bus['timestamp'].values[:500], clean_bus['consumption_kw'].values[:500],
                    label='Clean', alpha=0.7, linewidth=1)
        axes[1].plot(attack_bus['timestamp'].values[:500], attack_bus['consumption_kw'].values[:500],
                    label='Attack', alpha=0.7, linewidth=1, color='red')
        axes[1].set_xlabel('Timestamp')
        axes[1].set_ylabel('Consumption (kW)')
        axes[1].set_title(f'Bus {bus_id} - Consumption Time Series')
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save:
            plt.savefig(os.path.join(self.config.IMAGES_DIR, f'timeseries_bus_{bus_id}.png'), dpi=150)
            print(f"💾 Saved: {self.config.IMAGES_DIR}/timeseries_bus_{bus_id}.png")
        plt.show()
    
    def plot_correlation_matrix(self, save=True):
        """
        Plot correlation matrix of features
        """
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Select numerical columns
        numeric_cols = ['voltage_pu', 'consumption_kw', 'frequency_hz']
        corr = self.clean_df[numeric_cols].corr()
        
        sns.heatmap(corr, annot=True, fmt='.3f', cmap='coolwarm', center=0,
                   square=True, linewidths=1, ax=ax)
        ax.set_title('Feature Correlation Matrix')
        
        plt.tight_layout()
        
        if save:
            plt.savefig(os.path.join(self.config.IMAGES_DIR, 'correlation_matrix.png'), dpi=150)
            print(f"💾 Saved: {self.config.IMAGES_DIR}/correlation_matrix.png")
        plt.show()
    
    def generate_all_plots(self):
        """
        Generate all visualization plots
        """
        print("\n📊 Generating visualizations...")
        
        self.plot_voltage_distribution()
        self.plot_consumption_by_type()
        self.plot_attack_distribution()
        self.plot_time_series(bus_id=5)
        self.plot_correlation_matrix()
        
        print("\n✅ All visualizations generated!")
