-- Production seed data for Supabase.
--
-- init_data.sql (dev) gives all 4 default accounts the SAME bcrypt hash —
-- a real credential-reuse risk if deployed to a client-facing environment
-- as-is. This file uses unique, randomly generated passwords instead. Run
-- this INSTEAD OF init_data.sql when seeding the Supabase database.
--
-- IMPORTANT: change these passwords again after the first login, and do not
-- commit this file's passwords anywhere public once used — rotate them.

-- Grid status view (same as init_data.sql)
CREATE OR REPLACE VIEW grid_status_view AS
SELECT
    COUNT(*) as total_meters,
    SUM(CASE WHEN status = 'online' THEN 1 ELSE 0 END) as online_meters,
    SUM(CASE WHEN status = 'offline' THEN 1 ELSE 0 END) as offline_meters,
    ROUND(AVG(voltage)::numeric, 2) as avg_voltage,
    ROUND(SUM(power)::numeric, 2) as total_power,
    (SELECT COUNT(*) FROM alerts WHERE is_resolved = FALSE) as active_alerts
FROM smart_meters;

-- Default users — UNIQUE password per account (plaintext given once here so
-- whoever runs this can hand them to the client; delete this file's local
-- copy after the handoff).
--   admin    / o9nv43LvzseFoL3-
--   operator / 8AlJSKQKKrFaALSi
--   analyst  / dr-IbvFwkbUnnNQH
--   viewer   / tavzwNzKUGduakuJ
INSERT INTO users (username, password_hash, full_name, role)
VALUES
    ('admin',    '$2b$12$aqEquqB5nRxxe1qXDwLNR.pVNFyC8ITpKeenC6oHFt0xjun/6bdh6', 'Admin User',   'administrator'),
    ('operator', '$2b$12$Xa.tN2i5Y0OkHw.LHc98KuhLS37j03HVex4xwk5dQ/oDOsSURmwtm', 'Grid Operator', 'grid_operator'),
    ('analyst',  '$2b$12$ycBnhF2niakysd8315doO.8.btM/cMK1WsD/cJsND0rQ9R0xZulNK', 'Data Analyst',  'analyst'),
    ('viewer',   '$2b$12$4sVVSr8TZiZ6trEQ4pl9qu0hDi7ul.SSADRy8wptwXPfW1HfWC/pG', 'Viewer User',   'viewer')
ON CONFLICT (username) DO NOTHING;

-- 14 smart meters (same as init_data.sql)
INSERT INTO smart_meters (bus_id, status, consumer_type)
VALUES
    (1, 'online', 'Industrial'),
    (2, 'online', 'Commercial'),
    (3, 'online', 'Residential'),
    (4, 'online', 'Industrial'),
    (5, 'online', 'Commercial'),
    (6, 'online', 'Residential'),
    (7, 'online', 'Residential'),
    (8, 'online', 'Commercial'),
    (9, 'online', 'Residential'),
    (10, 'online', 'Commercial'),
    (11, 'online', 'Residential'),
    (12, 'online', 'Commercial'),
    (13, 'online', 'Residential'),
    (14, 'online', 'Industrial')
ON CONFLICT (bus_id) DO NOTHING;
