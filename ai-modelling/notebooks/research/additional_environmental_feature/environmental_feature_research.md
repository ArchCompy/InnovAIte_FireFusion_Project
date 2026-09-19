# Additional Environmental Feature Research

## 1. Purpose

This research explores additional environmental features that could be useful for the FireFusion bushfire forecasting model.

The current FireFusion dataset already contains environmental and climate features from ERA5 and ERA5-Land. The goal of this task is to find additional features that provide useful information that is not already covered by the current dataset.

The new data also needs to work with the current FireFusion data structure. Where possible, the features should be processed into the same 5 km geographic grid used by the existing GEE datasets and later matched using `.geo` and datetime where required.

The main features explored are:

- Vegetation index
- Elevation
- Slope


## 2. Requirements

For an additional feature to be suitable for FireFusion, it should:

- Cover the required FireFusion training period of 2018–2022 where temporal data is required.
- Cover Victoria, Australia.
- Provide information that is relevant to bushfire conditions.
- Have a spatial resolution that can be processed into the FireFusion 5 km grid.
- Be able to align with the existing dataset using geographic geometry.
- Have a clear way of handling datetime if its temporal resolution is different from the current data.
- Avoid unnecessary duplication of features already available from ERA5 and ERA5-Land.


## 3. Vegetation Index

### Candidate Dataset

**MODIS MOD13Q1 V6.1 – Terra Vegetation Indices**

Google Earth Engine dataset:

`MODIS/061/MOD13Q1`

MOD13Q1 provides vegetation index data at 250 m spatial resolution with a 16-day temporal frequency.

The dataset contains both Normalized Difference Vegetation Index (NDVI) and Enhanced Vegetation Index (EVI), as well as quality information that can be used to filter unreliable observations.

MOD13Q1 has coverage from 2000 onwards, so it covers the required FireFusion period of 2018–2022.

### Proposed Features

- `ndvi`
- `evi`

### Why It Could Be Useful

ERA5 and ERA5-Land mainly provide information about weather and land conditions, including temperature, wind, radiation and soil conditions.

NDVI and EVI add information about vegetation condition.

This could be useful for bushfire forecasting because vegetation is part of the available fuel in the landscape. Changes in vegetation condition could provide information that is not directly represented by the existing climate features.

EVI could also provide additional vegetation information, particularly in areas with denser vegetation where NDVI can become less sensitive.

### Compatibility with FireFusion

MOD13Q1 uses 250 m pixels, while FireFusion uses a larger 5 km grid.

To make the vegetation data compatible with FireFusion, the proposed approach is:

1. Load MOD13Q1 observations covering Victoria.
2. Apply quality filtering to remove unreliable observations.
3. Generate the same 5 km grid setup used by the current FireFusion GEE datasets.
4. Aggregate the valid 250 m MODIS pixels within each 5 km grid cell.
5. Export the NDVI and EVI values with the corresponding `.geo`.
6. Validate the generated `.geo` against the existing FireFusion grid.
7. Map the 16-day vegetation observations to the appropriate FireFusion datetime period.

The output could follow a structure similar to:

| `.geo` | datetime | ndvi | evi |
|---|---|---:|---:|
| Grid geometry A | 2018-01-01 00:00 | value | value |
| Grid geometry A | 2018-01-01 12:00 | value | value |

The temporal mapping method still needs to be tested.

MODIS provides vegetation observations every 16 days, so the data should not be treated as if vegetation was directly measured every 12 hours. Instead, each vegetation observation can represent the condition for its relevant period and later be mapped to the FireFusion timestamps using a clear and documented method.


## 4. Elevation and Slope

### Candidate Dataset

**Geoscience Australia DEM-S – Australian Smoothed Digital Elevation Model**

Google Earth Engine dataset:

`AU/GA/DEM_1SEC/v10/DEM-S`

DEM-S provides elevation data across Australia at approximately 30 m spatial resolution.

The dataset represents ground surface topography and can also be used to derive terrain features such as slope.

### Proposed Features

- `elevation`
- `slope`

### Why They Could Be Useful

Elevation and slope add information about the physical terrain that is not directly represented by the existing climate features.

Terrain can influence local environmental conditions and fire behaviour. Slope is particularly useful because fire behaviour can change between flat and steep terrain.

Unlike the vegetation features, elevation and slope are static. This means they only need to be calculated once for each FireFusion grid cell rather than collected separately for every year or datetime.

### Compatibility with FireFusion

DEM-S has a much higher spatial resolution than the FireFusion 5 km grid.

The proposed approach is:

1. Load DEM-S data covering Victoria.
2. Use the elevation band for elevation.
3. Calculate slope from the elevation surface.
4. Generate the same 5 km grid setup used by the current FireFusion GEE datasets.
5. Aggregate the higher-resolution terrain pixels within each 5 km grid cell.
6. Export the elevation and slope values with the corresponding `.geo`.
7. Validate the generated `.geo` against the existing FireFusion grid.

The standalone terrain output could look like:

| `.geo` | elevation | slope |
|---|---:|---:|
| Grid geometry A | value | value |
| Grid geometry B | value | value |

Elevation and slope do not need their own datetime because they are static.

When the terrain data is later combined with the existing FireFusion environmental dataset, the values can be matched using `.geo` while keeping the existing FireFusion datetime.

For example:

| `.geo` | datetime | elevation | slope |
|---|---|---:|---:|
| Grid A | 2018-01-01 00:00 | 420 | 7.3 |
| Grid A | 2018-01-01 12:00 | 420 | 7.3 |
| Grid A | 2018-01-02 00:00 | 420 | 7.3 |

The same elevation and slope values appearing across different timestamps is expected because the physical terrain does not change between observations.


## 5. Comparison

| Feature | Source | Spatial Resolution | Temporal Resolution | FireFusion Alignment | Suitability |
|---|---|---|---|---|---|
| NDVI | MODIS MOD13Q1 | 250 m | 16 days | `.geo` + temporal mapping | High |
| EVI | MODIS MOD13Q1 | 250 m | 16 days | `.geo` + temporal mapping | High |
| Elevation | GA DEM-S | ~30 m | Static | `.geo` | High |
| Slope | Derived from GA DEM-S | ~30 m | Static | `.geo` | High |


## 6. Initial Recommendation

Based on the research, the features recommended for further testing are:

### Vegetation

- NDVI
- EVI

### Terrain

- Elevation
- Slope

These features were selected because they add two different types of information that are not directly covered by the current ERA5 and ERA5-Land features:

1. Vegetation condition through NDVI and EVI.
2. Physical terrain through elevation and slope.

MODIS MOD13Q1 and GA DEM-S are also suitable for the current workflow because both are available through Google Earth Engine, cover Victoria, and can be processed into the FireFusion 5 km grid structure.

At this stage, the features are recommended for **testing rather than immediate integration**.

NDVI and EVI still require testing for spatial aggregation and temporal mapping, while elevation and slope mainly require spatial aggregation and `.geo` validation.


## 7. Proposed Processing Workflow

The proposed workflow is:

1. Load the selected source dataset from Google Earth Engine.
2. Filter the data to Victoria.
3. Apply quality filtering where required.
4. Generate the same 5 km grid setup used by the current FireFusion GEE datasets.
5. Aggregate the source data within each 5 km grid cell.
6. Export the results with `.geo`.
7. Compare the generated `.geo` geometries with the existing FireFusion data.
8. Handle temporal alignment for features that require datetime matching.
9. Validate the output before combining it with the current FireFusion dataset.

This keeps the original meaning of the source data while making the new features suitable for the existing FireFusion structure.


## 8. Next Steps

1. Test MODIS MOD13Q1 collection on a smaller period.
2. Check the NDVI and EVI values, quality filtering and missing data.
3. Validate the generated vegetation `.geo` against the existing FireFusion grid.
4. Test the method for mapping the 16-day MODIS observations to the FireFusion datetime structure.
5. Collect elevation and calculate slope from DEM-S.
6. Validate the terrain `.geo` against the existing FireFusion grid.
7. Check the elevation and slope values and missing data.
8. Test combining the new features with a sample of the existing ERA5 and ERA5-Land data.
9. Only collect and integrate the complete dataset after the processing methods have been validated.


## 9. References

Google Earth Engine. (n.d.). *MOD13Q1.061 Terra Vegetation Indices 16-Day Global 250m*. Earth Engine Data Catalog.  
https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MOD13Q1

NASA LP DAAC. (2021). *MODIS/Terra Vegetation Indices 16-Day L3 Global 250m SIN Grid V061 (MOD13Q1)*.  
https://doi.org/10.5067/MODIS/MOD13Q1.061

Google Earth Engine. (n.d.). *DEM-S: Australian Smoothed Digital Elevation Model*. Earth Engine Data Catalog.  
https://developers.google.com/earth-engine/datasets/catalog/AU_GA_DEM_1SEC_v10_DEM-S

Geoscience Australia. (2015). *Digital Elevation Model (DEM) of Australia*. Geoscience Australia.