CREATE TABLE IF NOT EXISTS core.dim_laqn_borough_mapping (
    laqn_borough_name TEXT PRIMARY KEY,
    borough_code TEXT
        REFERENCES core.dim_borough (borough_code),
    mapping_note TEXT
);

INSERT INTO core.dim_laqn_borough_mapping (
    laqn_borough_name,
    borough_code,
    mapping_note
)
SELECT
    mapping.laqn_name,
    borough.borough_code,
    mapping.mapping_note
FROM (
    VALUES
        ('Barking and Dagenham', 'Barking and Dagenham', NULL),
        ('Barnet', 'Barnet', NULL),
        ('Bexley', 'Bexley', NULL),
        ('Brent', 'Brent', NULL),
        ('Bromley', 'Bromley', NULL),
        ('Camden', 'Camden', NULL),
        ('City of London', NULL, 'No matching ONS borough in this dataset'),
        ('Croydon', 'Croydon', NULL),
        ('Ealing', 'Ealing', NULL),
        ('Enfield', 'Enfield', NULL),
        ('Greenwich', 'Greenwich', NULL),
        ('Hackney', 'Hackney', NULL),
        ('Hammersmith and Fulham', 'Hammersmith and Fulham', NULL),
        ('Haringey', 'Haringey', NULL),
        ('Harrow', 'Harrow', NULL),
        ('Havering', 'Havering', NULL),
        ('Hillingdon', 'Hillingdon', NULL),
        ('Hounslow', 'Hounslow', NULL),
        ('Islington', 'Islington', NULL),
        ('Kensington and Chelsea', 'Kensington and Chelsea', NULL),
        ('Kingston', 'Kingston upon Thames', 'Name standardized to ONS'),
        ('Lambeth', 'Lambeth', NULL),
        ('Lewisham', 'Lewisham', NULL),
        ('Merton', 'Merton', NULL),
        ('Newham', 'Newham', NULL),
        ('Redbridge', 'Redbridge', NULL),
        ('Richmond', 'Richmond upon Thames', 'Name standardized to ONS'),
        ('Southwark', 'Southwark', NULL),
        ('Sutton', 'Sutton', NULL),
        ('Tower Hamlets', 'Tower Hamlets', NULL),
        ('Waltham Forest', 'Waltham Forest', NULL),
        ('Wandsworth', 'Wandsworth', NULL),
        ('Westminster', 'Westminster', NULL)
) AS mapping(laqn_name, ons_name, mapping_note)
LEFT JOIN core.dim_borough AS borough
    ON borough.borough_name = mapping.ons_name
ON CONFLICT (laqn_borough_name)
DO UPDATE SET
    borough_code = EXCLUDED.borough_code,
    mapping_note = EXCLUDED.mapping_note;