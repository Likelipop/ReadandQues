SELECT 'CREATE DATABASE dagster_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'dagster_db')\gexec
