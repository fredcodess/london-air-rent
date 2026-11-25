CREATE TABLE IF NOT EXISTS core.borough_monthly_air_rent (
    borough_code TEXT NOT NULL
        REFERENCES core.dim_borough (borough_code),
    month DATE NOT NULL,
    average_no2 NUMERIC(10, 4),
    no2_measurement_count INTEGER NOT NULL DEFAULT 0,
    average_rent_gbp NUMERIC(10, 2),
    PRIMARY KEY (borough_code, month)
);