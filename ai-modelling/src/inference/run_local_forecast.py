# src/inference/run_local_forecast.py
import json
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from api.schemas.bushfire import DEFAULT_FEATURE_NAMES
from api.model_loader import load_models, get_model
from api.inference.bushfire_forecaster import predict_bushfire_forecast

DATA_PATH = "src/data/bushfire/forecaster_test_data.csv"
GRID_CACHE_PATH = "src/data/bushfire/data_grid_cache.npy"
LABEL_CACHE_PATH = "src/data/bushfire/label_grid_cache.npy"
COORDS_CACHE_PATH = "src/data/bushfire/grid_coords_cache.npz"
TIMESTAMPS_CACHE_PATH = "src/data/bushfire/grid_timestamps_cache.npy"
OUTPUT_DIR = "src/data/bushfire/forecasts"
CELL_SIZE_DEG = 0.05

MODEL_ID = "bushfire-forecaster-v1"


def get_or_build_coords():
    if os.path.exists(COORDS_CACHE_PATH):
        cached = np.load(COORDS_CACHE_PATH)
        return cached["lats"], cached["lons"]

    print("No coords cache found — extracting lat/lon from CSV (one-time cost)...")
    df = pd.read_csv(DATA_PATH, usecols=[".geo"])

    def extract_coords(geojson_str):
        geojson = json.loads(geojson_str)
        lons, lats = [], []
        for ring in geojson["coordinates"]:
            for point in ring:
                lons.append(float(point[0]))
                lats.append(float(point[1]))
        return min(lons), min(lats)

    lons, lats = [], []
    for s in df[".geo"]:
        try:
            lon, lat = extract_coords(s)
            lons.append(lon)
            lats.append(lat)
        except Exception:
            continue

    unique_lats = np.array(sorted(set(lats)))
    unique_lons = np.array(sorted(set(lons)))
    np.savez(COORDS_CACHE_PATH, lats=unique_lats, lons=unique_lons)
    print(f"Saved coords cache: {len(unique_lats)} lats x {len(unique_lons)} lons")
    return unique_lats, unique_lons

def get_or_build_timestamps():
    if os.path.exists(TIMESTAMPS_CACHE_PATH):
        cached = np.load(TIMESTAMPS_CACHE_PATH)
        return [datetime.fromtimestamp(t, tz=timezone.utc) for t in cached]

    print("No timestamps cache found; extracting datetime from CSV (one-time cost)...")
    df = pd.read_csv(DATA_PATH, usecols=["datetime"])

    parsed = pd.to_datetime(df["datetime"], utc=True, format="mixed")
    unique_sorted = sorted(parsed.unique())

    epoch_seconds = np.array([t.timestamp() for t in unique_sorted])
    np.save(TIMESTAMPS_CACHE_PATH, epoch_seconds)
    print(f"Saved timestamps cache: {len(unique_sorted)} timesteps")

    return [t.to_pydatetime() for t in unique_sorted]

def cell_polygon(lat, lon, size=CELL_SIZE_DEG):
    half = size / 2
    return {
        "type": "Polygon",
        "coordinates": [[
            [lon - half, lat - half],
            [lon + half, lat - half],
            [lon + half, lat + half],
            [lon - half, lat + half],
            [lon - half, lat - half],
        ]],
    }


def build_request(data_grid, label_grid, unique_lats, unique_lons, valid_mask, input_steps, timestamps, feature_names):
    """
    Build a GeoJSON forecast request whose per-cell observations carry both
    weather features and is_burning history, concatenated in the same
    order the model was trained on: FEATURES + ["is_burning"].
    """
    recent_weather = data_grid[-input_steps:] # [input_steps, H, W, n_weather]
    recent_fire = label_grid[-input_steps:] # [input_steps, H, W, 1]
    recent_timestamps = [t.isoformat() for t in timestamps[-input_steps:]]
    height, width = recent_weather.shape[1], recent_weather.shape[2]

    features = []
    for row in range(height):
        for col in range(width):
            if not valid_mask[row, col]:
                continue
            weather_obs = recent_weather[:, row, col, :] # [input_steps, n_weather], may have NaN
            fire_obs = recent_fire[:, row, col, :] # [input_steps, 1], no NaN (built from zeros)

            obs = np.concatenate([weather_obs, fire_obs], axis=-1).tolist()

            features.append({
                "type": "Feature",
                "geometry": cell_polygon(unique_lats[row], unique_lons[col]),
                "properties": {
                    "id": f"cell_{row}_{col}",
                    "observations": obs,
                    "timestamps": recent_timestamps,
                    "grid_row": row,
                    "grid_col": col,
                },
            })

    return {"type": "FeatureCollection", "features": features, "feature_names": feature_names}


def main():
    load_models()
    bundle = get_model(MODEL_ID)

    data_grid = np.load(GRID_CACHE_PATH) # [T, H, W, n_weather], raw/unscaled
    label_grid = np.load(LABEL_CACHE_PATH) # [T, H, W, 1], binary is_burning

    assert data_grid.shape[:3] == label_grid.shape[:3], (
        f"Grid mismatch: weather {data_grid.shape} vs labels {label_grid.shape}"
    )

    valid_mask = ~np.all(np.isnan(data_grid), axis=(0, -1))
    unique_lats, unique_lons = get_or_build_coords()
    timestamps = get_or_build_timestamps()

    input_steps = bundle.metadata.get("input_steps", 60)
    feature_names = bundle.metadata.get("input_channel_order") \
        or bundle.metadata.get("weather_features", DEFAULT_FEATURE_NAMES)
 
    request_geojson = build_request(
        data_grid, label_grid, unique_lats, unique_lons, valid_mask,
        input_steps, timestamps, feature_names,
    )
    print(f"Built request with {len(request_geojson['features'])} cells")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    request_path = os.path.join(OUTPUT_DIR, f"request_{ts}.geojson")
    with open(request_path, "w") as f:
        json.dump(request_geojson, f, indent=2)
    print(f"Saved request to {request_path}")

    result = predict_bushfire_forecast(request_geojson, bundle)

    out_path = os.path.join(OUTPUT_DIR, f"forecast_{ts}.geojson")
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)

    print(f"Saved forecast to {out_path}")


if __name__ == "__main__":
    main()