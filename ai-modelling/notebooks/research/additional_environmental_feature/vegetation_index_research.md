# Vegetation Index Research

## 1. Purpose

This research looks at vegetation indices that could be added as environmental features for the FireFusion bushfire forecasting model.

The current FireFusion dataset already contains climate and land features from ERA5 and ERA5-Land. Vegetation indices could add another type of information by showing the vegetation condition across different locations and periods.

The main vegetation indices explored are:

- Normalized Difference Vegetation Index (NDVI)
- Enhanced Vegetation Index (EVI)

The selected vegetation data also needs to work with the current FireFusion structure. This means it should be possible to process the data into the same 5 km grid setup and later align it using `.geo` and datetime.


## 2. Why Vegetation Information Could Be Useful

The current environmental features mainly describe conditions such as temperature, wind, radiation and soil conditions.

Vegetation indices provide different information because they describe the vegetation itself.

This could be useful for bushfire forecasting because vegetation is part of the available fuel in the landscape. Two locations could have similar weather conditions but different vegetation conditions, which may affect their bushfire risk differently.

Adding vegetation features could help the model capture this difference.


## 3. Selected Dataset

### MODIS MOD13Q1 V6.1

**Dataset:** MOD13Q1.061 Terra Vegetation Indices 16-Day Global 250m

**Google Earth Engine ID:**

`MODIS/061/MOD13Q1`

MOD13Q1 is a MODIS vegetation product available through Google Earth Engine.

It provides vegetation index data at approximately 250 m spatial resolution with observations every 16 days.

The dataset includes:

- NDVI
- EVI
- Detailed quality information
- Pixel reliability information

MOD13Q1 has historical coverage from 2000 onwards, so it covers the required FireFusion training period of 2018–2022.


## 4. NDVI

### What is NDVI?

NDVI stands for **Normalized Difference Vegetation Index**.

It uses reflected near-infrared and red light to measure vegetation greenness.

The general formula is:

`NDVI = (NIR - Red) / (NIR + Red)`

Healthy green vegetation normally reflects more near-infrared light and absorbs more red light, which results in a higher NDVI value.

Lower values can represent areas with less green vegetation, bare ground, water or other non-vegetated surfaces.

### Potential Use in FireFusion

NDVI could provide vegetation condition information for each FireFusion grid cell.

It would not be used as a direct measurement of bushfire occurrence. Instead, it would be an additional environmental feature that helps describe the condition of the landscape.

The MOD13Q1 NDVI band uses a scale factor of `0.0001`, so the raw values need to be scaled before they are used.


## 5. EVI

### What is EVI?

EVI stands for **Enhanced Vegetation Index**.

Like NDVI, it provides information about vegetation condition. However, EVI is designed to improve vegetation monitoring in areas with denser vegetation and reduce some effects from atmospheric conditions and the background below the vegetation canopy.

### Potential Use in FireFusion

EVI could provide additional vegetation information alongside NDVI.

Since MOD13Q1 already provides both features, NDVI and EVI can initially be collected together and tested.

The modelling stage can later determine whether:

- NDVI is enough by itself.
- EVI adds useful information.
- NDVI and EVI are too similar to keep both.

The EVI band also uses a scale factor of `0.0001`.


## 6. Why MOD13Q1 Was Selected

MOD13Q1 was selected as the main vegetation dataset to test because:

- It provides both NDVI and EVI.
- It covers Victoria.
- It covers the full 2018–2022 training period.
- It is available directly through Google Earth Engine.
- Its 250 m resolution provides multiple vegetation pixels within each 5 km FireFusion grid cell.
- It includes quality information for filtering unreliable observations.
- It is specifically designed for vegetation monitoring.

Using one source for both NDVI and EVI also keeps the collection process more consistent.


## 7. Spatial Compatibility with FireFusion

MOD13Q1 uses approximately 250 m pixels, while FireFusion uses a larger 5 km grid.

Because the spatial resolutions are different, the MODIS pixels need to be aggregated into the FireFusion grid before the data can be combined.

The vegetation collection will use the same general grid setup as the current FireFusion GEE workflow:

- **Region:** Victoria, Australia
- **Boundary:** `FAO/GAUL/2015/level1`
- **Grid size:** 5 km
- **Projection:** `EPSG:3857`

### Proposed Spatial Processing

1. Load the Victoria boundary.
2. Generate the FireFusion-style 5 km grid.
3. Load MOD13Q1 observations covering Victoria.
4. Select NDVI and EVI.
5. Apply the required scale factor and quality filtering.
6. Identify the valid MODIS pixels within each 5 km grid cell.
7. Calculate representative NDVI and EVI values for each cell.
8. Export the results with `.geo`.
9. Compare the generated `.geo` geometries with the existing FireFusion data.

The final vegetation data will therefore use the 5 km FireFusion-style grid rather than the original 250 m MODIS grid.


## 8. Spatial Aggregation

Multiple 250 m MODIS pixels can fall inside one 5 km FireFusion grid cell.

These pixels need to be combined into one representative vegetation value.

The initial approach is to calculate the **mean NDVI and EVI** from the valid MODIS pixels inside each grid cell.

For example:

| FireFusion `.geo` | MODIS pixels | Final NDVI |
|---|---:|---:|
| Grid A | Multiple valid pixels | Mean NDVI |
| Grid B | Multiple valid pixels | Mean NDVI |

The number of valid pixels used for each calculation can also be saved for validation.

Mean aggregation will be tested first. Median aggregation can also be compared later if outliers have a noticeable effect on the results.


## 9. Temporal Compatibility with FireFusion

The main challenge with MOD13Q1 is its temporal resolution.

The existing FireFusion environmental data uses observations at approximately:

- `00:00`
- `12:00`

This gives two observations per day.

MOD13Q1, however, provides vegetation composites every **16 days**.

Because of this, NDVI and EVI should not be treated as if they were directly measured every 12 hours.

The original MODIS observation date should first be kept during collection. The vegetation values can then be mapped to the relevant FireFusion timestamps during the later integration stage.


## 10. Proposed Temporal Processing

The initial approach is:

1. Keep the original MODIS observation date.
2. Identify the period represented by each observation.
3. Keep the NDVI and EVI values at their original temporal frequency during collection.
4. Determine which FireFusion timestamps fall within the relevant vegetation period.
5. Use the vegetation value for those timestamps when the datasets are later combined.
6. Keep the same value until the next applicable vegetation observation.
7. Avoid creating artificial changes between MODIS observations unless another method is tested and justified.
8. Document the final temporal mapping method.

This allows the vegetation features to work with the FireFusion 12-hour structure without claiming that MODIS directly measured vegetation every 12 hours.


## 11. Collection Output

Before temporal integration, the collected vegetation data could follow this structure:

| `.geo` | datetime | valid_from | valid_until | ndvi | evi |
|---|---|---|---|---:|---:|
| Grid A | MODIS date | Start date | End date | value | value |
| Grid B | MODIS date | Start date | End date | value | value |

The collection script can also keep:

- `grid_id`
- `ndvi_valid_pixel_count`
- `evi_valid_pixel_count`
- `dataset`

After temporal mapping, NDVI and EVI can later be added to the FireFusion 12-hour records using `.geo` and the relevant vegetation period.


## 12. Quality Control

MOD13Q1 includes quality information that can be used to avoid unreliable vegetation observations.

The initial collection uses `SummaryQA` to identify good-quality pixels.

For the first test:

`SummaryQA = 0`

will be used to keep good-quality observations.

The number of valid MODIS pixels contributing to each 5 km grid-cell value will also be recorded.

This helps identify cells where the final NDVI or EVI value is based on limited usable data.

`DetailedQA` can also be investigated later if more detailed quality filtering is needed.


## 13. Initial Recommendation

MODIS MOD13Q1 is recommended as the first vegetation dataset to test for FireFusion.

The initial features are:

- `ndvi`
- `evi`

It is a suitable candidate because it covers the required period and study area, provides useful vegetation information, is available through GEE, and can be processed into the FireFusion 5 km grid structure.

The main challenge is the difference in temporal resolution.

Because of this, the collection and matching method should first be tested on a smaller period before processing the complete 2018–2022 dataset.


## 14. Proposed Testing

Before full collection:

1. Test MOD13Q1 on a smaller period, such as January 2018.
2. Generate the FireFusion-style 5 km Victoria grid.
3. Collect NDVI and EVI from MOD13Q1.
4. Apply the scale factor and quality filtering.
5. Aggregate the valid 250 m MODIS pixels into each 5 km grid cell.
6. Compare the generated `.geo` geometries with the existing FireFusion data.
7. Check for missing NDVI and EVI values.
8. Check the NDVI and EVI ranges after scaling.
9. Review the valid-pixel counts.
10. Test the temporal mapping against the FireFusion 12-hour datetime structure.
11. Manually review several grid cells.
12. Only proceed with the full collection after the test results have been validated.


## 15. Next Steps

1. Run the vegetation collection script on a smaller test period.
2. Check NDVI and EVI quality and missing values.
3. Validate `.geo` against the existing FireFusion data.
4. Test the temporal mapping method.
5. Review whether mean aggregation is suitable.
6. Test combining the vegetation features with a sample of the current environmental dataset.
7. Review the results with the AI Modelling team.
8. Collect the full 2018–2022 vegetation dataset once the method has been confirmed.


## 16. References

Google Earth Engine. (n.d.). *MOD13Q1.061 Terra Vegetation Indices 16-Day Global 250m*. Earth Engine Data Catalog.  
https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MOD13Q1

NASA LP DAAC. (2021). *MODIS/Terra Vegetation Indices 16-Day L3 Global 250m SIN Grid V061 (MOD13Q1)*.  
https://doi.org/10.5067/MODIS/MOD13Q1.061