-- Executed once on first container start (empty data volume).
-- Enables pgvector (semantic retrieval) and uuid-ossp (uuid_generate_v4 defaults).
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
