# AI Modelling API Interface

## Table of Contents
1. Overview
2. Folder Structure
3. File Directory & Purpose
4. Architecture & Data Flow
5. Setup & Installation
6. API Endpoints
7. Testing Guide
8. Known Issues & Future Improvements
9. Contributing

## Overview

The **AI Modelling API** is a FastAPI-based REST service that exposes machine learning models for:
- **Misinformation Detection**: Binary classification of social media posts using DeBERTa v3-large
- **Bushfire Fire Prediction**: Spatiotemporal fire-occurrence probability per grid cell using a single ConvLSTM (5-D in, 5-D out), taking **8 input channels — 7 ERA5 weather + `is_burning`**
- **Bushfire Risk Classification (deprecated)**: TCN classifier, retired by the single-ConvLSTM refactor

The API uses a **YAML-driven model registry** to manage checkpoints, scalers, and metadata, enabling easy addition of new models without code changes.

> ### Bushfire forecast contract — read this first
>
> The deployed ConvLSTM takes **8 input channels, not 7**: the 7 ERA5 weather variables plus
> `is_burning`, the observed fire state, last in the channel order. `is_burning` is a **required
> input** sourced from live satellite fire detections — the endpoint cannot be called without it.
>
> | | Value |
> |---|---|
> | Input channels | **8** (`input_channel_order`, order-sensitive) |
> | Input steps | **30** |
> | Horizon | **1** |
> | `grid_shape` | **(142, 200)** |
> | `fire_threshold` | **0.6183173060417175** |
>
> A 7-channel request is rejected. See [Channel order](#bushfire-fire-prediction) for the full
> list, the `is_burning` rules, and the known gap around `grid_row` / `grid_col` derivation.
>
> Earlier revisions of this file documented 7 channels, `input_steps = 60` and
> `fire_threshold = 0.5`. Those figures were stale and should not be used.

**Key Design Principles:**
- Separation of concerns (routers, inference, schemas, config)
- Stateless, pure inference functions (**no database access in this service** — data retrieval is Backend's responsibility)
- GeoJSON-based I/O for spatial data
- Pydantic validation at API boundaries

## Folder Structure

```
api/
├── __init__.py                      # Package marker
├── README.md                        # This file
├── main.py                          # FastAPI app entrypoint + lifespan setup
├── model_loader.py                  # Model registry loader (YAML → checkpoint)
│
├── config/
│   └── models.yaml                  # Model registry (paths, metadata, kinds)
│
├── routers/
│   ├── __init__.py
│   ├── health.py                    # Health & readiness endpoints
│   └── predict.py                   # Inference endpoints (misinformation, bushfire)
│
├── inference/
│   ├── __init__.py
│   ├── misinformation.py            # DeBERTa inference adapter
│   ├── bushfire_forecaster.py       # ConvLSTM forecasting adapter
│   └── bushfire_classifier.py       # TCN classification adapter (deprecated)
│
└── schemas/
    ├── bushfire.py                  # GeoJSON timeseries Pydantic schemas
    └── misinformation.py            # Social post input/output schemas
```

## File Directory & Purpose

| Path | Type | Purpose |
|------|------|---------|
| main.py | Module | FastAPI app, lifespan (model loading at startup) |
| model_loader.py | Module | YAML-driven registry loader, checkpoint resolution |
| `config/models.yaml` | Config | Model registry with checkpoint paths & metadata |
| `routers/health.py` | Module | `GET /health`, `GET /ready` endpoints |
| `routers/predict.py` | Module | `POST /predict/*` endpoints for inference |
| `inference/misinformation.py` | Module | DeBERTa text classification logic |
| `inference/bushfire_forecaster.py` | Module | ConvLSTM time-series forecasting adapter |
| `inference/bushfire_classifier.py` | Module | TCN risk classification & orchestration — **deprecated** by the single-ConvLSTM refactor |
| `schemas/bushfire.py` | Module | Pydantic models for GeoJSON I/O validation |
| `schemas/misinformation.py` | Module | Pydantic models for post input/output |

## Architecture & Data Flow

### System Diagram

[Insert architecture diagram here: FastAPI app → Routers → Inference Adapters → Models]

### Request Flow (Example: Bushfire Forecast)

```
1. Client POST /predict/bushfire/forecast
   ↓
2. FastAPI validates input via ForecastRequest (Pydantic)
   ↓
3. predict.py route handler:
   - Resolves model_id from query param (or uses default)
   - Fetches LoadedModel bundle from _REGISTRY
   - Validates model kind == "bushfire_forecaster"
   ↓
4. bushfire_forecaster.py:predict_bushfire_forecast():
   - Validates GeoJSON structure
   - Extracts observations (timeseries per Feature)
   - Pads/truncates to input_steps (30 for the deployed checkpoint)
   - Builds gridded or batch tensor
   - Applies scaler
   - Runs bundle.model.predict() -> 5-D fire probability grid
   - Postprocesses to GeoJSON FeatureCollection
   ↓
5. FastAPI serializes response to JSON
   ↓
6. Client receives FeatureCollection with fire_probability per cell
```

## API Endpoints

### Health & Status

#### `GET /health`
Liveness probe (always returns 200).

```bash
curl http://localhost:8000/health
```

**Response:**
```json
{"status": "ok"}
```

---

#### `GET /ready`
Readiness probe (checks if models loaded successfully).

```bash
curl http://localhost:8000/ready
```

**Response:**
```json
{
  "ready": true,
  "load_errors": []
}
```

If `ready=false` or `load_errors` is non-empty, models failed to load—check server logs.

---

#### `GET /predict/models`
List all loaded models and their metadata.

```bash
curl http://localhost:8000/predict/models
```

**Response:**
```json
{
  "models": [
    {
      "model_id": "misinfo-deberta",
      "domain": "misinformation",
      "kind": "deberta_sequence_binary",
      "checkpoint": "/path/to/deberta"
    },
    {
      "model_id": "bushfire-forecaster-v1",
      "domain": "bushfire",
      "kind": "bushfire_forecaster",
      "checkpoint": "/path/to/convlstm_forecaster.pth"
    },
    {
      "model_id": "bushfire-classifier-v1",
      "domain": "bushfire",
      "kind": "bushfire_classifier",
      "checkpoint": "/path/to/tcn_classifier.pth"
    }
  ]
}
```

---

### Misinformation Detection

#### `POST /predict/misinformation`
Classify a single social media post for misinformation.

**Request Body:**
```json
{
  "id": "post-1",
  "author_name": "Alice",
  "platform": "twitter",
  "content": "Vaccines contain microchips inserted via 5G networks",
  "share_count": 12,
  "ts": null,
  "post_url": ""
}
```

**Query Parameters:**
- `model_id` (optional): Specific model to use (defaults to first misinformation model)

**Response:**
```json
{
  "model_id": "misinfo-deberta",
  "domain": "misinformation",
  "id": "post-1",
  "author_name": "Alice",
  "platform": "twitter",
  "content": "Vaccines contain microchips...",
  "label_id": 1,
  "label": "misinformation",
  "confidence": 0.92,
  "probabilities": {
    "non_misinformation": 0.08,
    "misinformation": 0.92
  },
  "risk_score": 0.92,
  "severity": "HIGH",
  "checkpoint": "/path/to/deberta"
}
```

**Severity Mapping:**
- `risk_score < 0.6` → `LOW`
- `0.6 ≤ risk_score < 0.75` → `MEDIUM`
- `0.75 ≤ risk_score < 0.9` → `HIGH`
- `risk_score ≥ 0.9` → `CRITICAL`

---

### Bushfire Fire Prediction

#### `POST /predict/bushfire/forecast`
Predict fire-occurrence probability per grid cell for the next timestep (`horizon = 1`).

**Request Body (GeoJSON FeatureCollection):**
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [144.9631, -37.8136]
      },
      "properties": {
        "id": "cell-001",
        "grid_row": 3,
        "grid_col": 7,
        "observations": [
          [20.5, 8.1, 0.0002, 1.4, -0.7, 10240000.0, 21.8, 0.0],
          [21.0, 8.4, 0.0000, 1.2, -0.9, 10510000.0, 22.3, 1.0],
          ...
        ]
      }
    }
  ]
}
```

**Input properties:**

| Property | Required | Description |
|---|---|---|
| `observations` | yes | `[seq_len, n_channels]` array. For the deployed checkpoint: **30 timesteps × 8 channels**. Padded/truncated to the checkpoint's `input_steps`. |
| `id` | no | Cell identifier, echoed in the response and used to join forecaster → classifier output. |
| `timestamps` | no | ISO-8601 timestamps, must be the same length as `observations`. |
| `grid_row`, `grid_col` | no | Position of the cell in the model grid. Must be supplied **together**. Strongly recommended — see *Gridded vs batched input*. |

**Channel order — 8 channels, order-sensitive.** The authoritative list is
`input_channel_order` in the checkpoint's scaler bundle, which the adapter prefers over
`DEFAULT_FEATURE_NAMES`. For the deployed `convlstm_forecaster.pth`:

| # | Channel | Unit | Scaled? |
|---|---|---|---|
| 0 | `era5land_temperature_2m_c` | °C | yes |
| 1 | `era5_dewpoint_temperature_2m_c` | °C | yes |
| 2 | `era5_total_precipitation` | m | yes |
| 3 | `era5_u_component_of_wind_10m` | m/s (eastward) | yes |
| 4 | `era5_v_component_of_wind_10m` | m/s (northward) | yes |
| 5 | `era5land_surface_solar_radiation_downwards` | J/m² | yes |
| 6 | `era5land_skin_temperature_c` | °C | yes |
| 7 | `is_burning` | binary `0.0` / `1.0` | **no** |

Channels 0–6 are ERA5 weather and are standardised by the bundled `StandardScaler`
(`n_features_in_ = 7`). Channel 7 is passed through **unscaled** —
`_apply_scaler()` deliberately scales the weather channels only.

If `feature_names` is supplied in the request it must equal this list exactly, including order.

### Channel 7 — `is_burning`

This is the **observed fire state**, not a prediction, and it is a **required input**. The model
was trained with past fire footprint concatenated onto the weather channels
(`ts_convlstm_forecaster_train.py`: `np.concatenate([train_scaled, train_labels], axis=-1)`,
`input_channels = n_features + 1`), so it answers *"given 30 timesteps of weather **and** where
fire was burning, where will fire be next?"*

Rules for callers:

- Supply `is_burning` for **every one of the 30 historical timesteps**, per cell.
- **Absence of a detection means `0.0`, not missing data.** Most cells at most timesteps have no
  fire; the training label grid was built as `np.zeros(...)` with only detected cells set to
  `1.0`. Do not reject or null-fill a row because no fire was recorded for it.
- Do **not** substitute an all-zero channel when the fire source is unavailable. That is a
  confident assertion that nothing is burning anywhere, and the model will forecast accordingly.
  Fail the request instead.
- Source: live satellite fire detections (NASA FIRMS active hotspots), which are the live
  equivalent of the `satellite_detections_within_fires.csv` training labels. Human-reported
  incident feeds and planned burns are a different distribution and must not be mixed in.

### Deployed checkpoint parameters

Read from `convlstm_scaler.pkl` / `convlstm_forecaster.pth`. Callers should read these from the
`/predict/models` metadata rather than hard-coding them.

| Parameter | Value |
|---|---|
| `input_channel_order` | the 8 channels above |
| `input_steps` | `30` |
| `horizon` | `1` |
| `grid_shape` | `(142, 200)` — (height, width) = (rows, cols) |
| `fire_threshold` | `0.6183173060417175` |

### Grid indexing — `grid_row` / `grid_col`

`grid_row` and `grid_col` are indices into the model's grid, **not** a lat/lon and not a
Data Engineering `location_id`. They are defined by the training data's own axes
(`load_and_format_gridded_data`):

```python
unique_lats = sorted(df['lat'].unique())   # grid_row  — row 0 is southernmost
unique_lons = sorted(df['lon'].unique())   # grid_col  — col 0 is westernmost
```

so `grid_row` counts north from the southern edge and `grid_col` counts east from the western
edge, both zero-indexed, bounded by `grid_shape`.

**Do not derive these indices yourself.** This grid is *not* `location_id` and *not* the
`victoria_grid_5000m` / EPSG:7899 grid from `gridGeneration.py`. Any other definition offsets
every cell.

The bundle ships `grid_shape` but not the axes, so AI Modelling publishes them alongside the
checkpoint:

```text
src/models/bushfire/checkpoints/convlstm_grid_axes.npz
    lats  float64[142]  ascending  -> index is grid_row
    lons  float64[200]  ascending  -> index is grid_col
```

Each value is the **south-west corner** of its cell. To map a coordinate:

```python
axes = np.load("convlstm_grid_axes.npz")
lats, lons = axes["lats"], axes["lons"]

def to_cell(lat, lon):
    """(grid_row, grid_col), or None if outside the grid."""
    row = int(np.searchsorted(lats, lat, side="right")) - 1
    col = int(np.searchsorted(lons, lon, side="right")) - 1
    if not (0 <= row < len(lats) and 0 <= col < len(lons)):
        return None
    return row, col
```

Return `None`, never clamp — a coordinate outside the grid must be dropped.

**Timesteps: 12-hourly buckets at 00:00 and 12:00 UTC**, oldest first, no gaps. This matches the
training convention (`date + daynight * 12h`).

**Gridded vs batched input:** the ConvLSTM is spatiotemporal — it expects
`[batch, seq_len, height, width, n_features]`. When every cell carries `grid_row`/`grid_col`
**and** the checkpoint's scaler bundle declares `grid_shape`, the adapter reassembles the real
grid so neighbouring cells inform each other. Otherwise each cell is processed as a
degenerate 1×1 grid (`[n_samples, seq_len, 1, 1, n_features]`) and spatial context is lost —
functional, but not what the model was trained on. Cells inside `grid_shape` that are not
supplied are filled with the training mean (0 after scaling), matching
`ts_convlstm_forecaster_train.scale_and_fill`.

**Query Parameters:**
- `model_id` (optional): Specific forecaster model

**Response:**
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {...},
      "properties": {
        "id": "cell-001",
        "fire_probability": [0.85],
        "is_burning_predicted": [true],
        "fire_threshold": 0.6183173060417175,
        "risk_score": 0.85,
        "risk_levels": [4],
        "risk_labels": ["HIGH"],
        "forecast": [[0.85]],
        "horizon": 1,
        "n_output_channels": 1,
        "grid_row": 3,
        "grid_col": 7,
        "model_id": "bushfire-convlstm-v1"
      }
    }
  ]
}
```

**Output properties:**

| Property | Description |
|---|---|
| `fire_probability` | Fire-occurrence probability in `[0, 1]`, one entry per horizon step. Primary output. |
| `is_burning_predicted` | `fire_probability > fire_threshold`, one entry per horizon step |
| `fire_threshold` | The threshold used for `is_burning_predicted` |
| `risk_score` | Mean `fire_probability` across the horizon |
| `risk_levels`, `risk_labels` | Discrete level `0..4` and its label, one entry per horizon step |
| `forecast` | `[horizon, n_output_channels]` raw model output — one **row** per horizon step. For the fire-probability model each row is `[p]`. Kept so a multi-channel checkpoint can still be served. |
| `horizon` | Number of predicted timesteps returned (1 for the current model) |
| `n_output_channels` | Values per predicted timestep (1 for the current model) |
| `grid_row`, `grid_col` | Echoed grid position, so a gridded response can be reassembled by the caller |

All per-horizon-step fields (`fire_probability`, `is_burning_predicted`, `risk_levels`,
`risk_labels`, `forecast`) are validated to have the same length.

---

### Integration guide — building a forecast request

For the Backend caller:

1. **Read the parameters, don't hard-code them.** `GET /predict/models` gives
   `input_channel_order`, `input_steps`, `horizon`, `grid_shape`.
2. **Map coordinates** to `(grid_row, grid_col)` with `to_cell()` above. Drop `None`.
3. **Build 30 timesteps**, 12-hourly, oldest first. Skip cells with incomplete history — don't pad.
4. **Channels 0–6: raw ERA5 units, unscaled.** The service applies the bundled scaler itself;
   pre-scaling silently corrupts every input. A missing weather value rejects that cell.
5. **Channel 7: `is_burning`** — `1.0` if a fire detection falls in that cell and bucket, else
   `0.0`. **No detection means `0.0`, not missing.** Never send an all-zero channel as a
   stand-in when the fire source is down — fail the request instead.
6. **One request for all cells.** The ConvLSTM is spatiotemporal; one cell per request collapses
   it to a 1×1 grid and throws away the spatial context. Omitted cells get the training mean.
7. **Pass `risk_factor` straight to Front-end** — it is already 1 = extreme … 5 = very low.

#### Request

Abbreviated in the middle; a real request carries all 30 rows per cell and every cell.

```json
{
  "type": "FeatureCollection",
  "feature_names": [
    "era5land_temperature_2m_c",
    "era5_dewpoint_temperature_2m_c",
    "era5_total_precipitation",
    "era5_u_component_of_wind_10m",
    "era5_v_component_of_wind_10m",
    "era5land_surface_solar_radiation_downwards",
    "era5land_skin_temperature_c",
    "is_burning"
  ],
  "features": [
    {
      "type": "Feature",
      "geometry": { "type": "Point", "coordinates": [148.20, -37.55] },
      "properties": {
        "id": "88_145",
        "grid_row": 88,
        "grid_col": 145,
        "timestamps": ["2026-08-20T00:00:00Z", "2026-08-20T12:00:00Z", "2026-09-03T12:00:00Z"],
        "observations": [
          [13.4, 7.2, 0.00021, 0.8, -0.1,  9840000.0, 13.9, 0.0],
          [21.7, 8.6, 0.00000, 1.9, -1.2, 14300000.0, 24.1, 0.0],
          [23.8, 6.1, 0.00000, 3.4, -2.7, 15100000.0, 27.6, 1.0]
        ]
      }
    },
    {
      "type": "Feature",
      "geometry": { "type": "Point", "coordinates": [142.45, -37.25] },
      "properties": {
        "id": "94_57",
        "grid_row": 94,
        "grid_col": 57,
        "timestamps": ["2026-08-20T00:00:00Z", "2026-09-03T12:00:00Z"],
        "observations": [
          [11.8, 6.9, 0.00112, -0.6, 1.1,  8730000.0, 12.2, 0.0],
          [19.2, 9.8, 0.00004,  1.1, 0.7, 12900000.0, 20.4, 0.0]
        ]
      }
    }
  ]
}
```

- 8 values per row, `is_burning` last. `feature_names` must equal `input_channel_order` exactly.
- Cell `88_145` has fire in its latest bucket (`1.0`); `94_57` has none. Both valid.
- `timestamps` same length as `observations`. `id` is free-form and echoed back.

#### Response

One Feature shown; the rest follow the same shape.

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": { "type": "Point", "coordinates": [148.20, -37.55] },
      "properties": {
        "id": "88_145",
        "fire_probability": [0.91],
        "is_burning_predicted": [true],
        "fire_threshold": 0.6183173060417175,
        "risk_score": 0.91,
        "risk_levels": [4],
        "risk_labels": ["HIGH"],
        "risk_factor": [1],
        "forecast": [[0.91]],
        "horizon": 1,
        "n_output_channels": 1,
        "grid_row": 88,
        "grid_col": 145,
        "model_id": "bushfire-forecaster-v1"
      }
    }
  ]
}
```

#### Errors

| Symptom | Cause | Fix |
|---|---|---|
| `Expected 8 input channels [...], but received observations with 7 columns.` | `is_burning` missing | Add channel 7 to every row |
| `feature_names mismatch: [...] (order-sensitive).` | wrong names or order | Copy `input_channel_order` verbatim |
| Low probabilities everywhere | all-zero `is_burning`, or weather pre-scaled | Check steps 4 and 5 |
| Neighbouring cells ignored | `grid_row`/`grid_col` missing → 1×1 grid | Supply both on every Feature |
| Cells misplaced, no error | row/col derived from `location_id` or another grid | Use the sidecar axes |

---

### Bushfire Risk Classification (deprecated)

> **Deprecated.** The architecture has been reduced from two models (ConvLSTM forecaster →
> TCN classifier) to a single ConvLSTM that predicts fire probability directly. The TCN
> classifier and `POST /predict/bushfire/classify` are being retired — use
> `POST /predict/bushfire/forecast`, which now returns `fire_probability` per cell.

**Risk Level Mapping (from fire probability):**

| Probability | Level | Label |
|---|---|---|
| `p < 0.2` | 0 | `LOW` |
| `0.2 ≤ p < 0.4` | 1 | `MEDIUM_LOW` |
| `0.4 ≤ p < 0.6` | 2 | `MEDIUM` |
| `0.6 ≤ p < 0.8` | 3 | `MEDIUM_HIGH` |
| `p ≥ 0.8` | 4 | `HIGH` |

Thresholds live in one place — `prob_to_risk_level()` in `api/schemas/bushfire.py`.

## Contributing

### Adding a New Model

1. **Place checkpoint** in `src/models/<domain>/checkpoints/`

2. **Add YAML entry** in `api/config/models.yaml`:
   ```yaml
   - id: my-model-v1
     domain: <domain>
     kind: <kind>
     enabled: true
     checkpoint: src/models/<domain>/checkpoints/<file>.pth
     scaler_checkpoint: <path_or_null>
   ```

3. **Create inference adapter** `api/inference/my_domain.py`:
   ```python
   def predict_my_domain(payload: dict, bundle: LoadedModel) -> dict:
       # Validate, preprocess, infer, postprocess
       return result
   ```
5. **Add Pydantic schemas** in `api/schemas/my_domain.py`
6. **Add route** in `api/routers/predict.py`
7. **Test** with example payloads