-- Create tables

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(50) NOT NULL DEFAULT 'viewer',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE smart_meters (
    id SERIAL PRIMARY KEY,
    bus_id INTEGER UNIQUE NOT NULL,
    voltage FLOAT,
    current FLOAT,
    power FLOAT,
    frequency FLOAT,
    status VARCHAR(50) DEFAULT 'online',
    consumer_type VARCHAR(100),
    last_reading TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE alerts (
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
    FOREIGN KEY (bus_id) REFERENCES smart_meters(bus_id) ON DELETE CASCADE
);

CREATE TABLE fcm_tokens (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) NOT NULL,
    token VARCHAR(255) UNIQUE NOT NULL,
    device_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    last_used TIMESTAMP,
    FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
);

CREATE TABLE blockchain_ledger (
    id SERIAL PRIMARY KEY,
    block_number INTEGER UNIQUE NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    data JSONB,
    hash VARCHAR(255) UNIQUE NOT NULL,
    previous_hash VARCHAR(255),
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255),
    action VARCHAR(255),
    resource VARCHAR(255),
    details JSONB,
    ip_address VARCHAR(45),
    status_code INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes
CREATE INDEX idx_alerts_bus ON alerts(bus_id);
CREATE INDEX idx_alerts_created ON alerts(created_at DESC);
CREATE INDEX idx_alerts_severity ON alerts(severity);
CREATE INDEX idx_alerts_resolved ON alerts(is_resolved);
CREATE INDEX idx_meters_bus ON smart_meters(bus_id);
CREATE INDEX idx_meters_status ON smart_meters(status);
CREATE INDEX idx_fcm_username ON fcm_tokens(username);
CREATE INDEX idx_fcm_active ON fcm_tokens(is_active);
CREATE INDEX idx_blockchain_block ON blockchain_ledger(block_number DESC);
CREATE INDEX idx_blockchain_verified ON blockchain_ledger(is_verified);
CREATE INDEX idx_audit_created ON audit_log(created_at DESC);
CREATE INDEX idx_audit_username ON audit_log(username);

-- Create view
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

-- Insert default users
INSERT INTO users (username, password_hash, full_name, role)
VALUES
    ('admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5YmMxSUFutQFu', 'Admin User', 'administrator'),
    ('operator', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5YmMxSUFutQFu', 'Grid Operator', 'grid_operator'),
    ('analyst', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5YmMxSUFutQFu', 'Data Analyst', 'analyst'),
    ('viewer', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5YmMxSUFutQFu', 'Viewer User', 'viewer')
ON CONFLICT (username) DO NOTHING;

-- Insert 14 smart meters
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
