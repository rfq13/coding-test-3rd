-- Initialize pgvector and trigram extensions only at cluster bootstrap.
-- Tables and indexes are created by the application after schema setup.
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;