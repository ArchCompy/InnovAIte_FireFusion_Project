# FireFusion Spatial Schema & Grid Logic

## 1. Purpose

The purpose of this document is to define the spatial schema and grid-alignment logic currently used in the FireFusion Data Engineering layer. FireFusion combines data from multiple sources such as NASA FIRMS, Open-Meteo, ELVIS and other bushfire-related datasets. These sources may provide slightly different latitude and longitude values for locations that are geographically close to each other.

To support reliable integration, FireFusion uses a common spatial grid and a shared `location_id`. The GridSnapper utility validates incoming coordinates, rounds valid coordinates to the nearest configured grid point, checks the central `location_registry` table, and returns a common identifier that can be used across datasets.

This approach allows FireFusion to align fire, weather, vegetation, topography and infrastructure data while preserving the original source coordinates for traceability.

---

## 2. Current Spatial Architecture

FireFusion follows a spatial-temporal hub-and-spoke database design.

The main spatial hub is the `location_registry` table. Other datasets reference this table through `location_id` rather than depending only on their raw latitude and longitude values.

Current spatially linked tables include:

- `weather_observation`
- `fire_incident_record`
- `vegetation_condition`
- `topography_profile`
- `infrastructure_asset`

Each observation table is expected to retain the original coordinates supplied by the source while using `location_id` as the common spatial join key.

This architecture supports the main FireFusion requirement of combining observations from different systems at a shared location.

---

## 3. Location Registry Schema

The current Supabase `location_registry` table contains the following fields:

| Field | Type | Purpose |
|---|---|---|
| `location_id` | integer | Primary key used as the common spatial identifier |
| `grid_latitude` | float8 | Latitude of the snapped grid point |
| `grid_longitude` | float8 | Longitude of the snapped grid point |
| `region_name` | varchar | Human-readable region associated with the location |
| `grid_row` | int4 | Optional grid row index |
| `grid_col` | int4 | Optional grid column index |

### Current implementation note

The current `GridSnapper` implementation directly uses:

- `location_id`
- `grid_latitude`
- `grid_longitude`
- `region_name`

The `grid_row` and `grid_col` fields exist in the database, but they are not currently populated or used by the GridSnapper utility.

---

## 4. Spatial Coverage

The current GridSnapper validates coordinates using a rectangular Victoria bounding box.

```text
Latitude minimum:  -39.2
Latitude maximum:  -34.0
Longitude minimum: 140.96
Longitude maximum: 150.0
```

A coordinate is considered valid only when both latitude and longitude fall within these configured bounds.

### Current validation rule

```text
-39.2 <= latitude <= -34.0
140.96 <= longitude <= 150.0
```

Coordinates outside these bounds are rejected and the GridSnapper returns `None`.

---

## 5. Coordinate Reference System

The existing FireFusion GridSnapper and database schema use latitude and longitude in decimal-degree format. However, the current code and architecture documentation do not explicitly declare a Coordinate Reference System identifier.

For this reason, this specification does not claim an official CRS that has not yet been confirmed in the project documentation.

### Recommendation

The project should formally confirm and document the CRS used by all upstream and downstream spatial datasets. If the project confirms that all geographic coordinates follow WGS84, then the standard should be explicitly documented as:

```text
WGS84 / EPSG:4326
```

Until this is confirmed, FireFusion should continue to treat the current coordinate format as decimal-degree latitude and longitude and avoid introducing transformations based on an assumed CRS.

---

## 6. Grid Resolution

The current GridSnapper implementation defines:

```python
GRID_SIZE = 0.1
```

This means that coordinates are snapped to the nearest `0.1` degree grid point.

The existing implementation describes `0.1` degree as approximately 11 km. More precisely, a 0.1-degree latitude interval is approximately 11 km in the north-south direction, while the physical east-west distance represented by 0.1 degree longitude changes with latitude.

Therefore, the FireFusion grid should be understood as a geographic degree-based grid rather than a fixed 11 km by 11 km square grid.

---

## 7. Grid Snapping Logic

The current GridSnapper rounds valid coordinates using the following logic:

```python
snapped_lat = round(round(latitude / GRID_SIZE) * GRID_SIZE, 4)
snapped_lon = round(round(longitude / GRID_SIZE) * GRID_SIZE, 4)
```

With `GRID_SIZE = 0.1`, a coordinate such as:

```text
Latitude:  -37.8147
Longitude: 145.0892
```

is snapped to:

```text
Latitude:  -37.8
Longitude: 145.1
```

Two nearby source coordinates that snap to the same grid point should resolve to the same `location_id`.

---

## 8. End-to-End GridSnapper Process

The current spatial processing workflow is:

```text
Raw latitude and longitude
          |
          v
Check for null coordinates
          |
          v
Validate against Victoria bounds
          |
          v
Snap to nearest 0.1 degree grid point
          |
          v
Query location_registry using snapped latitude and longitude
          |
          v
Does the grid point already exist?
       /       \
     Yes        No
      |          |
      v          v
Return       Insert new
existing     location_registry row
location_id  and return new location_id
```

### Detailed steps

#### Step 1 - Input

The minimum required input is:

```text
latitude
longitude
```

#### Step 2 - Validation

The GridSnapper checks:

- latitude is not `None`
- longitude is not `None`
- latitude is inside the configured Victoria bounds
- longitude is inside the configured Victoria bounds

If the validation fails, the method returns `None`.

#### Step 3 - Snap to Grid

Valid coordinates are rounded to the nearest `0.1` degree grid point.

#### Step 4 - Registry Lookup

The utility queries:

```sql
SELECT location_id
FROM location_registry
WHERE grid_latitude = %s
  AND grid_longitude = %s;
```

If the grid point already exists, its existing `location_id` is returned.

#### Step 5 - Create New Spatial Record

If the snapped grid location does not already exist, the utility creates a new registry record using:

```sql
INSERT INTO location_registry
    (grid_latitude, grid_longitude, region_name)
VALUES
    (%s, %s, %s)
RETURNING location_id;
```

The current code inserts `"Victoria"` as the default `region_name` for newly created locations.

---

## 9. Input and Output Contract

### Input

```text
latitude: numeric decimal-degree value
longitude: numeric decimal-degree value
```

### Main output

```text
location_id: integer
```

### Invalid output

```text
None
```

`None` is returned when a coordinate is missing or falls outside the configured Victoria bounds.

---

## 10. Raw Coordinate Preservation

A key FireFusion data-engineering principle is that raw source coordinates must not be discarded.

The GridSnapper generates a shared `location_id` for joining datasets, but it is not intended to replace the raw location values.

Observation tables should retain:

```text
original_latitude
original_longitude
```

This supports:

- data lineage
- auditing
- debugging
- future reprocessing
- comparison between raw and snapped locations

The snapped location and original source location therefore serve different purposes and should both be preserved.

---

## 11. Validation Rules

The following rules describe the current expected behaviour.

### Required rules

1. Latitude must not be null.
2. Longitude must not be null.
3. Coordinates must fall inside the configured Victoria bounding box.
4. Valid coordinates must be snapped to the configured grid size.
5. Existing grid points should reuse their existing `location_id`.
6. New grid points may create a new `location_registry` record.
7. Original source coordinates must be preserved in downstream observation tables.
8. Pipelines must check for `None` before inserting spatially invalid records.

### Recommended additional rules

1. Latitude and longitude should be validated as numeric before snapping.
2. The database should prevent duplicate rows for the same `grid_latitude` and `grid_longitude` combination.
3. Pipeline logs should record rejected coordinates for review instead of silently discarding them.
4. The project should explicitly document its CRS.

---

## 12. Edge-Case Handling

### Missing coordinates

If latitude or longitude is missing, the GridSnapper returns `None`.

### Coordinate outside Victoria bounds

Coordinates outside the configured bounding box are rejected.

For example, the tested Sydney coordinate:

```text
(-33.8688, 151.2093)
```

is rejected because it falls outside the configured Victoria bounds.

### Nearby coordinates

Two coordinates that differ slightly can still resolve to the same grid location.

The existing test demonstrates that:

```text
(-37.8147, 145.0892)
(-37.8199, 145.0901)
```

both return the same `location_id` because they snap to the same grid point.

### Multiple records in one grid cell

Multiple records snapping to one grid cell must not automatically be treated as duplicates. They may represent:

- different timestamps
- different data sources
- different observation types
- different measurements

The common `location_id` is used only for spatial alignment.

### New grid point

If a valid snapped coordinate is not already present in the registry, a new row is created.

### Existing grid point

If the snapped latitude and longitude already exist, the current `location_id` is returned instead of creating another spatial record.

---

## 13. Integration with FireFusion Observation Tables

The `location_registry` is intended to act as the common spatial reference for FireFusion data.

A typical pipeline should follow this pattern:

```python
from grid_snapper.grid_snapper import GridSnapper

snapper = GridSnapper()

for record in data:
    location_id = snapper.get_location_id(
        latitude=record["latitude"],
        longitude=record["longitude"]
    )

    if location_id is None:
        continue

    insert_to_database(
        location_id=location_id,
        original_latitude=record["latitude"],
        original_longitude=record["longitude"]
    )

snapper.close()
```

This allows datasets from different sources to share one spatial identifier while keeping their original values.

---

## 14. Integration with Victoria_Geo

The cleaned `Victoria_Geo` dataset can support FireFusion as a reference dataset for checking the consistency of suburb, postcode and coordinate information before records are integrated into the wider system.

A suitable workflow is:

```text
Victoria_Geo or other raw spatial source
            |
            v
Coordinate/data-quality validation
            |
            v
Retain original coordinate values
            |
            v
Pass valid coordinates to GridSnapper
            |
            v
Receive common location_id
            |
            v
Store location_id with downstream dataset
```

The Victoria_Geo dataset should not replace the GridSnapper. Instead, it can complement the GridSnapper by improving source-level coordinate quality before grid alignment.

---

## 15. Current Technical Limitations

### 15.1 Rectangular Victoria boundary

The current validation uses a rectangular bounding box rather than the true Victoria state boundary polygon.

This means a coordinate could theoretically pass the current bounds check while still falling outside the actual Victorian border.

### 15.2 Degree-based grid

The current grid uses degrees rather than a projected coordinate system measured directly in metres or kilometres.

As a result, the physical east-west size of a grid cell varies with latitude.

### 15.3 CRS is not explicitly declared

The project uses decimal-degree latitude and longitude values, but the official CRS is not explicitly declared in the current GridSnapper code or architecture documentation.

### 15.4 `grid_row` and `grid_col` are not used

The Supabase schema contains `grid_row` and `grid_col`, but the current GridSnapper does not generate or populate them.

### 15.5 Region naming

When a new location is created, the GridSnapper currently uses `"Victoria"` as the `region_name`. This does not provide a more detailed regional classification such as Gippsland, Grampians or Ballarat.

### 15.6 Database uniqueness is not enforced in the current utility

The application performs a lookup before creating a new location. However, the project should confirm that the database itself also enforces uniqueness for snapped grid coordinates to avoid duplicate records during concurrent inserts.

---

## 16. Recommended Improvements

The following improvements are recommended for future FireFusion development.

### High priority

1. **Formally document the CRS** used across all spatial data sources and database tables.
2. **Add a unique database constraint** for `(grid_latitude, grid_longitude)` if one is not already present.
3. **Add automated unit tests** for snapping, null coordinates, boundary values and duplicate grid lookups.
4. **Introduce structured logging** instead of using only `print()` messages.

### Medium priority

5. Replace rectangular boundary validation with an accurate Victoria polygon check if finer geographic validation is required.
6. Define whether `grid_row` and `grid_col` will be used, and populate them consistently if required.
7. Document and standardise how `region_name` is assigned.
8. Add batch-processing support for large datasets to reduce repeated database queries.

### Future consideration

9. Evaluate whether the current 0.1-degree resolution remains suitable for all AI Modelling and backend requirements.
10. Consider a projected spatial reference system in future if precise kilometre-based grid dimensions become necessary.

---

## 17. Test Evidence from Existing GridSnapper

The existing GridSnapper tutorial and implementation demonstrate the following behaviours:

| Test | Expected behaviour |
|---|---|
| Import GridSnapper | Utility imports successfully |
| Initialise GridSnapper | Connects successfully to Supabase |
| Valid Victorian coordinate | Returns a valid `location_id` |
| Two nearby coordinates | Return the same `location_id` when snapped to the same grid point |
| Coordinate outside Victoria | Returns `None` |
| Null coordinate | Returns `None` |

These tests provide evidence that the current utility already supports the main spatial-alignment workflow required by the project.

---

## 18. Spatial Schema Summary

The current FireFusion spatial design can be summarised as follows:

```text
Spatial coverage      : Victoria bounding box
Grid resolution       : 0.1 degrees
Coordinate format     : Decimal-degree latitude / longitude
Spatial hub           : location_registry
Primary spatial key   : location_id
Grid fields           : grid_latitude, grid_longitude
Raw coordinate policy : Preserve original values
Out-of-bounds policy  : Reject and return None
Grid creation policy  : Reuse existing location_id or create new registry row
```

The design provides a simple and practical mechanism for aligning different FireFusion data sources. The main next step is to strengthen the specification by formally confirming the CRS, enforcing database-level uniqueness, and improving geographic boundary validation where required.

---

## 19. References to Existing FireFusion Project Assets

This specification is based on the current project implementation and documentation available in the FireFusion repository and database:

- `data-engineering/grid_snapper/grid_snapper.py`
- `data-engineering/grid_snapper/README.md`
- `data-engineering/grid_snapper/docs/GRID_SNAPPER_TUTORIAL.md`
- `data-engineering/architecture/database_architecture.md`
- Supabase `location_registry` table
- Existing GridSnapper test outputs

---

## 20. Review Status

**Document status:** Draft for technical review  
**Area:** Data Engineering - Spatial Schema & Grid Logic  
**Project:** FireFusion  

### Items to confirm during review

- [ ] Confirm the official CRS used by FireFusion.
- [ ] Confirm whether `(grid_latitude, grid_longitude)` has a database unique constraint.
- [ ] Confirm whether `grid_row` and `grid_col` will be used in future development.
- [ ] Confirm whether the existing `0.1` degree resolution remains suitable for AI Modelling and backend requirements.
- [ ] Confirm whether `region_name` should remain a general label or be populated with a more specific Victorian region.

