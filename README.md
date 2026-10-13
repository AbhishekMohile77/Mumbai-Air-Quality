# Mumbai Metropolitan Region Air Quality Analytics

An end-to-end air-quality analytics project that ingests monitoring data from the OpenAQ API, 
stores and validates measurements in a MySQL data warehouse, and presents trends and data-quality insights through Power BI.

## Project Overview

This project analyses air-quality measurements across the Mumbai Metropolitan Region (MMR), including Mumbai, Thane, Navi Mumbai and surrounding areas.

It demonstrates an end-to-end analytics workflow covering API ingestion, Python-based data processing, 
relational data modelling, SQL transformations, data-quality checks, containerised execution and interactive reporting.

## Business Objectives
- Analyse pollutant concentrations across monitoring locations.
- Explore daily air-quality trends and hourly and weekday patterns.
- Compare monitoring stations and their measurement volumes.
- Present findings through an interactive Power BI dashboard.

## Architecture
OpenAQ API → Python ETL → MySQL Data Warehouse → SQL Views → Power BI

## Technology Stack
- Data source: OpenAQ API v3
- Programming: Python
- Data processing: Pandas, SQLAlchemy, Requests
- Database: MySQL
- Visualisation: Power BI
- Containerisation: Docker, Docker Compose
- Version control: Git and GitHub

## Data Model
- The warehouse uses a dimensional model consisting of:
- dim_location — monitoring locations and geographic information
- dim_parameter — pollutant names and measurement units
- dim_sensor — sensors associated with locations and parameters
- dim_date — calendar attributes
- fact_measurement — timestamped pollutant measurements
- data_quality — detected data-quality issues
- SQL views provide reporting-ready datasets for Power BI.

## Data Pipeline
1. Retrieve monitoring locations, parameters and sensors from OpenAQ
2. Populate and update dimension tables
3. Fetch hourly measurements through the OpenAQ API
4. Transform timestamps and measurement records
5. Upsert measurements using the sensor and timestamp key
6. Support incremental ingestion and configurable historical backfills
7. Run data-quality checks and store detected issues
8. Refresh the Power BI dashboard from the reporting views

## Power BI Dashboard
The dashboard contains four pages:
1. Air Quality Overview — KPI summaries, daily trends and pollutant comparisons.
2. Station Map & Hotspots — geographic station distribution and station rankings.
3. Pollution Patterns — weekday and hourly measurement patterns.
4. Data Quality & Coverage — measurement volumes, PM2.5 category distribution and detected issues.

## Docker Setup
The Python application is packaged in a Docker image, with Docker Compose providing named jobs for the dimension loader, measurement loader and quality checks.
MySQL currently runs on the Windows host, while the Python jobs run inside Docker containers.
