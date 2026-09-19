# Live Fire Event Integration — the `is_burning` Input Channel

**Status:** Plan — ready for implementation
**Owner:** AI Modelling — hand to Back-end once the grid axes artifact (§5) is published
**Contract detail:** `ai-modelling/api/README.md` is authoritative (channel table, JSON examples, rules)
**Complements:** `backend/docs/fire-risk-map-backend-integration.md`

---

## 1. The finding

The deployed ConvLSTM takes **8 input channels, not 7**: the 7 ERA5 weather variables plus
`is_burning` (observed fire state) last. Data Engineering's live fire event pipeline is its only
source.

- **Required, not optional.** A 7-channel request is rejected; the endpoint cannot be called
  without fire data.
- **No retrain.** The checkpoint was already trained this way.
- Backend's current 7-feature contract will be rejected as-is (§3).

**Evidence:**

| Source | Proof |
|---|---|
| `convlstm_forecaster.pth` | `ForecasterConfig(input_channels=8, ...)`; `convlstm1.conv.weight` is `(128, 40, 3, 3)` where `40 = 8 + hidden_size_1(32)` |
| `convlstm_scaler.pkl` | `input_channel_order` = 7 ERA5 + `is_burning`; `fire_input_channels: ['is_burning']`; scaler `n_features_in_ = 7` (weather only) |
| `ts_convlstm_forecaster_train.py` | `np.concatenate([train_scaled, train_labels], axis=-1)`; `input_channels = n_features + 1` |
| `api/inference/bushfire_forecaster.py` | Prefers `input_channel_order` over `DEFAULT_FEATURE_NAMES`; `_apply_scaler(..., n_weather)` scales the first 7 only |

The model answers *"given 30 timesteps of weather **and** where fire was burning, where will fire
be next?"* Past fire state is an input; future fire state is the target.

---

## 2. Source data

Two DE pipelines already run. Both stay read-only and unmodified.

| Source | Table | Use |
|---|---|---|
| NASA FIRMS active hotspots | `Fire_Incident_Record` where `record_type = 'ACTIVE'`, joined to `Location_Registry` / `Time_Registry` | **Feeds `is_burning`** |
| Vic Emergency realtime | `public.vic_emercency_bushfire_incident_realtime` (the `emercency` typo is the real name) | Not a model input |

`is_burning` comes from FIRMS only. The model was trained on satellite detections
(`satellite_detections_within_fires.csv`), and FIRMS is the live equivalent. Vic Emergency is
human-reported incidents including planned burns — a different distribution.

Use `original_latitude` / `original_longitude`, which FIRMS preserves un-snapped.

---

## 3. Backend's contract is short by one channel

`backend/firefusion-api/app/internal/models/ai_contract.py` declares 7 features, so
`AIRequestBuilder` emits 30 × 7 observations and AI rejects the request.
`AI_INPUT_STEPS = 30` is already correct.

### The one substantive logic change: absence means zero

`ai_request_builder.py` rejects any null value:

```python
if value is None:
    raise ValueError(f"Missing DE value '{de_field}' for AI feature '{ai_feature}'")
```

Correct for the 7 weather channels — a null temperature is genuinely unknown. **Wrong for
`is_burning`**, where "no detection in this cell at this timestep" is a real observed value of
`0.0`, not missing data. Almost every cell at almost every timestep is `0.0`; the training label
grid was built as `np.zeros(...)` with only detected cells set to `1.0`. Applying the null rule
would reject essentially every request.

So: keep the strict rule for the 7 weather channels, resolve `is_burning` with a `0.0` default,
and make the distinction explicit in code.

Never send an all-zero channel as a stand-in when the fire source is down — that asserts nothing
is burning anywhere, and the model forecasts accordingly. Fail the run instead.

---

## 4. Time alignment

**12-hourly buckets at 00:00 and 12:00 UTC**, 30 steps, oldest first, no gaps. This is the
training convention (`date + daynight * 12h`, matched to the weather axis by exact timestamp).
`Time_Registry.datetime_record` is the join key on the DE side.

A shifted bucket is silent: it feeds the model a plausible but wrong fire history.

---

## 5. Grid identity

`grid_row` / `grid_col` are indices into the model's grid — **not** `location_id`, and **not** the
`victoria_grid_5000m` / EPSG:7899 grid from `gridGeneration.py`. The grid is data-derived:
`load_and_format_gridded_data()` builds it from `sorted(unique_lats)` / `sorted(unique_lons)` of
the training weather CSV. Row 0 is southernmost, col 0 westernmost, `grid_shape = (142, 200)`.

The bundle ships `grid_shape` but not the axes, so AI Modelling publishes them alongside the
checkpoint:

```text
ai-modelling/src/models/bushfire/checkpoints/convlstm_grid_axes.npz
    lats  float64[142]  ascending  -> grid_row
    lons  float64[200]  ascending  -> grid_col
```

Mapping code is in `ai-modelling/api/README.md` under *Grid indexing*.

**Why `location_id` is not a shortcut.** `Location_Registry` has no `grid_row` / `grid_col` —
they are absent from `firms_active_fire/schema.sql`, and a search for `grid_row` across
`data-engineering/` returns nothing. `FIRE_RISK_SOURCE_SQL` nevertheless selects them, so that
query cannot succeed as written. This is a **schema** gap, not the population gap recorded in
`backend/docs/fire-risk-map-backend-integration.md`. DE's own snapping is also inconsistent
(`0.05°` in `firms_active_fire` vs `0.1°` in the Grid Snapper README), so `location_id` is not a
safe proxy either way.

**Debt:** the axes belong inside the scaler bundle next to `grid_shape` so the grid definition
travels with the model. The sidecar can drift out of sync with a future checkpoint, and a wrong
origin does not error — it offsets every detection by a constant and still returns plausible
numbers.

---

## 6. Integration points — where the gap is

Places in existing code the contract touches. Verified against current files; the design of any
new code is left to whoever implements it.

| | File | Gap |
|---|---|---|
| a | `backend/firefusion-api/.../models/ai_contract.py` | `AI_FEATURE_NAMES` and `DE_TO_AI_FEATURE_MAPPING` have 7 entries; need 8 with `is_burning` last |
| b | `backend/firefusion-api/.../services/ai_request_builder.py` | Emits 7-wide rows; the `value is None` check blocks `is_burning` (§3). `_build_grid_polygon()` assumes a 0.05° cell — check against the published axes |
| c | `backend/aggregator-api/.../repositories/aggregator_repository.py` | `FIRE_RISK_SOURCE_SQL` reads `weather_observation` only — no fire source. Also selects `lr.grid_row, lr.grid_col`, which don't exist. `RECENT_FIRE_INCIDENTS_V2_SQL` does read fire, but per-incident, not per-cell-per-timestep |
| d | `backend/aggregator-api/.../models/fire_risk_source.py` | `FireRiskSourceRecord` has no fire-state field |
| e | `backend/aggregator-api/.../routers/fire_data.py` | Both routes exist; one is per-incident, the other weather-only |
| f | `backend/firefusion-api/.../clients/aggregator_client.py` | `get_recent_fire_incidents()` is implemented but nothing calls it |
| g | `backend/firefusion-api/.../services/forecast_integration_service.py` | Calls only `get_fire_risk_inputs()`; fire never enters the flow |
| h | `convlstm_grid_axes.npz` | **Does not exist yet.** AI Modelling side; blocks everything downstream |
| i | `ai-modelling/api/inference/bushfire_forecaster.py` | **Not a gap** — already correct. Add no DB access; the service is stateless by design |

Response contract is unchanged. `risk_factor` stays as it is and Front-end is unaffected.

---

## 7. Verification

The grid and time mappings can both be wrong without raising an error.

1. **Label replay — the strongest check.** Run the mapping and time bucketing over
   `satellite_detections_within_fires.csv`, which already carries `cell_x` / `cell_y`, and assert
   the derived `(grid_row, grid_col)` equals the stored `(cell_y, cell_x)`. Validates origin,
   orientation and time convention against the exact data the model was trained on.
2. **Axes round-trip** — map the training weather CSV's own cell coordinates and assert they
   return their own indices. Include all four corners and one out-of-grid coordinate expecting
   `None`.
3. **Channel order** — request `feature_names` equals `input_channel_order` exactly, 8 floats
   per row.
4. **Zero-default** — a cell with no detections yields `is_burning = 0.0` for all 30 steps and is
   accepted; a null *weather* value still rejects the cell.
5. **Positive rate** — log the fraction of `is_burning == 1.0` and compare against the training
   positive rate. All-zero, or implausibly high, means a mapping or bucketing fault.
6. **End-to-end** — the built request is accepted without a channel-count or `feature_names`
   error.

Steps 1–2 need `forecaster_test_data.csv` and `satellite_detections_within_fires.csv`, both
gitignored as large data.

---

## 8. Summary

The deployed ConvLSTM requires an eighth input channel, `is_burning`, sourced from DE's live
FIRMS pipeline. The AI service already implements this correctly; Backend's 7-feature contract
does not. No retrain, no checkpoint change, no DE pipeline change — §6 lists every place the
contract touches.

One prerequisite remains: publishing `convlstm_grid_axes.npz` (§5, §6h). Until it exists nothing
downstream can map a coordinate to a cell.
