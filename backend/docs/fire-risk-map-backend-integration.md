# Fire Risk Map Backend Integration - PR #218

**Status:** Sprint 1 integration - Ready for Review  
**Owner:** Timothy Trevett  
**Reviewer:** Whole Backend Team  
**Streams affected:** Back-end, Front-end, AI Modelling, Data Engineering  
**Purpose:** Connect the existing Fire Risk Map API path to the newer Data Engineering and AI Modelling services without replacing the existing Frontend-facing contract.

---

## 1. Integration goal

The Backend integration is being prepared around the following flow:

```text
Data Engineering
    ↓
Aggregator API
    ↓
FireFusion API
    ↓
AI Modelling
    ↓
FireFusion API
    ↓
GET /api/bushfire-forecast
    ↓
Frontend Fire Risk Map
```

The aim is to keep the existing Frontend boundary stable while allowing Backend to retrieve prepared source data, build the AI request, call the AI forecast API, and return the resulting risk polygons to the map.

This work is intended to complement the separate Fire Risk Map Backend → Frontend API contract work rather than replace it.

---

## 2. Confirmed cross-stream contract

### Frontend

Frontend has confirmed that, for Sprint 1:

- the Fire Risk Map expects a GeoJSON `FeatureCollection` containing Polygon features;
- `properties.risk_factor` is sufficient for the map;
- the risk convention is `1 = extreme` through to `5 = very low`;
- `GET /api/bushfire-forecast` is the required working path;
- `/api/ws` can remain optional for Sprint 1.

### AI Modelling

AI Modelling has confirmed that:

- Backend calls `POST /predict/bushfire/forecast`;
- the response is a GeoJSON `FeatureCollection` containing prediction polygons;
- `risk_factor` is already converted to the Frontend convention, so Backend must not convert it again;
- forecast timestamps are included in the current response;
- the current known-working request contains 30 historical timesteps per grid cell;
- the request contains `feature_names`, and AI validates the supplied feature names/order during inference;
- the seven feature names listed below are the current source of truth for Backend integration;
- the overall request structure is expected to remain stable, although additional input features may be added later, including live fire-event data from Data Engineering.

Current AI input feature names are:

```text
era5land_temperature_2m_c
era5_dewpoint_temperature_2m_c
era5_total_precipitation
era5_u_component_of_wind_10m
era5_v_component_of_wind_10m
era5land_surface_solar_radiation_downwards
era5land_skin_temperature_c
```

---

## 3. Backend files added or changed

### `firefusion-api/app/internal/clients/aggregator_client.py`

Introduces a REST client for communication from `firefusion-api` to `aggregator-api`.

Current responsibilities:

- use the configured Aggregator service URL;
- request recent Data Engineering fire incident records where required;
- request Fire Risk Map source records through the dedicated internal data route;
- keep inter-service HTTP logic out of ForecastService and API routes;
- raise HTTP errors instead of passing failed responses further into the integration pipeline.

Current internal routes include:

```text
GET /internal/data/fire-incidents
GET /internal/data/fire-risk-inputs
```

---

### `firefusion-api/app/internal/clients/ai_modelling_client.py`

Introduces the REST boundary between Backend and the AI Modelling FastAPI service.

Current responsibilities:

- call `POST /predict/bushfire/forecast`;
- return the AI GeoJSON response to Backend;
- expose a `/health` check for AI service connectivity;
- keep the AI service URL configurable rather than hard-coded into business logic.

The current AI response includes fields such as `risk_factor`, `fire_probability`, `is_burning_predicted`, `forecast_timestamps`, `grid_row` and `grid_col`.

Backend should preserve AI's `risk_factor` value without applying a second risk conversion.

---

### `firefusion-api/app/internal/models/ai_forecast.py`

Defines the Backend representation of the AI forecast request.

The request is a GeoJSON `FeatureCollection`, where each grid cell contains:

- Polygon geometry;
- ordered historical observations;
- timestamps;
- `grid_row`;
- `grid_col`.

The current AI request uses 30 historical timesteps. The number of feature values should remain tied to the supplied `feature_names` rather than being permanently fixed, because AI Modelling may add additional model inputs later.

---

### `firefusion-api/app/internal/services/ai_request_builder.py`

Provides the transformation boundary between Data Engineering records and the AI Modelling request.

Its intended responsibilities are:

1. group source records by location/grid cell;
2. order records chronologically;
3. select the required 30 historical timesteps;
4. map Data Engineering fields into the exact AI `feature_names` order;
5. build the observation arrays and timestamps;
6. attach the correct geometry and grid identifiers;
7. return the final AI GeoJSON request.

Data Engineering has now confirmed the intended field and join structure for this component:

all seven current AI feature columns exist directly on public.weather_observation;

weather_observation.location_id joins to location_registry.location_id;

location_registry provides grid_latitude, grid_longitude, grid_row and grid_col;

weather_observation.time_id joins to time_registry.time_id;

time_registry.datetime_record is the intended chronological timestamp.

The remaining blocker is data population rather than mapping uncertainty. The seven ERA5 fields are currently null, existing weather rows have null time_id, and grid_row / grid_col are currently unpopulated.

Missing or unknown values should therefore fail clearly rather than being invented or silently substituted.

---

### `firefusion-api/app/internal/services/forecast_normaliser.py`

Provides the AI response → Frontend contract transformation.

For Sprint 1 the normalisation can remain intentionally small:

- validate that the AI response is a GeoJSON `FeatureCollection`;
- retain the Polygon geometry returned by AI;
- read the current forecast horizon value from `risk_factor`;
- validate that the value is within `1..5`;
- expose that same value to Frontend without converting the scale.

Frontend has confirmed that `risk_factor` alone is sufficient for the current Fire Risk Map integration, even though AI may return additional prediction metadata.

---

### `firefusion-api/app/internal/services/forecast_integration_service.py`

Coordinates the wider cross-stream Fire Risk Map flow:

```text
AggregatorClient
    ↓
AIRequestBuilder
    ↓
AIModellingClient
    ↓
ForecastNormaliser
    ↓
ForecastService
```

The intended final behaviour is for the normalised AI prediction to enter the same Backend prediction-storage path used by the existing prediction flow.

A shared `store_prediction()` path is being coordinated with the separate Fire Risk Map API contract work so the existing RabbitMQ flow and the newer AI REST flow can eventually use the same validation, Redis caching and WebSocket broadcasting logic.

Final integration of `forecast_service.py` is being coordinated separately because that file overlaps with PR #214.

---

### `aggregator-api/app/internal/models/fire_incident_v2.py`

Adds a model for the newer Data Engineering fire incident structure while retaining the existing legacy `FireEvent` model.

The new model includes:

- Data Engineering identifiers (`incident_id`, `location_id`, `time_id`);
- original coordinates;
- NASA FIRMS metadata where available;
- raw measurements such as brightness and FRP;
- joined location information;
- joined timestamp/season information.

Keeping this separate allows the newer DE schema to be introduced without immediately removing the inherited `fire_events_full` pathway.

---

### `aggregator-api/app/internal/models/fire_risk_source.py`

Defines one Data Engineering source observation returned by the Aggregator for the Fire Risk Map integration.

The model includes:

- `location_id`;
- `time_id`;
- `datetime_record`;
- `grid_latitude`;
- `grid_longitude`;
- `grid_row`;
- `grid_col`;
- `region_name`;
- the seven confirmed ERA5 model-input fields.

The ERA5 values and grid indices remain nullable at the Aggregator boundary because the current Data Engineering dataset is not yet fully populated.

The stricter requirement for complete model-ready values is enforced later in `AIRequestBuilder`.

---

### `aggregator-api/app/internal/repositories/aggregator_repository.py`

Adds a second repository query for the newer Data Engineering schema.

The new query joins:

```text
Fire_Incident_Record
    ↓ location_id
Location_Registry

Fire_Incident_Record
    ↓ time_id
Time_Registry
```

The existing `fire_events_full` query is deliberately retained so the current Backend path is not removed while the newer integration is being established.

---

### `aggregator-api/app/routers/fire_data.py`

Adds internal Backend endpoints including:

```text
GET /internal/data/fire-incidents?days=<n>
GET /internal/data/fire-risk-inputs?hours=<n>
```

These routes are intended for service-to-service use and are not Frontend endpoints.

The Fire Risk Map source route exposes the confirmed Data Engineering weather/location/time shape through `aggregator-api`, keeping Data Engineering database access isolated from the Frontend-facing API.

---

## 4. Current integration boundary

The following parts are now defined:

```text
Aggregator API
    ↓
AggregatorClient
    ↓
AIRequestBuilder
    ↓
AIModellingClient
    ↓
POST /predict/bushfire/forecast
    ↓
ForecastNormaliser
    ↓
ForecastService / existing Fire Risk Map API path
```

The AI request and response structures are now known. Frontend's minimum output contract is also confirmed.

The Data Engineering → Backend mapping is now structurally confirmed. The remaining live-data dependency is population of the required ERA5 feature values, chronological time_id values, and grid_row / grid_col values.

---

## 5. Confirmed Data Engineering source and remaining blocker

Data Engineering has now confirmed the intended source structure for the live Fire Risk Map input path.

The current source is:

public.weather_observation
    ↓ location_id
public.location_registry

public.weather_observation
    ↓ time_id
public.time_registry

Confirmed field ownership:

all seven current AI input feature columns exist directly on public.weather_observation;

location_registry provides grid_latitude, grid_longitude, grid_row and grid_col;

time_registry.datetime_record is the intended chronological timestamp;

weather_observation.location_id and weather_observation.time_id provide the required joins;

Aggregator access to the shared Supabase PostgreSQL database should use the scoped aggregator_readonly role rather than a service-role credential.

The remaining issue is data population:

all seven ERA5 feature columns are currently null on the existing weather_observation rows;

time_id is currently null on the existing weather rows, so the observations cannot yet be ordered into the required 30-step sequences;

grid_row and grid_col now exist on location_registry but are currently unpopulated.

This means the schema and Backend mapping are ready, but the live DE → Backend → AI path cannot yet construct a valid model request.

No missing model feature, timestamp or grid index should be approximated from an unrelated field. Backend should fail clearly until the required DE values are populated.

---

## 6. Known local limitation

The current local Docker PostgreSQL database does not contain the newer shared Data Engineering schema used by the Supabase environment.

As a result, the Fire Risk Map source query cannot be fully exercised against the inherited local Docker database.

The intended shared access path is now confirmed as the Data Engineering Supabase PostgreSQL database using the scoped `aggregator_readonly` role.

Even against the shared schema, the live Fire Risk Map request remains blocked until Data Engineering populates:

- the seven ERA5 model-input fields;
- `time_id`;
- `grid_row`;
- `grid_col`.

This is currently a data-population dependency rather than an unresolved Backend schema or contract issue.

---

## 7. Sprint 1 completion path

The intended final validation is:

```text
Data Engineering records
    ↓
Aggregator API
    ↓
AI-compatible 30-step request
    ↓
POST /predict/bushfire/forecast
    ↓
AI GeoJSON prediction
    ↓
Backend normalisation
    ↓
GET /api/bushfire-forecast
    ↓
Frontend renders Fire Risk Map polygons using risk_factor
```

Because the live DE source is not yet populated with complete AI-ready values, the same Backend/Frontend contract can still be validated using the confirmed AI request/response fixture or agreed pre-generated prediction data. The live Data Engineering path remains a documented data-population dependency rather than an unresolved schema-mapping dependency.

---

## 8. Key design decisions

- Keep `GET /api/bushfire-forecast` as the stable Frontend-facing endpoint.
- Keep `/api/ws` available but optional for Sprint 1.
- Keep Frontend isolated from Aggregator API and AI Modelling API details.
- Use REST for direct cross-stream integration.
- Preserve the existing RabbitMQ prediction path while introducing the AI REST path.
- Do not recalculate AI's `risk_factor`; AI already returns the Frontend-compatible `1..5` value.
- Keep AI input feature handling flexible because the feature list may grow later.
- Keep the legacy Backend data path available while the newer Data Engineering schema is introduced.
- Access the shared Data Engineering Supabase PostgreSQL source through the scoped `aggregator_readonly` role.
- Do not substitute older general weather fields for the confirmed ERA5 model inputs.
- Do not fabricate missing DE feature values, timestamps or grid indices; incomplete source data should fail clearly until populated.
- Coordinate the shared `ForecastService` storage path with PR #214 so the read and write paths remain consistent.