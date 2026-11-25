CREATE SCHEMA IF NOT EXISTS analytics;

CREATE OR REPLACE VIEW analytics.borough_monthly_air_rent AS
WITH monthly_air_quality AS (
    SELECT
        mapping.borough_code,
        DATE_TRUNC(
            'month',
            fact.measurement_timestamp_utc
        )::DATE AS month,
        AVG(fact.value) AS average_no2,
        COUNT(*) AS no2_measurement_count
    FROM core.fact_air_quality AS fact
    INNER JOIN core.dim_site AS site
        ON site.site_code = fact.site_code
    INNER JOIN core.dim_species AS species
        ON species.species_code = fact.species_code
    INNER JOIN core.dim_laqn_borough_mapping AS mapping
        ON mapping.laqn_borough_name = site.borough_name
    WHERE species.species_name = 'Nitrogen Dioxide'
      AND mapping.borough_code IS NOT NULL
    GROUP BY
        mapping.borough_code,
        DATE_TRUNC(
            'month',
            fact.measurement_timestamp_utc
        )::DATE
),
monthly_rent AS (
    SELECT
        borough_code,
        DATE_TRUNC('month', month)::DATE AS month,
        AVG(rent_gbp) AS average_rent_gbp
    FROM core.fact_rent
    GROUP BY
        borough_code,
        DATE_TRUNC('month', month)::DATE
)
SELECT
    rent.borough_code,
    borough.borough_name,
    rent.month,
    air.average_no2,
    COALESCE(air.no2_measurement_count, 0)
        AS no2_measurement_count,
    rent.average_rent_gbp
FROM monthly_rent AS rent
INNER JOIN core.dim_borough AS borough
    ON borough.borough_code = rent.borough_code
LEFT JOIN monthly_air_quality AS air
    ON air.borough_code = rent.borough_code
   AND air.month = rent.month;