# NOAA CPC Oceanic Niño Index (ONI) El Niño Data Pipeline

Contributor: **FireFusion Data Engineering Stream**

## Pipeline Name

El Niño-Southern Oscillation (ENSO) NOAA CPC ONI Data Pipeline

## Pipeline Script

```text
fetch_enso.py
```

## Purpose

This pipeline extracts monthly Sea Surface Temperature (SST) anomaly indices (Oceanic Niño Index / ONI) from the NOAA Climate Prediction Center (CPC) public endpoint.

The output supports the FireFusion project by providing macro-climate teleconnection features (`oni_anomaly`, `oni_lag6m`, `enso_phase`) to pre-condition fuel dryness and long-term bushfire risk predictions in Victoria.

---

## Source Information

* Source: NOAA Climate Prediction Center (CPC)
* Provider: NOAA Physical Sciences Laboratory
* API / Dataset URL: `https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt`
* Collection method: HTTP GET request using Python `urllib.request`
* Data format from source: Space-delimited ASCII text
* Output format: CSV
* Refresh frequency: Monthly
* Pipeline owner: Data Engineering stream

---

## Input Data

The script fetches data directly from the official NOAA CPC endpoint:

```text
https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt
```

Raw data is preserved unchanged in `data/raw/noaa_cpc_enso_oni_raw_<YYYYMMDD>.ascii` for audit lineage.

---

## Variables & Output Schema

| Column Name | Description | Type | Unit/Range | Null Allowed | Notes |
|-------------|-------------|------|------------|--------------|-------|
| `enso_id` | Primary Key | `INTEGER` | `1` to `N` | No | Entity primary key following team rule |
| `time_id` | Universal Master Calendar Key | `INTEGER` | `YYYYMMDDHH` | No | Foreign key linking to `Time_Registry` |
| `datetime_record` | Standard month-start timestamp | `TIMESTAMP` | `YYYY-MM-01 00:00:00` | No | Month-start alignment |
| `record_year_month` | Year-Month string | `VARCHAR` | `YYYY-MM` | No | e.g. `'2019-12'` |
| `oni_anomaly` | Oceanic Niño Index anomaly | `NUMERIC` | `-3.0` to `+3.0 °C` | No | Sea Surface Temp deviation |
| `enso_phase` | Active ENSO Phase | `VARCHAR` | `'El Nino'`, `'La Nina'`, `'Neutral'` | No | Derived categorical state |
| `oni_lag6m` | 6-Month Prior ONI Anomaly | `NUMERIC` | `-3.0` to `+3.0 °C` | Yes (first 6 rows) | Derived fuel drying pre-conditioning lag |
| `original_source` | Data Lineage Origin | `VARCHAR` | `'NOAA_CPC_ONI'` | No | Standard lineage tracking |

---

## Data Processing Steps

1. **Extraction**: Fetch raw space-delimited ASCII data from NOAA CPC API and store in `data/raw/`.
2. **Date Alignment**: Convert `SEAS` acronyms (`DJF`, `NDJ`, etc.) to standard 2-digit months and construct `datetime_record` (`YYYY-MM-01 00:00:00`).
3. **Master Time Key**: Generate integer `time_id` (`YYYYMM0100`) aligned with the central `Time_Registry` architecture.
4. **Feature Engineering**: Compute `oni_lag6m` (6-month lag) and derive categorical `enso_phase` (`El Nino` if ONI >= +0.5°C).
5. **Primary Key Assignment**: Add sequential `enso_id` (1, 2, 3, ...) as the first column.
6. **Output Delivery**: Save processed CSV files to `data/processed/noaa_cpc_enso_oni_processed_<YYYYMMDD>.csv` and `datasets/enso/noaa_cpc_enso_oni_<YYYYMMDD>.csv`.

---

## Output Data

* **Raw Storage**: `data-engineering/data/raw/noaa_cpc_enso_oni_raw_<YYYYMMDD>.ascii`
* **Processed Target**: `data-engineering/data/processed/noaa_cpc_enso_oni_processed_<YYYYMMDD>.csv`
* **Dataset Target**: `data-engineering/datasets/enso/noaa_cpc_enso_oni_<YYYYMMDD>.csv`
