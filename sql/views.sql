/* 
CREATION OF VIEWS

this file contains the queries of 4 SQL views generated on data

1. vw_daily_air_quality -> daily pollutant averages/max
2. vw_hourly_pattern -> hour-of-day + weekday patterns
3. vw_pm25_category -> PM2.5 air quality category
4. vw_station_coverage -> station data completeness
*/


-- 1. Daily Air Quality
CREATE OR REPLACE VIEW vw_daily_air_quality AS
SELECT
    dd.date AS measurement_date,
    dl.location_id,
    dl.name as location_name,
    dl.city,
    dl.latitude,
    dl.longitude,
    dp.name as pollutant,
    dp.display_name,
    dp.unit,
    ROUND(AVG(fm.value), 2) AS AVG_VALUE,
    ROUND(MAX(fm.value), 2) as max_value,
    COUNT(fm.value) AS measurement_count
FROM fact_measurement fm

JOIN dim_sensor ds
    ON fm.sensor_id = ds.sensor_id

JOIN dim_location dl
    ON ds.location_id = dl.location_id

JOIN dim_parameter dp
    ON ds.parameter_id = dp.parameter_id

JOIN dim_date dd
    ON DATE(fm.measured_at) = dd.date

GROUP BY
    dd.date,
    dl.location_id,
    dl.name,
    dl.city,
    dl.latitude,
    dl.longitude,
    dp.name,
    dp.display_name,
    dp.unit;




-- 2. Hourly / Weekday pattern
CREATE OR REPLACE VIEW vw_hourly_pattern AS
SELECT 
    HOUR(
        CONVERT_TZ(
            fm.measured_at,'+00:00','+05:30'
        )
    ) AS hour_of_day,

    DAYOFWEEK(
        CONVERT_TZ(
            fm.measured_at,'+00:00','+05:30'
        )
    ) AS weekday_number,

    DAYNAME(
        CONVERT_TZ(
            fm.measured_at,'+00:00','+05:30'
        )
    ) AS weekday_name,

    dp.name as pollutant,
    dp.display_name,
    dp.unit,

    ROUND(avg(fm.value), 2) AS avg_value,
    COUNT(fm.value) AS measurement_count
FROM fact_measurement fm

JOIN dim_sensor ds
    ON fm.sensor_id = ds.sensor_id

JOIN dim_parameter dp
    ON ds.parameter_id = dp.parameter_id

GROUP BY
    HOUR(CONVERT_TZ(fm.measured_at, '+00:00', '+05:30')),
    DAYOFWEEK(CONVERT_TZ(fm.measured_at, '+00:00', '+05:30')),
    DAYNAME(CONVERT_TZ(fm.measured_at, '+00:00', '+05:30')),
    dp.name,
    dp.display_name,
    dp.unit;




-- 3. PM2.5 Air quality category
CREATE OR REPLACE VIEW vw_pm25_category AS
SELECT
    DATE(fm.measured_at) AS measurement_date,
    dl.location_id,
    dl.name AS location_name,
    dl.city,
    ROUND(avg(fm.value), 2) as avg_pm25,

    CASE
        WHEN avg(fm.value) <= 30 THEN 'Good'
        WHEN avg(fm.value) <= 60 THEN 'Satisfactory'
        WHEN avg(fm.value) <= 90 THEN 'Moderate'
        WHEN avg(fm.value) <= 120 THEN 'Poor'
        WHEN avg(fm.value) <= 250 THEN 'Very Poor'
        ELSE 'Severe'
    END AS air_quality_category
FROM fact_measurement fm
JOIN dim_sensor ds
    ON fm.sensor_id = ds.sensor_id
JOIN dim_location dl
    ON ds.location_id = dl.location_id
JOIN dim_parameter dp
    ON ds.parameter_id = dp.parameter_id

Where dp.name = 'pm25' AND dp.unit = 'µg/m³'

GROUP BY DATE(fm.measured_at),
         dl.location_id,
         dl.name,
         dl.city;




-- 4. Station covergae
CREATE OR REPLACE VIEW vw_station_coverage AS
SELECT
    dl.location_id,
    dl.name AS location_name,
    dl.city,

    dp.name AS pollutant,
    dp.display_name,
    dp.unit,

    COUNT(fm.measured_at) AS actual_measurements,
    COUNT(DISTINCT DATE(fm.measured_at)) AS active_days,

    MIN(fm.measured_at) as first_measurement,
    MAX(fm.measured_at) as last_measurement
FROM fact_measurement fm

JOIN dim_sensor ds
    ON fm.sensor_id = ds.sensor_id
JOIN dim_location dl
    ON ds.location_id = dl.location_id
JOIN dim_parameter dp
    ON ds.parameter_id = dp.parameter_id

GROUP BY
    dl.location_id,
    dl.name,
    dl.city,
    dp.name,
    dp.display_name,
    dp.unit;




-- 5. Quality Issues
CREATE OR REPLACE VIEW vw_data_quality_issues AS
SELECT
    dq.sensor_id,
    dl.location_id,
    dl.name AS location_name,
    dl.city,
    dp.name AS pollutant,
    dp.display_name,
    dp.unit,
    dq.check_type,
    dq.detail,
    dq.flagged_at
FROM data_quality dq
JOIN dim_sensor ds
    ON dq.sensor_id = ds.sensor_id
JOIN dim_location dl
    ON ds.location_id = dl.location_id
JOIN dim_parameter dp
    ON ds.parameter_id = dp.parameter_id;


-- Test the views
SHOW FULL TABLES WHERE table_type='VIEW';

SELECT * FROM vw_daily_air_quality limit 5;

SELECT * FROM vw_hourly_pattern limit 5;

SELECT * FROM vw_pm25_category limit 10;

SELECT * FROM vw_station_coverage limit 20;

SELECT * FROM vw_data_quality_issues limit 20;

