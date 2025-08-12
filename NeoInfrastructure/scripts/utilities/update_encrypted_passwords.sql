-- Update database connections with properly encrypted passwords
-- Password 'postgres' encrypted with key 'KDEAXgazY0zwe6ZkVsXT980pDADnoX9I'

UPDATE admin.database_connections 
SET 
    encrypted_password = 'gAAAAABol4ATGxSZIbqI00K0du_r2yesIsV_AUgGyZ5oeuI6jhs-6suJ07tkS8HuzEI0fT366Cllhozg5uGOSFSUQ3hI3kY2GA==',
    updated_at = NOW()
WHERE connection_name IN (
    'neofast-admin-primary',
    'neofast-shared-us-primary', 
    'neofast-analytics-us',
    'neofast-shared-eu-primary',
    'neofast-analytics-eu'
);

-- Verify the update
SELECT 
    connection_name,
    host,
    database_name,
    LEFT(encrypted_password, 20) || '...' as encrypted_pwd_preview,
    updated_at
FROM admin.database_connections 
ORDER BY connection_name;