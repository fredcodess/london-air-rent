CREATE TABLE IF NOT EXISTS staging.rent_monthly (
    month DATE NOT NULL,
    borough_code TEXT NOT NULL,
    borough_name TEXT NOT NULL,
    rent_gbp NUMERIC(10, 2) NOT NULL,
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS core.dim_borough (
    borough_code TEXT PRIMARY KEY,
    borough_name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS core.fact_rent (
    borough_code TEXT NOT NULL
        REFERENCES core.dim_borough (borough_code),
    month DATE NOT NULL,
    rent_gbp NUMERIC(10, 2) NOT NULL,
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (borough_code, month),

    CONSTRAINT chk_fact_rent_positive
        CHECK (rent_gbp > 0)
);