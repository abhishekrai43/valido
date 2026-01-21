-- Fix for /api/validate 500 error:
-- psycopg2.errors.InvalidColumnReference: there is no unique or exclusion constraint
-- matching the ON CONFLICT specification
--
-- This API uses:
--   INSERT INTO license_usage (license_key, device_id, last_validated)
--   ...
--   ON CONFLICT (license_key, device_id) DO UPDATE ...
--
-- Postgres requires a UNIQUE constraint or UNIQUE index on (license_key, device_id)
-- for that ON CONFLICT clause to be valid.

-- Create table if it doesn't exist (safe)
CREATE TABLE IF NOT EXISTS license_usage (
    id SERIAL PRIMARY KEY,
    license_key TEXT NOT NULL,
    device_id TEXT NOT NULL,
    last_validated TIMESTAMPTZ DEFAULT NOW()
);

-- Add the missing unique index needed for ON CONFLICT (license_key, device_id)
CREATE UNIQUE INDEX IF NOT EXISTS ux_license_usage_license_key_device_id
    ON license_usage (license_key, device_id);

-- Optional: supporting indexes
CREATE INDEX IF NOT EXISTS idx_license_usage_license_key
    ON license_usage (license_key);

CREATE INDEX IF NOT EXISTS idx_license_usage_last_validated
    ON license_usage (last_validated);
