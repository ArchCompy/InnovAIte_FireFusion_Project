"""
FireFusion Data Engineering Pipeline — El Niño (ENSO) Data Ingestion & Processing
Dataset: NOAA Climate Prediction Center (CPC) Oceanic Niño Index (ONI)
"""

import os
import sys
import logging
from datetime import datetime
import pandas as pd
import urllib.request

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Base directories following repository architecture
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RAW_DATA_DIR = os.path.join(BASE_DIR, "data", "raw")
PROCESSED_DATA_DIR = os.path.join(BASE_DIR, "data", "processed")
DICTIONARY_DIR = os.path.join(BASE_DIR, "data", "data_dictionaries")
DOCS_DIR = os.path.join(BASE_DIR, "data", "docs")
DATASETS_ENSO_DIR = os.path.join(BASE_DIR, "datasets", "enso")

# Official NOAA CPC ONI ASCII Endpoint
NOAA_ONI_URL = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"
DATE_STAMP = datetime.now().strftime("%Y%m%d")


def create_directories():
    """Ensure all team architectural directories exist."""
    for folder in [RAW_DATA_DIR, PROCESSED_DATA_DIR, DICTIONARY_DIR, DOCS_DIR, DATASETS_ENSO_DIR]:
        os.makedirs(folder, exist_ok=True)
        logger.info(f"Directory verified: {folder}")


def fetch_raw_data():
    """
    Stage 2: Extraction — Fetch untouched raw dataset from NOAA CPC and preserve in data/raw/.
    """
    raw_filename = f"noaa_cpc_enso_oni_raw_{DATE_STAMP}.ascii"
    raw_filepath = os.path.join(RAW_DATA_DIR, raw_filename)
    
    logger.info(f"Fetching raw ENSO data from: {NOAA_ONI_URL}")
    urllib.request.urlretrieve(NOAA_ONI_URL, raw_filepath)
    logger.info(f"Raw data successfully preserved in: {raw_filepath}")
    return raw_filepath


def transform_and_standardise(raw_filepath):
    """
    Stage 4: Transformation — Clean and align with FireFusion Star Schema & Time_Registry.
    Saves to data/processed/ and datasets/enso/.
    """
    logger.info(f"Transforming raw data: {raw_filepath}")
    
    # Read space-delimited ASCII file from NOAA raw storage
    df_raw = pd.read_csv(raw_filepath, sep=r'\s+')
    logger.info(f"Raw record count: {len(df_raw)} rows")
    
    # Map season acronym (SEAS) to 2-digit month integer
    seas_to_month = {
        'DJF': 1, 'JFM': 2, 'FMA': 3, 'MAM': 4,
        'AMJ': 5, 'MJJ': 6, 'JJA': 7, 'JAS': 8,
        'ASO': 9, 'SON': 10, 'OND': 11, 'NDJ': 12
    }
    
    df = df_raw.copy()
    df['month'] = df['SEAS'].map(seas_to_month)
    
    # Clean Year-Month column string (e.g. '2019-12')
    df['record_year_month'] = df['YR'].astype(str) + '-' + df['month'].astype(str).str.zfill(2)
    
    # Construct standard month-start datetime ('YYYY-MM-01 00:00:00')
    df['datetime_record'] = pd.to_datetime(df['record_year_month'] + '-01 00:00:00')
    
    # Calculate integer time_id following team Time_Registry standard (YYYYMMDDHH)
    df['time_id'] = df['datetime_record'].dt.strftime('%Y%m0100').astype(int)
    
    # Clean ONI Anomaly value
    df['oni_anomaly'] = pd.to_numeric(df['ANOM'], errors='coerce')
    
    # Derive ENSO Phase categorisation
    def assign_phase(anom):
        if anom >= 0.5:
            return 'El Nino'
        elif anom <= -0.5:
            return 'La Nina'
        else:
            return 'Neutral'
            
    df['enso_phase'] = df['oni_anomaly'].apply(assign_phase)
    
    # Derive 6-month pre-conditioning lag feature (oni_lag6m)
    df['oni_lag6m'] = df['oni_anomaly'].shift(6)
    
    # Data Lineage origin tag 
    df['original_source'] = 'NOAA_CPC_ONI'
    
    # Sort chronologically
    df_sorted = df.sort_values('datetime_record').reset_index(drop=True)
    
    # Generate explicit entity Primary Key enso_id
    df_sorted['enso_id'] = range(1, len(df_sorted) + 1)
    
    # Select final schema-aligned columns with enso_id first
    final_cols = ['enso_id', 'time_id', 'datetime_record', 'record_year_month', 'oni_anomaly', 'enso_phase', 'oni_lag6m', 'original_source']
    df_clean = df_sorted[final_cols]
    
    # 1. Save processed CSV file to data/processed/ 
    processed_filename = f"noaa_cpc_enso_oni_processed_{DATE_STAMP}.csv"
    processed_filepath = os.path.join(PROCESSED_DATA_DIR, processed_filename)
    df_clean.to_csv(processed_filepath, index=False)
    logger.info(f"Processed dataset saved to: {processed_filepath}")
    
    # 2. Save dataset copy to datasets/enso/
    enso_dataset_filename = f"noaa_cpc_enso_oni_{DATE_STAMP}.csv"
    enso_dataset_path = os.path.join(DATASETS_ENSO_DIR, enso_dataset_filename)
    df_clean.to_csv(enso_dataset_path, index=False)
    logger.info(f"Standard dataset copy saved to: {enso_dataset_path}")
    
    return df_clean


def main():
    logger.info("Starting El Niño (ENSO) Data Engineering Pipeline...")
    create_directories()
    raw_path = fetch_raw_data()
    df_clean = transform_and_standardise(raw_path)
    logger.info("EL NIÑO DATA PIPELINE COMPLETED SUCCESSFULLY!")


if __name__ == "__main__":
    main()
