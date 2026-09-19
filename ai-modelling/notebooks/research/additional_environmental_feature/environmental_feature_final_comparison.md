# Environmental Feature Final Comparison

## 1. Purpose

This document summarises the additional environmental feature research for FireFusion and compares the selected vegetation and terrain features.

The goal is to find additional features that:

- Add useful information that is not already covered by the current ERA5 and ERA5-Land data.
- Are relevant to bushfire forecasting.
- Cover Victoria and the required historical period where needed.
- Can be processed into the FireFusion 5 km grid structure.
- Can be matched with the current dataset using `.geo` and datetime where required.

Based on the research, the features selected for further testing are:

- NDVI
- EVI
- Elevation
- Slope


## 2. Final Comparison

| Feature | Dataset | Information Added | Spatial Resolution | Temporal Resolution | FireFusion Matching | Suitability |
|---|---|---|---|---|---|---|
| NDVI | MODIS MOD13Q1 V6.1 | Vegetation greenness and condition | 250 m | 16 days | `.geo` + temporal mapping | High |
| EVI | MODIS MOD13Q1 V6.1 | Additional vegetation condition | 250 m | 16 days | `.geo` + temporal mapping | High |
| Elevation | GA DEM-S | Terrain height | ~30 m | Static | `.geo` | High |
| Slope | Derived from GA DEM-S | Terrain steepness | ~30 m | Static | `.geo` | High |


## 3. Vegetation Features

### Selected Dataset

**MODIS MOD13Q1 V6.1**

Google Earth Engine ID:

`MODIS/061/MOD13Q1`

### Selected Features

- `ndvi`
- `evi`

NDVI and EVI were selected because they add information about vegetation condition, which is different from the climate and land features already available from ERA5 and ERA5-Land.

MOD13Q1 is suitable for further testing because:

- It provides both NDVI and EVI.
- It covers Victoria.
- It covers the required 2018–2022 period.
- It is available through Google Earth Engine.
- It provides vegetation data at 250 m resolution.
- It includes quality information that can be used to filter unreliable observations.
- The higher-resolution pixels can be aggregated into the FireFusion 5 km grid.

### Main Limitation

The main challenge is the temporal resolution.

The current FireFusion environmental data uses approximately 12-hour observations, while MOD13Q1 provides vegetation composites every 16 days.

Because of this, NDVI and EVI should not be treated as if vegetation was directly measured every 12 hours.

The original MODIS observation period should be kept during collection, and the method for mapping the vegetation values to the FireFusion datetime structure should be tested before integration.


## 4. Terrain Features

### Selected Dataset

**Geoscience Australia DEM-S**

Google Earth Engine ID:

`AU/GA/DEM_1SEC/v10/DEM-S`

### Selected Features

- `elevation`
- `slope`

Elevation and slope were selected because they add information about the physical terrain that is not directly represented by the current climate features.

DEM-S is suitable for further testing because:

- It covers Victoria.
- It provides detailed Australian terrain data at approximately 30 m resolution.
- Elevation is available directly from the dataset.
- Slope can be calculated from the same elevation surface.
- It is available through Google Earth Engine.
- The higher-resolution terrain data can be aggregated into the FireFusion 5 km grid.
- Terrain only needs to be processed once because it is static.

### Main Limitation

DEM-S uses a much finer spatial resolution than the FireFusion grid.

The original DEM pixels therefore cannot be used directly. They need to be aggregated into representative terrain values for each 5 km grid cell.

Mean elevation and mean slope will be tested first. Other terrain statistics can be explored later if needed.


## 5. Compatibility with FireFusion

Both datasets can be processed using the same general grid setup as the current FireFusion GEE workflow:

- **Region:** Victoria, Australia
- **Boundary:** `FAO/GAUL/2015/level1`
- **Grid size:** 5 km
- **Projection:** `EPSG:3857`

The generated `.geo` should then be compared with the existing FireFusion data before the new features are combined.


### 5.1 NDVI and EVI

NDVI and EVI require both spatial and temporal processing.

The proposed method is:

1. Load the Victoria boundary.
2. Generate the FireFusion-style 5 km grid.
3. Load MOD13Q1 observations covering Victoria.
4. Apply the required scale factor and quality filtering.
5. Aggregate valid 250 m MODIS pixels within each 5 km grid cell.
6. Export NDVI and EVI with `.geo` and the original MODIS observation period.
7. Compare the generated `.geo` with the existing FireFusion data.
8. Test the method for mapping the 16-day observations to the FireFusion datetime structure.
9. Only combine the vegetation features after spatial and temporal compatibility has been validated.


### 5.2 Elevation and Slope

Elevation and slope only require spatial matching because they are static.

The proposed method is:

1. Load the Victoria boundary.
2. Generate the FireFusion-style 5 km grid.
3. Load DEM-S covering Victoria.
4. Extract elevation.
5. Calculate slope from the elevation surface.
6. Aggregate the higher-resolution terrain data within each 5 km grid cell.
7. Export elevation and slope with `.geo`.
8. Compare the generated `.geo` with the existing FireFusion data.
9. Match the terrain features using `.geo` while keeping the existing FireFusion datetime.
10. Confirm that the join does not unexpectedly create or remove records.


## 6. Expected Final Structure

After the features have been validated and combined with the existing environmental data, the structure could look like:

| `.geo` | datetime | ndvi | evi | elevation | slope |
|---|---|---:|---:|---:|---:|
| Grid A | 2018-01-01 00:00 | value | value | value | value |
| Grid A | 2018-01-01 12:00 | value | value | value | value |
| Grid B | 2018-01-01 00:00 | value | value | value | value |

NDVI and EVI may stay the same across multiple FireFusion timestamps because MOD13Q1 has a 16-day temporal frequency.

Elevation and slope will also stay the same across timestamps because terrain is static.


## 7. Benefits and Limitations

| Feature | Main Benefit | Main Limitation |
|---|---|---|
| NDVI | Adds vegetation greenness and condition | 16-day temporal resolution |
| EVI | Adds additional vegetation information, especially for denser vegetation | 16-day temporal resolution and may overlap with NDVI |
| Elevation | Adds physical terrain information | Requires spatial aggregation |
| Slope | Adds terrain steepness information | Needs to be derived and spatially aggregated |


## 8. Final Recommendation

Based on the research, all four features are suitable candidates for further testing.

### Vegetation

- NDVI
- EVI

### Terrain

- Elevation
- Slope

These features were selected because they add two different types of information to the current FireFusion dataset:

1. **Vegetation condition** through NDVI and EVI.
2. **Physical terrain** through elevation and slope.

MODIS MOD13Q1 and GA DEM-S were also selected because both are available through Google Earth Engine, cover Victoria, and can be processed into the FireFusion 5 km grid structure.

At this stage, the features should be **tested before they are added to the full dataset**.

The main checks are whether the generated `.geo` correctly matches the existing FireFusion data and whether the MODIS temporal mapping can be handled without changing the meaning of the original vegetation observations.


## 9. Testing Priority

The proposed testing order is:

1. **Elevation and slope**
   - Both can be collected from the same DEM-S source.
   - They are static, so no temporal mapping is required.
   - The main requirement is `.geo` validation.

2. **NDVI and EVI**
   - Both can be collected together from MOD13Q1.
   - They require both spatial aggregation and temporal mapping.
   - The 16-day observation period needs to be handled carefully.

This allows the simpler terrain workflow to be validated first before testing the additional temporal processing required for vegetation.


## 10. Validation Requirements

Before the new features are combined with the complete FireFusion dataset:

1. Compare the generated `.geo` geometries with the existing FireFusion data.
2. Check the number of unique grid cells.
3. Check for missing values.
4. Check the feature value ranges.
5. Review valid source-pixel counts.
6. Manually inspect several grid cells.
7. Confirm that the spatial aggregation produces reasonable values.
8. Test the temporal mapping for NDVI and EVI.
9. Test joining the features with a sample of the combined ERA5 and ERA5-Land data.
10. Confirm that the join does not unexpectedly add or remove records.


## 11. Next Steps

1. Run the terrain collection script.
2. Validate elevation and slope values.
3. Compare the terrain `.geo` with the existing FireFusion data.
4. Test joining the terrain features with a sample of the current environmental dataset.
5. Run the vegetation collection on a smaller test period.
6. Check NDVI and EVI quality, values and missing data.
7. Compare the vegetation `.geo` with the existing FireFusion data.
8. Test the MODIS temporal mapping method.
9. Test combining the vegetation features with a sample of the current environmental dataset.
10. Review the results with the AI Modelling team.
11. Only proceed with full integration after the processing methods have been validated.


## 12. Supporting Research

More detailed research is available in:

- `environmental_feature_research.md`
- `vegetation_index_research.md`
- `terrain_feature_research.md`


## 13. References

Google Earth Engine. (n.d.). *MOD13Q1.061 Terra Vegetation Indices 16-Day Global 250m*. Earth Engine Data Catalog.  
https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MOD13Q1

NASA LP DAAC. (2021). *MODIS/Terra Vegetation Indices 16-Day L3 Global 250m SIN Grid V061 (MOD13Q1)*.  
https://doi.org/10.5067/MODIS/MOD13Q1.061

Google Earth Engine. (n.d.). *DEM-S: Australian Smoothed Digital Elevation Model*. Earth Engine Data Catalog.  
https://developers.google.com/earth-engine/datasets/catalog/AU_GA_DEM_1SEC_v10_DEM-S

Geoscience Australia. (n.d.). *Smoothed Digital Elevation Model (DEM-S) of Australia derived from SRTM data*. Geoscience Australia.