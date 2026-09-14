-- Smart Grid Database Schema
-- PostgreSQL 15+
-- This schema replaces JSON file storage with a proper relational database

-- ============================================================================
-- TABLE: users (replaces users.json)
-- ============================================================================
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(50) NOT NULL DEFAULT 'viewer',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT valid_role CHECK (role IN ('viewer', 'analyst', 'grid_operator', 'administrator'))
);

-- ============================================================================
-- TABLE: smart_meters
-- ============================================================================
CREATE TABLE IF NOT EXISTS smart_meters (
    id SERIAL PRIMARY KEY,
    bus_id INTEGER UNIQUE NOT NULL,
    voltage FLOAT,
    current FLOAT,
    power FLOAT,
    frequency FLOAT,
    status VARCHAR(50) DEFAULT 'online',
    consumer_type VARCHAR(100),
    last_reading TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT valid_status CHECK (status IN ('online', 'offline', 'error'))
);

-- ============================================================================
-- TABLE: alerts (anomalies detected by AI)
-- ============================================================================
CREATE TABLE IF NOT EXISTS alerts (
    id SERIAL PRIMARY KEY,
    bus_id INTEGER NOT NULL,
    alert_type VARCHAR(100) NOT NULL,
    attack_type VARCHAR(50),
    confidence FLOAT NOT NULL,
    severity VARCHAR(50) NOT NULL,
    description TEXT,
    is_resolved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    resolved_at TIMESTAMP,
    FOREIGN KEY (bus_id) REFERENCES smart_meters(bus_id) ON DELETE CASCADE,
    CONSTRAINT valid_severity CHECK (severity IN ('info', 'warning', 'critical')),
    CONSTRAINT valid_confidence CHECK (confidence >= 0 AND confidence <= 1)
);

-- ============================================================================
-- TABLE: fcm_tokens (Firebase Cloud Messaging tokens for push notifications)
-- ============================================================================
CREATE TABLE IF NOT EXISTS fcm_tokens (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) NOT NULL,
    token VARCHAR(255) UNIQUE NOT NULL,
    device_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    last_used TIMESTAMP,
    FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
);

-- ============================================================================
-- TABLE: blockchain_ledger (replaces poa_ledger.json)
-- ============================================================================
CREATE TABLE IF NOT EXISTS blockchain_ledger (
    id SERIAL PRIMARY KEY,
    block_number INTEGER UNIQUE NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    data JSONB,
    hash VARCHAR(255) UNIQUE NOT NULL,
    previous_hash VARCHAR(255),
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT valid_hash CHECK (hash IS NOT NULL AND previous_hash IS NOT NULL)
);

-- ============================================================================
-- TABLE: audit_log (tracks all API operations for compliance)
-- ============================================================================
CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255),
    action VARCHAR(255),
    resource VARCHAR(255),
    details JSONB,
    ip_address VARCHAR(45),
    status_code INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- INDEXES (for performance optimization)
-- ============================================================================

-- Alerts indexes
CREATE INDEX IF NOT EXISTS idx_alerts_bus ON alerts(bus_id);
CREATE INDEX IF NOT EXISTS idx_alerts_created ON alerts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity);
CREATE INDEX IF NOT EXISTS idx_alerts_resolved ON alerts(is_resolved);

-- Smart meters indexes
CREATE INDEX IF NOT EXISTS idx_meters_bus ON smart_meters(bus_id);
CREATE INDEX IF NOT EXISTS idx_meters_status ON smart_meters(status);

-- FCM tokens indexes
CREATE INDEX IF NOT EXISTS idx_fcm_username ON fcm_tokens(username);
CREATE INDEX IF NOT EXISTS idx_fcm_active ON fcm_tokens(is_active);

-- Blockchain indexes
CREATE INDEX IF NOT EXISTS idx_blockchain_block ON blockchain_ledger(block_number DESC);
CREATE INDEX IF NOT EXISTS idx_blockchain_verified ON blockchain_ledger(is_verified);

-- Audit log indexes
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_username ON audit_log(username);

-- ============================================================================
-- VIEWS (for common queries)
-- ============================================================================

-- View: Active alerts with meter details
CREATE OR REPLACE VIEW active_alerts_view AS
SELECT
    a.id,
    a.bus_id,
    m.voltage,
    m.current,
    m.power,
    a.alert_type,
    a.attack_type,
    a.confidence,
    a.severity,
    a.description,
    a.created_at
FROM alerts a
LEFT JOIN smart_meters m ON a.bus_id = m.bus_id
WHERE a.is_resolved = FALSE
ORDER BY a.created_at DESC;

-- View: Grid status summary
CREATE OR REPLACE VIEW grid_status_view AS
SELECT
    COUNT(*) as total_meters,
    SUM(CASE WHEN status = 'online' THEN 1 ELSE 0 END) as online_meters,
    SUM(CASE WHEN status = 'offline' THEN 1 ELSE 0 END) as offline_meters,
    ROUND(AVG(voltage)::numeric, 2) as avg_voltage,
    ROUND(SUM(power)::numeric, 2) as total_power,
    (SELECT COUNT(*) FROM alerts WHERE is_resolved = FALSE) as active_alerts
FROM smart_meters;

-- ============================================================================
-- FUNCTIONS (for common operations)
-- ============================================================================

-- Function: Update alert resolution timestamp
CREATE OR REPLACE FUNCTION resolve_alert(alert_id INT) RETURNS VOID AS $$
BEGIN
    UPDATE alerts
    SET is_resolved = TRUE, resolved_at = NOW()
    WHERE id = alert_id;
END;
$$ LANGUAGE plpgsql;

-- Function: Get unread alerts count for a user
CREATE OR REPLACE FUNCTION count_unread_alerts() RETURNS INTEGER AS $$
BEGIN
    RETURN (SELECT COUNT(*) FROM alerts WHERE is_resolved = FALSE);
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- INITIAL DATA (optional test users)
-- ============================================================================

-- Insert default users (if they don't exist)
INSERT INTO users (username, password_hash, full_name, role)
VALUES
    ('admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5YmMxSUFutQFu', 'Admin User', 'administrator'),
    ('operator', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5YmMxSUFutQFu', 'Grid Operator', 'grid_operator'),
    ('analyst', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5YmMxSUFutQFu', 'Data Analyst', 'analyst'),
    ('viewer', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5YmMxSUFutQFu', 'Viewer User', 'viewer')
ON CONFLICT (username) DO NOTHING;

-- Insert 14 smart meters (buses)
INSERT INTO smart_meters (bus_id, status, consumer_type)
VALUES
    (1, 'online', 'Industrial'),
    (2, 'online', 'Commercial'),
    (3, 'online', 'Residential'),
    (4, 'online', 'Industrial'),
    (5, 'online', 'Commercial'),
    (6, 'online', 'Residential'),
    (7, 'online', 'Industrial'),
    (8, 'online', 'Commercial'),
    (9, 'online', 'Residential'),
    (10, 'online', 'Industrial'),
    (11, 'online', 'Commercial'),
    (12, 'online', 'Residential'),
    (13, 'online', 'Industrial'),
    (14, 'online', 'Commercial')
ON CONFLICT (bus_id) DO NOTHING;

-- ============================================================================
-- COMMENTS (for documentation)
-- ============================================================================

COMMENT ON TABLE users IS 'User accounts with role-based access control (RBAC)';
COMMENT ON TABLE smart_meters IS 'IoT Smart meter readings and status';
COMMENT ON TABLE alerts IS 'AI-detected anomalies and attacks';
COMMENT ON TABLE fcm_tokens IS 'Firebase Cloud Messaging tokens for push notifications';
COMMENT ON TABLE blockchain_ledger IS 'Proof-of-Authority blockchain ledger for audit trail';
COMMENT ON TABLE audit_log IS 'Complete audit trail of API operations for compliance';

COMMENT ON COLUMN users.role IS 'viewer|analyst|grid_operator|administrator';
COMMENT ON COLUMN alerts.confidence IS 'Confidence score 0.0-1.0';
COMMENT ON COLUMN blockchain_ledger.is_verified IS 'Whether block has been verified on-chain';
