# Terrain Feature Research

## 1. Purpose

This research looks at terrain features that could be added as environmental features for the FireFusion bushfire forecasting model.

The current FireFusion dataset already contains climate and land features from ERA5 and ERA5-Land. Terrain features could add another type of information by describing the physical landscape of each location.

The main terrain features explored are:

- Elevation
- Slope

The terrain data also needs to work with the current FireFusion structure. This means it should be possible to process the data into the same 5 km grid setup and later match it with the existing dataset using `.geo`.

Unlike most of the current environmental features, elevation and slope are static. They only need to be calculated once for each grid cell rather than collected for every datetime.


## 2. Why Terrain Information Could Be Useful

Terrain can affect local environmental conditions and fire behaviour.

Elevation describes the height of the landscape, while slope describes how steep the terrain is.

These features provide information that is different from weather variables such as temperature, wind and radiation.

For example, two locations could experience similar weather conditions but have very different terrain. Adding elevation and slope allows the model to represent some of these differences.

Slope could be particularly useful because fire behaviour can change depending on terrain steepness.


## 3. Selected Dataset

### Geoscience Australia DEM-S

**Dataset:** Australian Smoothed Digital Elevation Model (DEM-S)

**Google Earth Engine ID:**

`AU/GA/DEM_1SEC/v10/DEM-S`

DEM-S is an Australian Digital Elevation Model derived from Shuttle Radar Topography Mission (SRTM) data.

It represents ground surface topography and has been smoothed to reduce noise and provide a smoother representation of the terrain.

The dataset has a spatial resolution of approximately 30 m and covers Australia, including Victoria.

The elevation surface can also be used to calculate other terrain features such as slope.

Since terrain is treated as static for this project, the same terrain information can be used throughout the FireFusion 2018–2022 training period.


## 4. Elevation

### What is Elevation?

Elevation represents the height of the ground surface relative to sea level.

DEM-S provides elevation values across Australia.

### Potential Use in FireFusion

Elevation could provide a physical terrain feature for each FireFusion grid cell.

For example, two locations could experience similar weather conditions but exist at very different elevations.

Including elevation allows the model to represent this difference rather than relying only on the existing climate and land features.

The proposed feature is:

`elevation`


## 5. Slope

### What is Slope?

Slope represents how steep the terrain is.

It can be calculated from changes in elevation between nearby locations.

Lower slope values represent flatter terrain, while higher values represent steeper terrain.

### Potential Use in FireFusion

Slope could provide useful information about the terrain structure of each FireFusion grid cell.

This could be relevant because fire behaviour can be affected by terrain steepness.

Slope does not require another dataset because it can be calculated directly from the DEM-S elevation surface using Google Earth Engine.

The proposed feature is:

`slope`


## 6. Why DEM-S Was Selected

DEM-S was selected as the main terrain dataset to test because:

- It covers Victoria.
- It provides detailed Australian elevation data at approximately 30 m resolution.
- It represents ground surface topography.
- Slope can be calculated from the same elevation data.
- It is available directly through Google Earth Engine.
- Its higher resolution allows multiple terrain pixels to be summarised within each FireFusion 5 km grid cell.
- Elevation and slope provide information that is different from the existing climate features.
- One source can be used for both terrain features.

Using one dataset for both elevation and slope also keeps the collection and processing method consistent.


## 7. Spatial Compatibility with FireFusion

DEM-S uses approximately 30 m pixels, while FireFusion uses a larger 5 km grid.

Because the spatial resolutions are different, the DEM-S pixels need to be aggregated into the FireFusion grid before the features can be combined with the existing data.

The terrain collection will use the same general grid setup as the current FireFusion GEE workflow:

- **Region:** Victoria, Australia
- **Boundary:** `FAO/GAUL/2015/level1`
- **Grid size:** 5 km
- **Projection:** `EPSG:3857`

### Proposed Spatial Processing

1. Load the Victoria boundary.
2. Generate the FireFusion-style 5 km grid.
3. Load DEM-S covering Victoria.
4. Select the elevation data.
5. Calculate slope from the elevation surface.
6. Identify the DEM pixels within each 5 km grid cell.
7. Calculate representative elevation and slope values for each cell.
8. Export the results with `.geo`.
9. Compare the generated `.geo` geometries with the existing FireFusion data.
10. Check for missing or unexpected terrain values.

The final terrain dataset will therefore use the 5 km FireFusion-style grid rather than the original 30 m DEM-S grid.


## 8. Spatial Aggregation

Many DEM-S pixels can fall inside one 5 km FireFusion grid cell.

These values need to be combined into representative terrain features.

For the first version, the selected aggregation methods are:

- Mean elevation
- Mean slope

For example:

| FireFusion `.geo` | elevation | slope |
|---|---:|---:|
| Grid A | 420.5 | 7.3 |
| Grid B | 615.2 | 12.6 |
| Grid C | 183.8 | 3.9 |

Mean aggregation gives a simple representation of the overall terrain within each grid cell.

The number of valid DEM pixels used for each value can also be recorded for validation.

Other terrain statistics could be tested later if needed, such as:

- Minimum elevation
- Maximum elevation
- Elevation range
- Median elevation
- Maximum slope
- Median slope

These are not required for the first collection. They can be explored later if mean elevation and mean slope do not provide enough information.


## 9. Temporal Compatibility with FireFusion

Elevation and slope are static features.

Unlike ERA5, ERA5-Land or MODIS vegetation observations, terrain does not need to be collected for every timestamp.

The standalone terrain dataset can therefore contain one terrain record for each `.geo`.

For example:

| `.geo` | elevation | slope |
|---|---:|---:|
| Grid A | 420.5 | 7.3 |
| Grid B | 615.2 | 12.6 |

When terrain is later combined with the existing FireFusion environmental data, the terrain values can be matched using `.geo`.

For example:

| `.geo` | datetime | elevation | slope |
|---|---|---:|---:|
| Grid A | 2018-01-01 00:00 | 420.5 | 7.3 |
| Grid A | 2018-01-01 12:00 | 420.5 | 7.3 |
| Grid A | 2018-01-02 00:00 | 420.5 | 7.3 |

The elevation and slope values stay the same across different timestamps because the physical terrain does not change between observations.

This does not mean DEM-S provides data every 12 hours. The terrain values are simply static features attached to each geographic grid cell.


## 10. Matching with the Existing FireFusion Data

The current ERA5 and ERA5-Land workflow uses geographic geometry and datetime to align environmental observations.

Terrain requires a slightly different method because it does not have a changing datetime.

The proposed terrain matching method is:

1. Generate elevation and slope for each 5 km `.geo`.
2. Compare the terrain `.geo` geometries with the existing FireFusion data.
3. Confirm that the grid cells represent the same geographic locations.
4. Match the terrain data with the environmental dataset using `.geo`.
5. Keep the original FireFusion datetime.
6. Repeat the terrain values across records belonging to the same `.geo`.
7. Check that the join does not unexpectedly add or remove environmental records.

This means the final modelling dataset can still keep both `.geo` and `datetime`, even though terrain itself only needs `.geo` for matching.


## 11. Collection Output

The standalone terrain dataset could contain:

| `.geo` | elevation | slope |
|---|---:|---:|
| Grid A | value | value |
| Grid B | value | value |
| Grid C | value | value |

The collection script can also keep:

- `grid_id`
- `elevation_valid_pixel_count`
- `slope_valid_pixel_count`
- `dataset`

After combining the terrain features with the existing FireFusion data, the structure could look like:

| `.geo` | datetime | existing features | elevation | slope |
|---|---|---|---:|---:|
| Grid A | 2018-01-01 00:00 | ... | 420.5 | 7.3 |
| Grid A | 2018-01-01 12:00 | ... | 420.5 | 7.3 |
| Grid B | 2018-01-01 00:00 | ... | 615.2 | 12.6 |

This adds the terrain features without changing the existing FireFusion temporal structure.


## 12. Validation

The terrain output should be checked before it is combined with the full FireFusion dataset.

The initial validation should include:

1. Check the number of unique `.geo` geometries.
2. Compare the generated `.geo` with the existing FireFusion grid.
3. Check for FireFusion grid cells that are missing terrain information.
4. Check for missing elevation values.
5. Check for missing slope values.
6. Check the minimum and maximum elevation.
7. Check the minimum and maximum slope.
8. Review the number of valid DEM pixels used for each grid cell.
9. Test joining the terrain data with a sample of the existing environmental data.
10. Confirm that the join does not unexpectedly change the number of records.

Several grid cells should also be checked manually to make sure the terrain values are reasonable for their locations.


## 13. Initial Recommendation

Geoscience Australia DEM-S is recommended as the first terrain dataset to test for FireFusion.

The initial features are:

- `elevation`
- `slope`

DEM-S is suitable for further testing because it covers Victoria, is available through GEE, provides detailed terrain information, and can be processed into the FireFusion 5 km grid structure.

Another advantage is that the terrain data only needs to be processed once because elevation and slope are static.

The main requirement before integration is confirming that the generated 5 km `.geo` geometries correctly align with the existing FireFusion data.


## 14. Proposed Testing

Before using the terrain features in the full dataset:

1. Generate the FireFusion-style 5 km Victoria grid.
2. Load DEM-S from Google Earth Engine.
3. Extract elevation.
4. Calculate slope from the elevation surface.
5. Calculate mean elevation and mean slope for each grid cell.
6. Record the number of valid source pixels used.
7. Export the terrain features with `.geo`.
8. Compare the generated `.geo` geometries with the existing FireFusion grid.
9. Check elevation and slope value ranges.
10. Check for missing values.
11. Manually review several locations.
12. Test joining the terrain output with a sample of the combined ERA5 and ERA5-Land data.
13. Confirm that the join does not create or remove environmental records.
14. Only use the terrain features for full integration after the method has been validated.


## 15. Next Steps

1. Run the terrain collection script.
2. Check the generated elevation and slope values.
3. Validate `.geo` against the existing FireFusion data.
4. Check missing values and valid-pixel counts.
5. Test the terrain join with a sample of the combined ERA5 and ERA5-Land dataset.
6. Review whether mean elevation and mean slope provide enough information.
7. Explore additional terrain statistics later if needed.
8. Review the results with the AI Modelling team.
9. Use the terrain features in the full dataset after the processing and matching methods have been confirmed.


## 16. References

Google Earth Engine. (n.d.). *DEM-S: Australian Smoothed Digital Elevation Model*. Earth Engine Data Catalog.  
https://developers.google.com/earth-engine/datasets/catalog/AU_GA_DEM_1SEC_v10_DEM-S

Geoscience Australia. (n.d.). *Smoothed Digital Elevation Model (DEM-S) of Australia derived from SRTM data*. Geoscience Australia.