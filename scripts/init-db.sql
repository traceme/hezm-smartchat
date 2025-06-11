-- SmartChat Database Initialization Script
-- This script runs when the PostgreSQL container starts for the first time

-- Create the database if it doesn't exist (handled by POSTGRES_DB env var)
-- Create extensions for better performance and functionality
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text similarity search

-- Set timezone
SET timezone = 'UTC';

-- Create indexes that might be needed for performance
-- Note: The actual table creation is handled by SQLAlchemy migrations

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON DATABASE smartchat TO postgres;

-- Log the successful initialization
DO $$
BEGIN
    RAISE NOTICE 'SmartChat database initialized successfully at %', NOW();
END
$$; 