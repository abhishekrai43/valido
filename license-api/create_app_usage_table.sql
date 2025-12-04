-- Create app_usage table for tracking active users
-- Run this in Supabase SQL Editor

CREATE TABLE IF NOT EXISTS app_usage (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(64) UNIQUE NOT NULL,
    app_version VARCHAR(20),
    action VARCHAR(50) DEFAULT 'app_open',
    platform VARCHAR(20) DEFAULT 'Windows',
    open_count INTEGER DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for quick lookups
CREATE INDEX IF NOT EXISTS idx_app_usage_device_id ON app_usage(device_id);
CREATE INDEX IF NOT EXISTS idx_app_usage_last_seen ON app_usage(last_seen);

-- Useful queries for analytics:

-- Count unique users in last 7 days
-- SELECT COUNT(DISTINCT device_id) FROM app_usage WHERE last_seen > NOW() - INTERVAL '7 days';

-- Count unique users in last 30 days  
-- SELECT COUNT(DISTINCT device_id) FROM app_usage WHERE last_seen > NOW() - INTERVAL '30 days';

-- Daily active users
-- SELECT DATE(last_seen) as date, COUNT(DISTINCT device_id) as dau 
-- FROM app_usage 
-- WHERE last_seen > NOW() - INTERVAL '30 days'
-- GROUP BY DATE(last_seen) 
-- ORDER BY date DESC;

-- Total opens by version
-- SELECT app_version, COUNT(*) as users, SUM(open_count) as total_opens
-- FROM app_usage
-- GROUP BY app_version
-- ORDER BY users DESC;
