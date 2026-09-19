# Additional Environmental Features

## Overview

This folder contains the research and data collection work for adding additional environmental features to the FireFusion bushfire forecasting dataset.

The current FireFusion dataset already uses environmental data from ERA5 and ERA5-Land. This task explores other features that could provide useful information that is not already covered by the current data.

After comparing different options, the features selected for further testing are:

- **NDVI**
- **EVI**
- **Elevation**
- **Slope**

Two datasets were selected:

- **MODIS MOD13Q1 V6.1** for NDVI and EVI
- **Geoscience Australia DEM-S** for elevation and slope

Both datasets are available through Google Earth Engine (GEE) and can be processed into the same 5 km grid structure used by the current FireFusion GEE datasets.


## Selected Features

### Vegetation Index

**Dataset:** MODIS MOD13Q1 V6.1

**GEE Dataset ID:**

`MODIS/061/MOD13Q1`

**Features:**

- NDVI
- EVI

MOD13Q1 provides vegetation index data at 250 m resolution with observations every 16 days.

NDVI and EVI were selected because they provide information about vegetation condition, which is different from the weather and land variables already available from ERA5 and ERA5-Land.

MOD13Q1 was selected because:

- It provides both NDVI and EVI.
- It covers Victoria.
- It covers the required 2018–2022 period.
- It is available directly through GEE.
- It includes quality information that can be used to filter unreliable observations.
- Its 250 m pixels can be aggregated into the FireFusion 5 km grid.

One limitation is that MOD13Q1 uses a 16-day temporal frequency, while the current FireFusion environmental data uses 12-hour observations.

Because of this, the MODIS data will first be kept at its original temporal frequency. The method for matching it with the FireFusion datetime will be tested before the data is combined.


### Terrain

**Dataset:** Geoscience Australia DEM-S

**GEE Dataset ID:**

`AU/GA/DEM_1SEC/v10/DEM-S`

**Features:**

- Elevation
- Slope

DEM-S provides elevation data for Australia at approximately 30 m resolution.

Elevation is taken directly from the DEM, while slope is calculated from the elevation surface using Google Earth Engine.

These features were selected because they provide information about the physical terrain that is not directly represented by the existing climate data.

DEM-S was selected because:

- It covers Victoria.
- It provides detailed Australian terrain data.
- Elevation and slope can come from the same dataset.
- It is available directly through GEE.
- The higher-resolution data can be aggregated into the FireFusion 5 km grid.

Elevation and slope are static, so they only need to be calculated once for each grid cell.


## Why These Features Were Selected

The main goal was to find features that add new information instead of collecting more variables that are already similar to the existing ERA5 and ERA5-Land data.

| Feature | What It Adds | Dataset | Matching Method |
|---|---|---|---|
| NDVI | Vegetation greenness and condition | MODIS MOD13Q1 | `.geo` + datetime mapping |
| EVI | Additional vegetation condition information | MODIS MOD13Q1 | `.geo` + datetime mapping |
| Elevation | Terrain height | GA DEM-S | `.geo` |
| Slope | Terrain steepness | GA DEM-S | `.geo` |

The selected datasets also cover Victoria, are available through GEE, and can be processed into the existing FireFusion grid structure.


## Grid Compatibility

MODIS and DEM-S do not originally use the same grid as the current FireFusion data.

To make the new features compatible, the collection scripts use the same general grid setup as the existing FireFusion GEE workflow:

- **Region:** Victoria, Australia
- **Boundary:** `FAO/GAUL/2015/level1`
- **Grid size:** 5 km
- **Projection:** `EPSG:3857`

The processing workflow is:

1. Load the Victoria boundary.
2. Generate the 5 km grid.
3. Load the environmental dataset from GEE.
4. Process the required features.
5. Aggregate the original higher-resolution data into each 5 km grid cell.
6. Export the result with `.geo`.
7. Compare the new `.geo` geometries with the existing FireFusion data.
8. Only combine the datasets after the spatial alignment has been validated.

`grid_id` is included as a reference, but it should not be used by itself to match different datasets.

The `.geo` geometry should be used to confirm that the grid cells represent the same geographic locations.


## Vegetation Processing

The vegetation script collects NDVI and EVI from MODIS MOD13Q1.

The processing steps are:

1. Load MODIS MOD13Q1.
2. Select NDVI and EVI.
3. Use `SummaryQA` to keep good-quality observations.
4. Apply the MODIS scale factor.
5. Calculate the mean NDVI and EVI from valid 250 m pixels inside each 5 km grid cell.
6. Record the number of valid pixels used for each value.
7. Keep the original MODIS observation date and validity period.
8. Export the results for validation and later temporal matching.

The output contains:

- `grid_id`
- `.geo`
- `datetime`
- `valid_from`
- `valid_until`
- `ndvi`
- `evi`
- `ndvi_valid_pixel_count`
- `evi_valid_pixel_count`
- `dataset`


## Terrain Processing

The terrain script collects elevation from DEM-S and calculates slope from the elevation surface.

The processing steps are:

1. Load DEM-S.
2. Select elevation.
3. Calculate slope.
4. Calculate mean elevation and mean slope inside each 5 km grid cell.
5. Record the number of valid source pixels used.
6. Export the results with `.geo`.

The output contains:

- `grid_id`
- `.geo`
- `elevation`
- `slope`
- `elevation_valid_pixel_count`
- `slope_valid_pixel_count`
- `dataset`

There is no separate datetime for terrain because elevation and slope are static.

When the terrain features are later combined with the current environmental dataset, they can be matched using `.geo` while keeping the existing FireFusion datetime.


## Folder Structure

```text
additional-environmental-features/
├── README.md
├── collect_vegetation_features.py
├── collect_terrain_features.py
└── research/
    ├── environmental_feature_research.md
    ├── vegetation_index_research.md
    ├── terrain_feature_research.md
    └── environmental_feature_final_comparison.md