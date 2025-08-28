-- Migration: Add timezone field to users table
-- Description: Add timezone preference field for user timezone handling

-- Add timezone field to users table
ALTER TABLE users 
ADD COLUMN timezone TEXT DEFAULT 'UTC';

-- Add index for timezone field for efficient timezone-based queries
CREATE INDEX idx_users_timezone ON users(timezone);

-- Add constraint to validate timezone format (basic validation)
-- Most validation will be done at application level for better error messages
ALTER TABLE users 
ADD CONSTRAINT check_timezone_format 
CHECK (timezone ~ '^[A-Za-z0-9_/+-]+$' AND length(timezone) <= 64);

-- Update existing users to have UTC timezone as default
UPDATE users 
SET timezone = 'UTC' 
WHERE timezone IS NULL;

-- Add comment
COMMENT ON COLUMN users.timezone IS 'User preferred timezone (IANA timezone identifier, e.g., America/New_York, UTC)';