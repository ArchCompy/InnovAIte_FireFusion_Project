import os
import json
import numpy as np
import pandas as pd
import psycopg2
from dotenv import load_dotenv
from sklearn.neighbors import BallTree


load_dotenv()


FACILITY_JSON_FILE = "facilities_at_risk_register_geocoded.json"

OUTPUT_JSON_FILE = "facilities_fire_risk_with_location_id.json"
OUTPUT_CSV_FILE = "facilities_fire_risk_with_location_id.csv"

EARTH_RADIUS_M = 6371000

LOCATION_ID_MIN = 1
LOCATION_ID_MAX = 463807


def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )


def load_facilities(path):
    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)

    if isinstance(data, dict):
        data = [data]

    return pd.DataFrame(data)


def load_location_registry(conn):
    query = """
        SELECT
            location_id,
            grid_latitude,
            grid_longitude
        FROM public.location_registry
        WHERE location_id BETWEEN %s AND %s
        ORDER BY location_id
    """

    return pd.read_sql_query(
        query,
        conn,
        params=(LOCATION_ID_MIN, LOCATION_ID_MAX)
    )


def save_facilities_json(df, path):
    records = df.replace({np.nan: None}).to_dict(orient="records")

    with open(path, "w", encoding="utf-8") as file:
        json.dump(records, file, indent=4, ensure_ascii=False)


def match_to_nearest_grid(facilities_df, location_df):

    facilities_df["latitude"] = pd.to_numeric(
        facilities_df["latitude"],
        errors="coerce"
    )

    facilities_df["longitude"] = pd.to_numeric(
        facilities_df["longitude"],
        errors="coerce"
    )

    location_df["grid_latitude"] = pd.to_numeric(
        location_df["grid_latitude"],
        errors="coerce"
    )

    location_df["grid_longitude"] = pd.to_numeric(
        location_df["grid_longitude"],
        errors="coerce"
    )

    location_df = location_df.dropna(
        subset=["grid_latitude", "grid_longitude"]
    ).copy()

    if location_df.empty:
        raise RuntimeError(
            "No valid rows were found in public.location_registry."
        )

    grid_coordinates_rad = np.radians(
        location_df[
            ["grid_latitude", "grid_longitude"]
        ].to_numpy()
    )

    tree = BallTree(
        grid_coordinates_rad,
        metric="haversine"
    )

    facilities_df["location_id"] = None
    facilities_df["matched_grid_latitude"] = None
    facilities_df["matched_grid_longitude"] = None
    facilities_df["distance_to_grid_m"] = None
    facilities_df["grid_match_status"] = "no_facility_lat_lon"

    valid_facilities_mask = (
        facilities_df["latitude"].notna()
        & facilities_df["longitude"].notna()
    )

    valid_facilities = facilities_df.loc[
        valid_facilities_mask,
        ["latitude", "longitude"]
    ]

    if valid_facilities.empty:
        print("No facilities with latitude/longitude found.")
        return facilities_df

    facility_coordinates_rad = np.radians(
        valid_facilities.to_numpy()
    )

    distances_rad, indices = tree.query(
        facility_coordinates_rad,
        k=1
    )

    distances_m = (
        distances_rad.flatten()
        * EARTH_RADIUS_M
    )

    nearest_indices = indices.flatten()

    matched_location_rows = (
        location_df
        .iloc[nearest_indices]
        .reset_index(drop=True)
    )

    valid_index = facilities_df.loc[
        valid_facilities_mask
    ].index

    facilities_df.loc[
        valid_index,
        "location_id"
    ] = matched_location_rows[
        "location_id"
    ].to_numpy()

    facilities_df.loc[
        valid_index,
        "matched_grid_latitude"
    ] = matched_location_rows[
        "grid_latitude"
    ].to_numpy()

    facilities_df.loc[
        valid_index,
        "matched_grid_longitude"
    ] = matched_location_rows[
        "grid_longitude"
    ].to_numpy()

    facilities_df.loc[
        valid_index,
        "distance_to_grid_m"
    ] = distances_m.round(2)

    facilities_df.loc[
        valid_index,
        "grid_match_status"
    ] = np.where(
        distances_m <= 1000,
        "matched",
        "matched_far_check_needed"
    )

    return facilities_df


def main():

    conn = None

    try:
        print("Loading geocoded facility data...")

        facilities_df = load_facilities(
            FACILITY_JSON_FILE
        )

        print(
            f"Facilities loaded: {len(facilities_df)}"
        )

        print("Connecting to Supabase/PostgreSQL...")

        conn = get_db_connection()

        print(
            "Loading public.location_registry..."
        )

        location_df = load_location_registry(
            conn
        )

        print(
            f"Grid locations loaded: {len(location_df)}"
        )

        print(
            "Matching facilities to nearest location_id..."
        )

        result_df = match_to_nearest_grid(
            facilities_df,
            location_df
        )

        save_facilities_json(
            result_df,
            OUTPUT_JSON_FILE
        )

        result_df.to_csv(
            OUTPUT_CSV_FILE,
            index=False
        )

        print(
            "Finished matching facilities to location registry."
        )

        print(
            f"Output JSON: {OUTPUT_JSON_FILE}"
        )

        print(
            f"Output CSV: {OUTPUT_CSV_FILE}"
        )

        print()
        print("Match status summary:")

        print(
            result_df[
                "grid_match_status"
            ].value_counts(
                dropna=False
            )
        )

    except Exception as error:
        print(f"Pipeline failed: {error}")
        raise

    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    main()