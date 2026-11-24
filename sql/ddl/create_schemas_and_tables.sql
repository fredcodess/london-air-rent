CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS core;

CREATE TABLE IF NOT EXISTS staging.air_quality_measurements (
    site_code TEXT NOT NULL,
    species_code TEXT NOT NULL,
    measurement_timestamp_utc TIMESTAMPTZ NOT NULL,
    value DOUBLE PRECISION,
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS core.dim_site (
    site_code TEXT PRIMARY KEY,
    site_name TEXT,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    borough_name TEXT
);

CREATE TABLE IF NOT EXISTS core.dim_species (
    species_code TEXT PRIMARY KEY,
    species_name TEXT
);

CREATE TABLE IF NOT EXISTS core.fact_air_quality (
    site_code TEXT NOT NULL REFERENCES core.dim_site(site_code),
    species_code TEXT NOT NULL REFERENCES core.dim_species(species_code),
    measurement_timestamp_utc TIMESTAMPTZ NOT NULL,
    value DOUBLE PRECISION,
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (site_code, species_code, measurement_timestamp_utc)
);