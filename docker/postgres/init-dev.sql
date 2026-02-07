-- Development Database Initialization Script
-- This script runs when the PostgreSQL container starts for the first time

-- Create extensions (useful for Django)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Grant additional privileges to the default postgres user for development
-- This ensures Django can create/drop test databases during development
ALTER USER postgres CREATEDB;
ALTER USER postgres WITH SUPERUSER;

-- Output success message
DO $$
BEGIN
    RAISE NOTICE 'Development database initialized successfully!';
END $$;