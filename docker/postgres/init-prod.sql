-- Production Database Initialization Script
-- This script runs when the PostgreSQL container starts for the first time

-- Create database user if not exists (for production)
DO $$ 
BEGIN 
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'investigator_user') THEN
      CREATE USER investigator_user WITH PASSWORD 'change-this-password';
      RAISE NOTICE 'Created user investigator_user';
   END IF;
END
$$;

-- Create extensions (useful for Django)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Grant privileges (only if the database exists)
DO $$
BEGIN
    -- Check if database exists before granting privileges
    IF EXISTS (SELECT 1 FROM pg_database WHERE datname = 'investigator_prod') THEN
        EXECUTE 'GRANT ALL PRIVILEGES ON DATABASE investigator_prod TO investigator_user';
        RAISE NOTICE 'Granted privileges on investigator_prod to investigator_user';
    ELSE
        RAISE NOTICE 'Database investigator_prod will be created by environment variables';
    END IF;
    
    -- Grant database creation privileges
    ALTER USER investigator_user CREATEDB;
END
$$;

-- Output success message
DO $$
BEGIN
    RAISE NOTICE 'Production database initialized successfully!';
END $$;