import ee

# 1. CONFIGURATION

# Google Earth Engine project ID.
# Change this to the GEE project being used for FireFusion.
GEE_PROJECT = "YOUR_GEE_PROJECT_ID"

# Victoria boundary dataset.
BOUNDARY_DATASET = "FAO/GAUL/2015/level1"

# Geoscience Australia DEM-S dataset.
DEM_DATASET = "AU/GA/DEM_1SEC/v10/DEM-S"

# FireFusion grid size.
GRID_SCALE = 5000

# Projection used by the existing FireFusion grid workflow.
GRID_CRS = "EPSG:3857"

# Approximate native DEM-S resolution.
DEM_SCALE = 30

# Google Drive export folder.
DRIVE_FOLDER = "FireFusion_Terrain_Features"

# Export file name.
EXPORT_FILENAME = (
    "FireFusion_Terrain_"
    "Elevation_Slope_5km"
)

# Mean + pixel count are used for the initial aggregation.
SPATIAL_REDUCER = (
    ee.Reducer.mean()
    .combine(
        reducer2=ee.Reducer.count(),
        sharedInputs=True
    )
)


# 2. INITIALISE GOOGLE EARTH ENGINE

def initialise_earth_engine():
    """
    Initialise the Google Earth Engine Python API.
    """

    try:
        ee.Initialize(
            project=GEE_PROJECT
        )

    except Exception:
        print(
            "Earth Engine authentication required."
        )

        ee.Authenticate()

        ee.Initialize(
            project=GEE_PROJECT
        )

    print(
        "Google Earth Engine initialised successfully."
    )


# 3. LOAD VICTORIA BOUNDARY

def load_victoria_boundary():
    """
    Load Victoria using the same boundary source
    used by the existing FireFusion workflows.
    """

    states = ee.FeatureCollection(
        BOUNDARY_DATASET
    )

    victoria = (
        states
        .filter(
            ee.Filter.eq(
                "ADM0_NAME",
                "Australia"
            )
        )
        .filter(
            ee.Filter.eq(
                "ADM1_NAME",
                "Victoria"
            )
        )
    )

    print(
        "Victoria boundary loaded."
    )

    return victoria


# 4. CREATE FIREFUSION 5 KM GRID

def create_victoria_grid(
    region,
    grid_scale=GRID_SCALE
):
    """
    Create the Victoria 5 km grid using the same
    FireFusion grid-generation method.

    Projection:
        EPSG:3857

    Grid size:
        5000 metres

    IMPORTANT:
        grid_id is included for reference only.

        `.geo` should be used when validating and
        matching terrain data with the existing
        FireFusion datasets.
    """

    grid_projection = (
        ee.Projection(
            GRID_CRS
        )
        .atScale(
            grid_scale
        )
    )

    grid_image = (
        ee.Image.random(
            seed=0
        )
        .multiply(
            1000000
        )
        .toInt()
        .reproject(
            grid_projection
        )
    )

    grid = grid_image.reduceToVectors(
        geometry=region.geometry(),
        scale=grid_scale,
        crs=GRID_CRS,
        geometryType="polygon",
        reducer=ee.Reducer.countEvery(),
        maxPixels=1e13
    )

    grid = grid.map(
        lambda feature:
        feature.set(
            "grid_id",
            feature.id()
        )
    )

    print(
        "Victoria 5 km grid created."
    )

    return grid


# 5. LOAD DEM-S

def load_dem():
    """
    Load the DEM-S elevation dataset.

    The DEM provides the elevation surface used
    for both elevation and slope features.
    """

    dem = ee.Image(
        DEM_DATASET
    )

    print(
        "DEM-S loaded."
    )

    return dem


# 6. PREPARE ELEVATION

def prepare_elevation(
    dem
):
    """
    Select and rename the elevation band.
    """

    elevation = (
        dem
        .select(
            "elevation"
        )
        .rename(
            "elevation"
        )
    )

    return elevation


# 7. DERIVE SLOPE

def derive_slope(
    elevation
):
    """
    Derive slope from the elevation surface.

    Earth Engine returns slope in degrees.
    """

    slope = (
        ee.Terrain.slope(
            elevation
        )
        .rename(
            "slope"
        )
    )

    return slope


# 8. CREATE TERRAIN IMAGE

def create_terrain_image():
    """
    Create one image containing:
        - elevation
        - slope
    """

    dem = load_dem()

    elevation = prepare_elevation(
        dem
    )

    slope = derive_slope(
        elevation
    )

    terrain = (
        elevation
        .addBands(
            slope
        )
    )

    print(
        "Elevation and slope prepared."
    )

    return terrain


# 9. AGGREGATE TERRAIN TO FIREFUSION GRID

def aggregate_terrain_to_grid(
    terrain,
    grid
):
    """
    Aggregate the high-resolution terrain data
    to each FireFusion 5 km grid cell.

    Initial features:
        - mean elevation
        - mean slope

    Pixel counts are also retained for validation.
    """

    reduced = terrain.reduceRegions(
        collection=grid,
        reducer=SPATIAL_REDUCER,
        scale=DEM_SCALE,
        tileScale=4
    )

    def format_feature(
        feature
    ):

        feature = ee.Feature(
            feature
        )

        return feature.set({

            # Keep grid_id for reference.
            "grid_id": feature.get(
                "grid_id"
            ),

            # Mean elevation inside the 5 km cell.
            "elevation": feature.get(
                "elevation_mean"
            ),

            # Mean slope inside the 5 km cell.
            "slope": feature.get(
                "slope_mean"
            ),

            # Number of DEM pixels contributing
            # to each aggregated value.
            "elevation_valid_pixel_count":
                feature.get(
                    "elevation_count"
                ),

            "slope_valid_pixel_count":
                feature.get(
                    "slope_count"
                ),

            "dataset": "GA_DEM-S"
        })

    terrain_features = reduced.map(
        format_feature
    )

    return terrain_features


# 10. BASIC VALIDATION

def validate_terrain_output(
    terrain_features
):
    """
    Run basic checks on the aggregated terrain output.

    These checks are intended to confirm that the
    generated dataset is reasonable before export.
    """

    total_cells = (
        terrain_features
        .size()
        .getInfo()
    )

    missing_elevation = (
        terrain_features
        .filter(
            ee.Filter.eq(
                "elevation",
                None
            )
        )
        .size()
        .getInfo()
    )

    missing_slope = (
        terrain_features
        .filter(
            ee.Filter.eq(
                "slope",
                None
            )
        )
        .size()
        .getInfo()
    )

    elevation_min = (
        terrain_features
        .aggregate_min(
            "elevation"
        )
        .getInfo()
    )

    elevation_max = (
        terrain_features
        .aggregate_max(
            "elevation"
        )
        .getInfo()
    )

    slope_min = (
        terrain_features
        .aggregate_min(
            "slope"
        )
        .getInfo()
    )

    slope_max = (
        terrain_features
        .aggregate_max(
            "slope"
        )
        .getInfo()
    )

    print(
        "\nTerrain validation"
    )

    print(
        f"Total grid cells: "
        f"{total_cells}"
    )

    print(
        f"Missing elevation values: "
        f"{missing_elevation}"
    )

    print(
        f"Missing slope values: "
        f"{missing_slope}"
    )

    print(
        f"Elevation range: "
        f"{elevation_min} to "
        f"{elevation_max}"
    )

    print(
        f"Slope range: "
        f"{slope_min} to "
        f"{slope_max}"
    )


# 11. EXPORT TERRAIN FEATURES

def export_terrain_features(
    terrain_features
):
    """
    Export terrain features as CSV.

    `.geo` is included so the terrain dataset can later
    be validated and matched against the existing
    FireFusion environmental datasets.
    """

    description = (
        "FireFusion_Terrain_"
        "Elevation_Slope_5km"
    )

    task = ee.batch.Export.table.toDrive(
        collection=terrain_features,
        description=description,
        folder=DRIVE_FOLDER,
        fileNamePrefix=EXPORT_FILENAME,
        fileFormat="CSV",

        selectors=[
            "grid_id",
            ".geo",
            "elevation",
            "slope",
            "elevation_valid_pixel_count",
            "slope_valid_pixel_count",
            "dataset"
        ]
    )

    task.start()

    print(
        "\nTerrain export task started."
    )

    print(
        f"Task ID: {task.id}"
    )


# 12. MAIN WORKFLOW

def main():

    print(
        "\nFireFusion Terrain Feature Collection"
    )

    print(
        "Dataset: Geoscience Australia DEM-S"
    )

    print(
        f"Grid: {GRID_SCALE / 1000:.0f} km"
    )

    print(
        f"Projection: {GRID_CRS}"
    )

    print(
        f"DEM processing scale: "
        f"{DEM_SCALE} m\n"
    )

    # 1. Initialise Earth Engine.
    initialise_earth_engine()

    # 2. Load Victoria boundary.
    victoria = (
        load_victoria_boundary()
    )

    # 3. Create the FireFusion-style 5 km grid.
    grid = create_victoria_grid(
        victoria
    )

    # 4. Check the generated grid count.
    grid_count = (
        grid
        .size()
        .getInfo()
    )

    print(
        f"Generated grid cells: "
        f"{grid_count}"
    )

    # 5. Create elevation and slope image.
    terrain = (
        create_terrain_image()
    )

    # 6. Aggregate terrain to the FireFusion grid.
    terrain_features = (
        aggregate_terrain_to_grid(
            terrain,
            grid
        )
    )

    # 7. Run basic validation.
    validate_terrain_output(
        terrain_features
    )

    # 8. Export the terrain dataset.
    export_terrain_features(
        terrain_features
    )

    print(
        "\nTerrain processing complete."
    )

    print(
        "Check the Earth Engine Tasks page "
        "or Google Drive for export progress."
    )


# 13. RUN SCRIPT

if __name__ == "__main__":
    main()