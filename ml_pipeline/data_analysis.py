"""
Enhanced Data Analysis, Cleaning, and Visualization
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, Tuple
import warnings
warnings.filterwarnings('ignore')

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 6)


class SmartGridDataAnalyzer:
    """
    Comprehensive data analysis and visualization for smart grid data
    """
    
    def __init__(self):
        self.df = None
        self.stats = {}
        
    def load_and_explore(self, filepath: str, nrows: int = None) -> pd.DataFrame:
        """
        Load data and perform initial exploration
        """
        print("=" * 80)
        print("📊 DATA EXPLORATION")
        print("=" * 80)
        
        # Load data
        print(f"\n📂 Loading data from {filepath}...")
        if nrows:
            self.df = pd.read_csv(filepath, nrows=nrows)
            print(f"   ✅ Loaded {len(self.df):,} records (sample)")
        else:
            self.df = pd.read_csv(filepath)
            print(f"   ✅ Loaded {len(self.df):,} records (full dataset)")
        
        # Basic info
        print(f"\n📋 Dataset Info:")
        print(f"   • Shape: {self.df.shape}")
        print(f"   • Columns: {list(self.df.columns)}")
        print(f"   • Memory usage: {self.df.memory_usage(deep=True).sum() / 1024**2:.2f} MB")
        
        # Data types
        print(f"\n🔤 Data Types:")
        for col, dtype in self.df.dtypes.items():
            print(f"   • {col}: {dtype}")
        
        # Missing values
        print(f"\n❓ Missing Values:")
        missing = self.df.isnull().sum()
        for col, count in missing.items():
            if count > 0:
                pct = (count / len(self.df)) * 100
                print(f"   • {col}: {count:,} ({pct:.2f}%)")
        
        if missing.sum() == 0:
            print("   ✅ No missing values!")
        
        return self.df
    
    def analyze_distributions(self, save_dir: str = "ml_pipeline/plots/"):
        """
        Analyze and visualize data distributions
        """
        print("\n" + "=" * 80)
        print("📈 DISTRIBUTION ANALYSIS")
        print("=" * 80)
        
        import os
        os.makedirs(save_dir, exist_ok=True)
        
        # Numerical columns
        num_cols = ['consommation_kw', 'tension_v', 'courant_a']
        
        # 1. Distribution plots
        fig, axes = plt.subplots(1, 3, figsize=(15, 4))
        
        for idx, col in enumerate(num_cols):
            axes[idx].hist(self.df[col], bins=50, alpha=0.7, color='steelblue', edgecolor='black')
            axes[idx].set_title(f'Distribution of {col}', fontweight='bold')
            axes[idx].set_xlabel(col)
            axes[idx].set_ylabel('Frequency')
            axes[idx].grid(alpha=0.3)
            
            # Add statistics
            mean_val = self.df[col].mean()
            median_val = self.df[col].median()
            axes[idx].axvline(mean_val, color='red', linestyle='--', label=f'Mean: {mean_val:.2f}')
            axes[idx].axvline(median_val, color='green', linestyle='--', label=f'Median: {median_val:.2f}')
            axes[idx].legend()
        
        plt.tight_layout()
        plt.savefig(f"{save_dir}/01_distributions.png", dpi=300, bbox_inches='tight')
        print(f"   💾 Saved: {save_dir}/01_distributions.png")
        plt.close()
        
        # 2. Box plots (outlier detection)
        fig, axes = plt.subplots(1, 3, figsize=(15, 4))
        
        for idx, col in enumerate(num_cols):
            axes[idx].boxplot(self.df[col], vert=True)
            axes[idx].set_title(f'Box Plot: {col}', fontweight='bold')
            axes[idx].set_ylabel(col)
            axes[idx].grid(alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(f"{save_dir}/02_boxplots_outliers.png", dpi=300, bbox_inches='tight')
        print(f"   💾 Saved: {save_dir}/02_boxplots_outliers.png")
        plt.close()
        
        # 3. Statistical summary
        print(f"\n📊 Statistical Summary:")
        print(self.df[num_cols].describe())
        
    def analyze_categorical(self, save_dir: str = "ml_pipeline/plots/"):
        """
        Analyze categorical variables
        """
        print("\n" + "=" * 80)
        print("🏷️ CATEGORICAL ANALYSIS")
        print("=" * 80)
        
        import os
        os.makedirs(save_dir, exist_ok=True)
        
        # 1. Zone distribution
        fig, axes = plt.subplots(1, 3, figsize=(15, 4))
        
        # Zone counts
        zone_counts = self.df['zone'].value_counts()
        axes[0].bar(zone_counts.index, zone_counts.values, color='skyblue', edgecolor='black')
        axes[0].set_title('Distribution by Zone', fontweight='bold')
        axes[0].set_xlabel('Zone')
        axes[0].set_ylabel('Count')
        axes[0].grid(axis='y', alpha=0.3)
        
        # Type counts
        type_counts = self.df['type'].value_counts()
        axes[1].bar(type_counts.index, type_counts.values, color='lightcoral', edgecolor='black')
        axes[1].set_title('Distribution by Consumer Type', fontweight='bold')
        axes[1].set_xlabel('Type')
        axes[1].set_ylabel('Count')
        axes[1].grid(axis='y', alpha=0.3)
        axes[1].tick_params(axis='x', rotation=45)
        
        # Status counts
        status_counts = self.df['statut'].value_counts()
        colors = ['green' if x == 'NORMAL' else 'red' for x in status_counts.index]
        axes[2].bar(status_counts.index, status_counts.values, color=colors, edgecolor='black')
        axes[2].set_title('Distribution by Status', fontweight='bold')
        axes[2].set_xlabel('Status')
        axes[2].set_ylabel('Count')
        axes[2].grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(f"{save_dir}/03_categorical_distributions.png", dpi=300, bbox_inches='tight')
        print(f"   💾 Saved: {save_dir}/03_categorical_distributions.png")
        plt.close()
        
        # Print counts
        print(f"\n📊 Zone Distribution:")
        for zone, count in zone_counts.items():
            pct = (count / len(self.df)) * 100
            print(f"   • {zone}: {count:,} ({pct:.2f}%)")
        
        print(f"\n📊 Consumer Type Distribution:")
        for ctype, count in type_counts.items():
            pct = (count / len(self.df)) * 100
            print(f"   • {ctype}: {count:,} ({pct:.2f}%)")
        
        print(f"\n📊 Status Distribution:")
        for status, count in status_counts.items():
            pct = (count / len(self.df)) * 100
            print(f"   • {status}: {count:,} ({pct:.2f}%)")
        
    def analyze_temporal_patterns(self, save_dir: str = "ml_pipeline/plots/"):
        """
        Analyze temporal patterns
        """
        print("\n" + "=" * 80)
        print("⏰ TEMPORAL ANALYSIS")
        print("=" * 80)
        
        import os
        os.makedirs(save_dir, exist_ok=True)
        
        # Parse timestamp
        self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])
        self.df['hour'] = self.df['timestamp'].dt.hour
        self.df['day_of_week'] = self.df['timestamp'].dt.dayofweek
        self.df['date'] = self.df['timestamp'].dt.date
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        # 1. Consumption by hour
        hourly_consumption = self.df.groupby('hour')['consommation_kw'].mean()
        axes[0, 0].plot(hourly_consumption.index, hourly_consumption.values, marker='o', linewidth=2, color='steelblue')
        axes[0, 0].fill_between(hourly_consumption.index, hourly_consumption.values, alpha=0.3)
        axes[0, 0].set_title('Average Consumption by Hour', fontweight='bold')
        axes[0, 0].set_xlabel('Hour of Day')
        axes[0, 0].set_ylabel('Consumption (kW)')
        axes[0, 0].grid(alpha=0.3)
        axes[0, 0].set_xticks(range(0, 24, 2))
        
        # 2. Consumption by consumer type and hour
        for ctype in self.df['type'].unique():
            type_data = self.df[self.df['type'] == ctype].groupby('hour')['consommation_kw'].mean()
            axes[0, 1].plot(type_data.index, type_data.values, marker='o', label=ctype, linewidth=2)
        
        axes[0, 1].set_title('Consumption by Type and Hour', fontweight='bold')
        axes[0, 1].set_xlabel('Hour of Day')
        axes[0, 1].set_ylabel('Consumption (kW)')
        axes[0, 1].legend()
        axes[0, 1].grid(alpha=0.3)
        axes[0, 1].set_xticks(range(0, 24, 2))
        
        # 3. Voltage by hour
        hourly_voltage = self.df.groupby('hour')['tension_v'].mean()
        axes[1, 0].plot(hourly_voltage.index, hourly_voltage.values, marker='o', linewidth=2, color='orange')
        axes[1, 0].fill_between(hourly_voltage.index, hourly_voltage.values, alpha=0.3, color='orange')
        axes[1, 0].set_title('Average Voltage by Hour', fontweight='bold')
        axes[1, 0].set_xlabel('Hour of Day')
        axes[1, 0].set_ylabel('Voltage (V)')
        axes[1, 0].grid(alpha=0.3)
        axes[1, 0].set_xticks(range(0, 24, 2))
        
        # 4. Anomaly rate by hour
        hourly_anomalies = self.df.groupby('hour')['statut'].apply(lambda x: (x == 'ALERTE').sum() / len(x) * 100)
        axes[1, 1].bar(hourly_anomalies.index, hourly_anomalies.values, color='red', alpha=0.7, edgecolor='black')
        axes[1, 1].set_title('Anomaly Rate by Hour', fontweight='bold')
        axes[1, 1].set_xlabel('Hour of Day')
        axes[1, 1].set_ylabel('Anomaly Rate (%)')
        axes[1, 1].grid(axis='y', alpha=0.3)
        axes[1, 1].set_xticks(range(0, 24, 2))
        
        plt.tight_layout()
        plt.savefig(f"{save_dir}/04_temporal_patterns.png", dpi=300, bbox_inches='tight')
        print(f"   💾 Saved: {save_dir}/04_temporal_patterns.png")
        plt.close()
        
    def analyze_correlations(self, save_dir: str = "ml_pipeline/plots/"):
        """
        Analyze correlations between variables
        """
        print("\n" + "=" * 80)
        print("🔗 CORRELATION ANALYSIS")
        print("=" * 80)
        
        import os
        os.makedirs(save_dir, exist_ok=True)
        
        # Select numerical columns
        num_cols = ['consommation_kw', 'tension_v', 'courant_a']
        
        # Compute correlation matrix
        corr_matrix = self.df[num_cols].corr()
        
        # Plot heatmap
        plt.figure(figsize=(8, 6))
        sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', center=0, 
                    square=True, linewidths=1, cbar_kws={"shrink": 0.8})
        plt.title('Correlation Matrix', fontweight='bold', fontsize=14)
        plt.tight_layout()
        plt.savefig(f"{save_dir}/05_correlation_matrix.png", dpi=300, bbox_inches='tight')
        print(f"   💾 Saved: {save_dir}/05_correlation_matrix.png")
        plt.close()
        
        print(f"\n📊 Correlation Matrix:")
        print(corr_matrix)
        
    def detect_outliers(self, save_dir: str = "ml_pipeline/plots/"):
        """
        Detect and visualize outliers
        """
        print("\n" + "=" * 80)
        print("🔍 OUTLIER DETECTION")
        print("=" * 80)
        
        import os
        os.makedirs(save_dir, exist_ok=True)
        
        num_cols = ['consommation_kw', 'tension_v', 'courant_a']
        
        outlier_stats = {}
        
        for col in num_cols:
            # IQR method
            Q1 = self.df[col].quantile(0.25)
            Q3 = self.df[col].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            
            outliers = self.df[(self.df[col] < lower_bound) | (self.df[col] > upper_bound)]
            outlier_pct = (len(outliers) / len(self.df)) * 100
            
            outlier_stats[col] = {
                'count': len(outliers),
                'percentage': outlier_pct,
                'lower_bound': lower_bound,
                'upper_bound': upper_bound
            }
            
            print(f"\n📊 {col}:")
            print(f"   • Outliers: {len(outliers):,} ({outlier_pct:.2f}%)")
            print(f"   • Lower bound: {lower_bound:.2f}")
            print(f"   • Upper bound: {upper_bound:.2f}")
        
        return outlier_stats
    
    def generate_summary_report(self, save_path: str = "ml_pipeline/results/data_summary.txt"):
        """
        Generate comprehensive summary report
        """
        print("\n" + "=" * 80)
        print("📝 GENERATING SUMMARY REPORT")
        print("=" * 80)
        
        import os
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("SMART GRID DATA ANALYSIS REPORT\n")
            f.write("=" * 80 + "\n\n")
            
            f.write("1. DATASET OVERVIEW\n")
            f.write("-" * 80 + "\n")
            f.write(f"Total Records: {len(self.df):,}\n")
            f.write(f"Total Columns: {len(self.df.columns)}\n")
            f.write(f"Memory Usage: {self.df.memory_usage(deep=True).sum() / 1024**2:.2f} MB\n\n")
            
            f.write("2. COLUMN INFORMATION\n")
            f.write("-" * 80 + "\n")
            for col in self.df.columns:
                f.write(f"  • {col}: {self.df[col].dtype}\n")
            f.write("\n")
            
            f.write("3. STATISTICAL SUMMARY\n")
            f.write("-" * 80 + "\n")
            f.write(self.df[['consommation_kw', 'tension_v', 'courant_a']].describe().to_string())
            f.write("\n\n")
            
            f.write("4. CATEGORICAL DISTRIBUTIONS\n")
            f.write("-" * 80 + "\n")
            f.write("Zones:\n")
            for zone, count in self.df['zone'].value_counts().items():
                pct = (count / len(self.df)) * 100
                f.write(f"  • {zone}: {count:,} ({pct:.2f}%)\n")
            
            f.write("\nConsumer Types:\n")
            for ctype, count in self.df['type'].value_counts().items():
                pct = (count / len(self.df)) * 100
                f.write(f"  • {ctype}: {count:,} ({pct:.2f}%)\n")
            
            f.write("\nStatus:\n")
            for status, count in self.df['statut'].value_counts().items():
                pct = (count / len(self.df)) * 100
                f.write(f"  • {status}: {count:,} ({pct:.2f}%)\n")
            
            f.write("\n" + "=" * 80 + "\n")
        
        print(f"   💾 Saved: {save_path}")


def run_complete_analysis(filepath: str, nrows: int = 50000):
    """
    Run complete data analysis pipeline
    """
    analyzer = SmartGridDataAnalyzer()
    
    # Load and explore
    df = analyzer.load_and_explore(filepath, nrows=nrows)
    
    # Analyze distributions
    analyzer.analyze_distributions()
    
    # Analyze categorical
    analyzer.analyze_categorical()
    
    # Analyze temporal patterns
    analyzer.analyze_temporal_patterns()
    
    # Analyze correlations
    analyzer.analyze_correlations()
    
    # Detect outliers
    analyzer.detect_outliers()
    
    # Generate summary report
    analyzer.generate_summary_report()
    
    print("\n" + "=" * 80)
    print("✅ ANALYSIS COMPLETE")
    print("=" * 80)
    print("\n📁 All visualizations saved to: ml_pipeline/plots/")
    print("📄 Summary report saved to: ml_pipeline/results/data_summary.txt")


if __name__ == "__main__":
    run_complete_analysis("donnees_smart_meters.csv", nrows=50000)
