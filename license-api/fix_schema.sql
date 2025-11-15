-- Add missing column to app_versions table
ALTER TABLE app_versions 
ADD COLUMN IF NOT EXISTS is_required BOOLEAN DEFAULT FALSE;

-- Verify the column was added
SELECT column_name, data_type, column_default 
FROM information_schema.columns 
WHERE table_name = 'app_versions';
