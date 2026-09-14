#!/usr/bin/env python3
"""
Migration script: JSON files → PostgreSQL database
Migrates data from JSON storage to PostgreSQL for production use.

Usage:
    python migration_json_to_postgres.py
"""

import json
import os
import sys
from pathlib import Path
import psycopg2
from psycopg2.extras import execute_values
import time

# ============================================================================
# Configuration
# ============================================================================

DATABASE_URL = "postgresql://admin:admin123@localhost:5432/smartgrid"
DATA_DIR = Path(__file__).parent / "data"
SCHEMA_FILE = Path(__file__).parent / "production/database/schema.sql"

# ============================================================================
# Helper functions
# ============================================================================

def connect_db():
    """Connect to PostgreSQL database."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        print("✅ Connected to PostgreSQL")
        return conn
    except psycopg2.OperationalError as e:
        print(f"❌ Failed to connect to database: {e}")
        sys.exit(1)


def execute_sql_file(conn, sql_file):
    """Execute SQL schema file."""
    try:
        with open(sql_file, 'r') as f:
            sql = f.read()

        cursor = conn.cursor()
        cursor.execute(sql)
        conn.commit()
        print(f"✅ Schema created from {sql_file}")
        cursor.close()
    except Exception as e:
        print(f"❌ Error executing schema: {e}")
        conn.rollback()
        sys.exit(1)


def load_json(file_path):
    """Load JSON file safely."""
    if not os.path.exists(file_path):
        print(f"⚠️  {file_path} not found, skipping")
        return []

    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"⚠️  {file_path} is invalid JSON, skipping")
        return []


def migrate_users(conn):
    """Migrate users from users.json to users table."""
    print("\n📁 Migrating users...")

    users_file = DATA_DIR / "users.json"
    users_data = load_json(users_file)

    if not users_data:
        print("   No users to migrate")
        return

    if isinstance(users_data, dict) and 'users' in users_data:
        users_data = users_data['users']

    try:
        cursor = conn.cursor()

        for user in users_data:
            cursor.execute("""
                INSERT INTO users (username, password_hash, full_name, role)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (username) DO NOTHING
            """, (
                user.get('username'),
                user.get('password_hash', ''),
                user.get('full_name', ''),
                user.get('role', 'viewer')
            ))

        conn.commit()
        print(f"   ✅ Migrated {len(users_data)} users")
        cursor.close()
    except Exception as e:
        print(f"   ❌ Error migrating users: {e}")
        conn.rollback()


def migrate_smart_meters(conn):
    """Migrate smart meters data."""
    print("\n📊 Migrating smart meters...")

    # Initialize 14 meters with data from readings if available
    try:
        cursor = conn.cursor()

        # Meters should already be created by schema, just update if we have data
        readings_file = DATA_DIR / "meter_readings.json"
        readings = load_json(readings_file)

        if readings:
            for reading in readings:
                cursor.execute("""
                    UPDATE smart_meters
                    SET voltage = %s, current = %s, power = %s,
                        frequency = %s, last_reading = NOW()
                    WHERE bus_id = %s
                """, (
                    reading.get('voltage'),
                    reading.get('current'),
                    reading.get('power'),
                    reading.get('frequency'),
                    reading.get('bus_id')
                ))

        conn.commit()
        print("   ✅ Smart meters initialized (14 buses)")
        cursor.close()
    except Exception as e:
        print(f"   ❌ Error migrating smart meters: {e}")
        conn.rollback()


def migrate_alerts(conn):
    """Migrate alerts from JSON to database."""
    print("\n⚠️  Migrating alerts...")

    alerts_file = DATA_DIR / "alerts.json"
    alerts_data = load_json(alerts_file)

    if not alerts_data:
        print("   No alerts to migrate")
        return

    if isinstance(alerts_data, dict) and 'alerts' in alerts_data:
        alerts_data = alerts_data['alerts']

    try:
        cursor = conn.cursor()

        for alert in alerts_data:
            cursor.execute("""
                INSERT INTO alerts (bus_id, alert_type, attack_type, confidence, severity, description)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                alert.get('bus_id'),
                alert.get('alert_type', 'unknown'),
                alert.get('attack_type'),
                alert.get('confidence', 0.0),
                alert.get('severity', 'warning'),
                alert.get('description', '')
            ))

        conn.commit()
        print(f"   ✅ Migrated {len(alerts_data)} alerts")
        cursor.close()
    except Exception as e:
        print(f"   ❌ Error migrating alerts: {e}")
        conn.rollback()


def migrate_fcm_tokens(conn):
    """Migrate FCM tokens from JSON to database."""
    print("\n📱 Migrating FCM tokens...")

    fcm_file = DATA_DIR / "fcm_tokens.json"
    fcm_data = load_json(fcm_file)

    if not fcm_data:
        print("   No FCM tokens to migrate")
        return

    try:
        cursor = conn.cursor()

        for token_key, token_info in fcm_data.items():
            cursor.execute("""
                INSERT INTO fcm_tokens (username, token, device_name, is_active)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (token) DO NOTHING
            """, (
                token_info.get('username', 'unknown'),
                token_key,
                token_info.get('device_name', 'Unknown Device'),
                token_info.get('active', True)
            ))

        conn.commit()
        print(f"   ✅ Migrated {len(fcm_data)} FCM tokens")
        cursor.close()
    except Exception as e:
        print(f"   ❌ Error migrating FCM tokens: {e}")
        conn.rollback()


def migrate_blockchain(conn):
    """Migrate blockchain ledger from JSON to database."""
    print("\n🔗 Migrating blockchain ledger...")

    ledger_file = DATA_DIR / "poa_ledger.json"
    ledger_data = load_json(ledger_file)

    if not ledger_data:
        print("   No blockchain data to migrate")
        return

    if isinstance(ledger_data, dict) and 'blocks' in ledger_data:
        ledger_data = ledger_data['blocks']

    try:
        cursor = conn.cursor()

        for idx, block in enumerate(ledger_data):
            cursor.execute("""
                INSERT INTO blockchain_ledger
                (block_number, timestamp, data, hash, previous_hash, is_verified)
                VALUES (%s, NOW(), %s, %s, %s, %s)
                ON CONFLICT (block_number) DO NOTHING
            """, (
                idx,
                json.dumps(block.get('data', {})),
                block.get('hash'),
                block.get('previous_hash'),
                block.get('is_verified', False)
            ))

        conn.commit()
        print(f"   ✅ Migrated {len(ledger_data)} blockchain blocks")
        cursor.close()
    except Exception as e:
        print(f"   ❌ Error migrating blockchain: {e}")
        conn.rollback()


def verify_migration(conn):
    """Verify migration was successful."""
    print("\n🔍 Verifying migration...")

    try:
        cursor = conn.cursor()

        tables = {
            'users': 'SELECT COUNT(*) FROM users',
            'smart_meters': 'SELECT COUNT(*) FROM smart_meters',
            'alerts': 'SELECT COUNT(*) FROM alerts',
            'fcm_tokens': 'SELECT COUNT(*) FROM fcm_tokens',
            'blockchain_ledger': 'SELECT COUNT(*) FROM blockchain_ledger'
        }

        for table, query in tables.items():
            cursor.execute(query)
            count = cursor.fetchone()[0]
            print(f"   {table}: {count} records")

        cursor.close()
        print("\n✅ Migration verification complete!")
    except Exception as e:
        print(f"❌ Verification failed: {e}")


# ============================================================================
# Main
# ============================================================================

def main():
    """Run migration."""
    print("╔════════════════════════════════════════════════════════╗")
    print("║  Smart Grid: JSON → PostgreSQL Migration               ║")
    print("╚════════════════════════════════════════════════════════╝\n")

    # Connect to database
    conn = connect_db()

    # Create schema
    print(f"\n📋 Creating schema from {SCHEMA_FILE}...")
    execute_sql_file(conn, SCHEMA_FILE)

    # Run migrations
    print("\n🔄 Running migrations...\n")
    migrate_users(conn)
    migrate_smart_meters(conn)
    migrate_alerts(conn)
    migrate_fcm_tokens(conn)
    migrate_blockchain(conn)

    # Verify
    verify_migration(conn)

    # Cleanup
    conn.close()

    print("\n╔════════════════════════════════════════════════════════╗")
    print("║  ✅ Migration Complete!                               ║")
    print("║  Next: Update API endpoints to use database           ║")
    print("╚════════════════════════════════════════════════════════╝\n")


if __name__ == "__main__":
    main()
