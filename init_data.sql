-- Initialize views, functions, and data

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
