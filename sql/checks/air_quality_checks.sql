-- 1. Required keys and timestamps must not be null
SELECT COUNT(*) AS invalid_required_fields
FROM core.fact_air_quality
WHERE site_code IS NULL
   OR species_code IS NULL
   OR measurement_timestamp_utc IS NULL;

-- 2. Natural key must be unique
SELECT COUNT(*) AS duplicate_keys
FROM (
    SELECT site_code, species_code, measurement_timestamp_utc
    FROM core.fact_air_quality
    GROUP BY 1, 2, 3
    HAVING COUNT(*) > 1
) duplicates;

-- 3. Values should not be negative
-- SELECT COUNT(*) AS negative_values
-- FROM core.fact_air_quality
-- WHERE value < 0;

-- Report negative readings for review.
-- Negative values are retained; this is an informational check.
SELECT
    species_code,
    COUNT(*) AS negative_readings,
    MIN(value) AS minimum_value
FROM core.fact_air_quality
WHERE value < 0
GROUP BY species_code;

-- 4. Facts should have matching dimension records
SELECT COUNT(*) AS missing_dimension_records
FROM core.fact_air_quality f
LEFT JOIN core.dim_site s USING (site_code)
LEFT JOIN core.dim_species p USING (species_code)
WHERE s.site_code IS NULL
   OR p.species_code IS NULL;