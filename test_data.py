#!/usr/bin/env python3
"""Quick script to inspect generated fast datasets."""
from __future__ import annotations

import os

import pandas as pd


def main() -> int:
    print('=' * 70)
    print('📊 GENERATED FILES')
    print('=' * 70)

    clean_file = './data/clean/smartgrid_clean_fast.csv'
    attack_file = './data/attacks/attacks_fast.csv'

    if os.path.exists(clean_file):
        clean = pd.read_csv(clean_file)
        print(f'\n✅ CLEAN DATA: {clean_file}')
        print(f'   Rows: {len(clean):,}')
        print(f'   Columns: {list(clean.columns)}')
        print('\n   Sample:')
        print(clean.head(3).to_string())
        print('\n   Statistics:')
        print(f'   - Avg consumption: {clean["consumption_kw"].mean():.2f} kW')
        print(f'   - Avg voltage: {clean["voltage_pu"].mean():.4f} pu')
    else:
        print(f'❌ Not found: {clean_file}')

    if os.path.exists(attack_file):
        attacks = pd.read_csv(attack_file)
        print(f'\n✅ ATTACK DATA: {attack_file}')
        print(f'   Rows: {len(attacks):,}')
        print(f'   Attack types: {list(attacks["attack_type"].unique())}')
        print('   Attack distribution:')
        for attack_type, count in attacks['attack_type'].value_counts().items():
            print(f'      - {attack_type}: {count:,}')
        print('\n   Sample FDIA attack:')
        fdia = attacks[attacks['attack_type'] == 'fdia'].head(2)
        print(fdia.to_string())
    else:
        print(f'❌ Not found: {attack_file}')

    print('\n' + '=' * 70)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
