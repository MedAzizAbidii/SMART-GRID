#!/usr/bin/env python3
"""
Quick test script to view generated data
"""
import pandas as pd
import os

print('='*70)
print('📊 GENERATED FILES')
print('='*70)

clean_file = './data/clean/smartgrid_clean_fast.csv'
attack_file = './data/attacks/attacks_fast.csv'

if os.path.exists(clean_file):
    clean = pd.read_csv(clean_file)
    print(f'\n✅ CLEAN DATA: {clean_file}')
    print(f'   Rows: {len(clean):,}')
    print(f'   Columns: {list(clean.columns)}')
    print(f'\n   Sample:')
    print(clean.head(3).to_string())
    print(f'\n   Statistics:')
    print(f'   - Avg consumption: {clean["consumption_kw"].mean():.2f} kW')
    print(f'   - Avg voltage: {clean["voltage_pu"].mean():.4f} pu')
else:
    print(f'❌ Not found: {clean_file}')

if os.path.exists(attack_file):
    attacks = pd.read_csv(attack_file)
    print(f'\n✅ ATTACK DATA: {attack_file}')
    print(f'   Rows: {len(attacks):,}')
    print(f'   Attack types: {list(attacks["attack_type"].unique())}')
    print(f'   Attack distribution:')
    for atype, count in attacks['attack_type'].value_counts().items():
        print(f'      - {atype}: {count:,}')
    print(f'\n   Sample FDIA attack:')
    fdia = attacks[attacks['attack_type'] == 'fdia'].head(2)
    print(fdia.to_string())
else:
    print(f'❌ Not found: {attack_file}')

print(f'\n' + '='*70)
