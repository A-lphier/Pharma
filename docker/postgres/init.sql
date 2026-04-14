-- init.sql - Inizializzazione database FatturaMVP
-- Crea estensioni e utente applicativo

-- Abilita estensioni utili
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Crea tablespace custom per partizioni future (opzionale)
-- CREATE TABLESPACE fatturamvp_tablespace LOCATION '/var/lib/postgresql/tablespaces/fatturamvp';

-- Log configurazione
-- I log delle query lente vengono configurati tramite postgresql.conf
