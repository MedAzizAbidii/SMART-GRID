"""
Connection to PyPowSyBl power flow solver (Mock version when library unavailable)
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional

try:
    import pypowsybl as pp
    HAS_PYPOWSYBL = True
except ImportError:
    HAS_PYPOWSYBL = False

class PyPowSyBlInterface:
    """
    Interface between Python and PyPowSyBl power flow solver
    """
    def __init__(self):
        self.network = None
        self._create_network()
    
    def _create_network(self):
        """Create IEEE 14-bus network"""
        if HAS_PYPOWSYBL:
            try:
                self.network = pp.network.create_ieee14()
                print("✅ IEEE 14-bus network created (PyPowSyBl)")
            except Exception as e:
                print(f"⚠️ PyPowSyBl error: {e}, using mock network")
                self._create_mock_network()
        else:
            print("⚠️ PyPowSyBl not available, using mock network for simulation")
            self._create_mock_network()
    
    def _create_mock_network(self):
        """Create mock IEEE 14-bus network for testing"""
        # Create mock bus data for IEEE 14-bus
        self.bus_data = {
            f'VL{i}_0': {'v_mag': 1.0 + np.random.normal(0, 0.01)} 
            for i in range(1, 15)
        }
        self.generators = {}
        self.loads = {}
        self.lines = {}
    
    
    def set_generator_output(self, bus_id: int, power_mw: float) -> None:
        """Set generator active power output"""
        if HAS_PYPOWSYBL and self.network:
            generator_id = f"VL{1 if bus_id in [1,2] else bus_id}_0"
            try:
                self.network.update_generators(generator_id, target_p=power_mw)
            except:
                pass
        else:
            self.generators[bus_id] = power_mw
    
    def set_load_demand(self, bus_id: int, load_mw: float) -> None:
        """Set load demand at bus"""
        if HAS_PYPOWSYBL and self.network:
            load_id = f'LOAD_{bus_id}_0'
            try:
                loads = self.network.get_loads()
                if load_id in loads.index:
                    self.network.update_loads(load_id, p0=load_mw)
            except:
                pass
        else:
            self.loads[bus_id] = load_mw
    
    def run_power_flow(self) -> bool:
        """Execute power flow calculation"""
        if HAS_PYPOWSYBL and self.network:
            try:
                results = pp.loadflow.run_ac(self.network)
                return results[0].status.value == 'CONVERGED'
            except Exception as e:
                print(f"Power flow error: {e}")
                return False
        else:
            # Mock convergence - always succeeds
            return True
    
    def get_bus_voltages(self) -> pd.DataFrame:
        """Get voltage magnitudes and angles for all buses"""
        if HAS_PYPOWSYBL and self.network:
            return self.network.get_buses()
        else:
            # Return mock voltage data
            data = {
                'v_mag': [1.0 + np.random.normal(0, 0.01) for _ in range(14)]
            }
            return pd.DataFrame(data, index=[f'VL{i+1}_0' for i in range(14)])
    
    def get_line_currents(self) -> pd.DataFrame:
        """Get currents on all transmission lines"""
        if HAS_PYPOWSYBL and self.network:
            return self.network.get_lines()
        else:
            return pd.DataFrame()
    
    def get_line_power_flows(self) -> pd.DataFrame:
        """Get power flows on all transmission lines"""
        if HAS_PYPOWSYBL and self.network:
            return self.network.get_branch_power_flows()
        else:
            return pd.DataFrame()
    
    def get_power_losses(self) -> Tuple[float, float]:
        """Get active and reactive power losses"""
        if HAS_PYPOWSYBL and self.network:
            lines = self.network.get_lines()
            p_loss = lines['p1'].sum() + lines['p2'].sum()
            q_loss = lines['q1'].sum() + lines['q2'].sum()
            return p_loss, q_loss
        else:
            # Mock losses (small amount)
            return np.random.uniform(0.5, 2.0), np.random.uniform(0.2, 1.0)
