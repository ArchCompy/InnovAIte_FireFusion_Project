import ee

# 1. CONFIGURATION

# Google Earth Engine project ID.
# Change this to the GEE project being used for FireFusion.
GEE_PROJECT = "YOUR_GEE_PROJECT_ID"

# Dataset used for vegetation indices.
MODIS_DATASET = "MODIS/061/MOD13Q1"

# Victoria boundary dataset.
BOUNDARY_DATASET = "FAO/GAUL/2015/level1"

# FireFusion historical training period.
START_YEAR = 2018
END_YEAR = 2022

# FireFusion grid size.
GRID_SCALE = 5000

# Projection used by the existing FireFusion grid workflow.
GRID_CRS = "EPSG:3857"

# MOD13Q1 native pixel resolution.
MODIS_SCALE = 250

# Export location in Google Drive.
DRIVE_FOLDER = "FireFusion_Vegetation_Features"

# Initial spatial aggregation method.
#
# Mean is used because multiple 250 m MODIS pixels
# can fall inside one FireFusion 5 km grid cell.
#
# Count is also saved for validation.
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
        ee.Initialize(project=GEE_PROJECT)

    except Exception:
        print("Earth Engine authentication required.")

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
    Load Victoria using the same boundary dataset used by
    the existing FireFusion GEE environmental workflows.
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
    Create the Victoria 5 km grid using the same approach
    as the existing FireFusion GEE datasets.

    Projection:
        EPSG:3857

    Grid size:
        5000 metres

    IMPORTANT:
        grid_id is included for reference only.

        `.geo` should be used when validating and matching
        this dataset with ERA5, ERA5-Land, or other FireFusion
        datasets.
    """

    grid_projection = (
        ee.Projection(
            GRID_CRS
        )
        .atScale(
            grid_scale
        )
    )

    # Create an image aligned to the 5 km projection.
    grid_image = (
        ee.Image.random(seed=0)
        .multiply(1000000)
        .toInt()
        .reproject(
            grid_projection
        )
    )

    # Convert each projected cell into a polygon.
    grid = grid_image.reduceToVectors(
        geometry=region.geometry(),
        scale=grid_scale,
        crs=GRID_CRS,
        geometryType="polygon",
        reducer=ee.Reducer.countEvery(),
        maxPixels=1e13
    )

    # Keep grid_id for reference.
    #
    # Do not rely on this field as the cross-dataset
    # matching key.
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


# 5. QUALITY MASK AND SCALE MODIS DATA

def prepare_modis_image(image):
    """
    Prepare MOD13Q1 NDVI and EVI.

    SummaryQA:
        0 = Good-quality observation

    Only good-quality pixels are used in the initial
    processing workflow.

    NDVI and EVI use a scale factor of 0.0001.
    """

    quality = image.select(
        "SummaryQA"
    )

    good_quality_mask = quality.eq(
        0
    )

    vegetation = (
        image
        .select(
            [
                "NDVI",
                "EVI"
            ]
        )
        .updateMask(
            good_quality_mask
        )
        .multiply(
            0.0001
        )
        .rename(
            [
                "ndvi",
                "evi"
            ]
        )
    )

    # Preserve the original MODIS timestamp.
    vegetation = vegetation.copyProperties(
        image,
        [
            "system:time_start"
        ]
    )

    return vegetation


# 6. AGGREGATE ONE MODIS IMAGE TO FIREFUSION GRID

def image_to_firefusion_grid(
    image,
    grid
):
    """
    Aggregate one MOD13Q1 observation to the FireFusion
    5 km grid.

    Multiple 250 m MODIS pixels within each FireFusion
    grid cell are summarised using the mean.

    Pixel counts are also saved for validation.
    """

    image = ee.Image(
        image
    )

    observation_date = ee.Date(
        image.get(
            "system:time_start"
        )
    )

    # MOD13Q1 represents a 16-day vegetation period.
    valid_until = observation_date.advance(
        16,
        "day"
    )

    reduced = image.reduceRegions(
        collection=grid,
        reducer=SPATIAL_REDUCER,
        scale=MODIS_SCALE,
        tileScale=4
    )

    def format_feature(feature):

        feature = ee.Feature(
            feature
        )

        return feature.set({

            # Keep grid_id for reference.
            "grid_id": feature.get(
                "grid_id"
            ),

            # Native MODIS observation date.
            "datetime": observation_date.format(
                "YYYY-MM-dd'T'00:00:00"
            ),

            # Used later when mapping vegetation values
            # to FireFusion 12-hour observations.
            "valid_from": observation_date.format(
                "YYYY-MM-dd'T'00:00:00"
            ),

            "valid_until": valid_until.format(
                "YYYY-MM-dd'T'00:00:00"
            ),

            # Aggregated vegetation features.
            "ndvi": feature.get(
                "ndvi_mean"
            ),

            "evi": feature.get(
                "evi_mean"
            ),

            # Number of valid MODIS pixels contributing
            # to each grid-cell mean.
            "ndvi_valid_pixel_count": feature.get(
                "ndvi_count"
            ),

            "evi_valid_pixel_count": feature.get(
                "evi_count"
            ),

            "dataset": "MODIS_MOD13Q1_V6.1"
        })

    return reduced.map(
        format_feature
    )


# 7. BUILD ONE YEAR OF VEGETATION DATA

def build_year_collection(
    year,
    grid
):
    """
    Collect all MOD13Q1 observations for one year and
    aggregate them to the FireFusion 5 km grid.
    """

    start_date = ee.Date.fromYMD(
        year,
        1,
        1
    )

    end_date = start_date.advance(
        1,
        "year"
    )

    collection = (
        ee.ImageCollection(
            MODIS_DATASET
        )
        .filterDate(
            start_date,
            end_date
        )
        .filterBounds(
            grid.geometry()
        )
        .map(
            prepare_modis_image
        )
        .sort(
            "system:time_start"
        )
    )

    image_count = collection.size().getInfo()

    print(
        f"{year}: found "
        f"{image_count} MOD13Q1 observations."
    )

    image_list = collection.toList(
        collection.size()
    )

    def accumulate(
        index,
        accumulated
    ):

        index = ee.Number(
            index
        ).toInt()

        image = ee.Image(
            image_list.get(
                index
            )
        )

        grid_features = image_to_firefusion_grid(
            image,
            grid
        )

        return (
            ee.FeatureCollection(
                accumulated
            )
            .merge(
                grid_features
            )
        )

    indices = ee.List.sequence(
        0,
        collection.size().subtract(
            1
        )
    )

    vegetation_features = ee.FeatureCollection(
        indices.iterate(
            accumulate,
            ee.FeatureCollection([])
        )
    )

    return vegetation_features


# 8. EXPORT ONE YEAR TO GOOGLE DRIVE

def export_year(
    year,
    vegetation_features
):
    """
    Export one year of vegetation features as CSV.

    `.geo` is included so that the output can later be
    validated against and matched with the existing
    FireFusion datasets.
    """

    description = (
        f"FireFusion_MOD13Q1_NDVI_EVI_{year}"
    )

    filename = (
        f"FireFusion_Vegetation_"
        f"NDVI_EVI_5km_{year}"
    )

    task = ee.batch.Export.table.toDrive(
        collection=vegetation_features,
        description=description,
        folder=DRIVE_FOLDER,
        fileNamePrefix=filename,
        fileFormat="CSV",

        selectors=[
            "grid_id",
            ".geo",
            "datetime",
            "valid_from",
            "valid_until",
            "ndvi",
            "evi",
            "ndvi_valid_pixel_count",
            "evi_valid_pixel_count",
            "dataset"
        ]
    )

    task.start()

    print(
        f"{year}: export task started."
    )

    print(
        f"Task ID: {task.id}"
    )


# 9. MAIN COLLECTION WORKFLOW

def main():

    print(
        "\nFireFusion Vegetation Feature Collection"
    )

    print(
        "Dataset: MODIS MOD13Q1 V6.1"
    )

    print(
        f"Period: {START_YEAR}-{END_YEAR}"
    )

    print(
        f"Grid: {GRID_SCALE / 1000:.0f} km"
    )

    print(
        f"Projection: {GRID_CRS}\n"
    )

    # 1. Initialise Earth Engine.
    initialise_earth_engine()

    # 2. Load Victoria.
    victoria = load_victoria_boundary()

    # 3. Generate the FireFusion-style 5 km grid.
    grid = create_victoria_grid(
        victoria
    )

    # 4. Check the number of generated grid cells.
    grid_count = grid.size().getInfo()

    print(
        f"Generated grid cells: "
        f"{grid_count}\n"
    )

    # 5. Process one year at a time.
    for year in range(
        START_YEAR,
        END_YEAR + 1
    ):

        print(
            f"Processing {year}..."
        )

        vegetation_features = (
            build_year_collection(
                year,
                grid
            )
        )

        # 6. Submit yearly export.
        export_year(
            year,
            vegetation_features
        )

    print(
        "\nAll export tasks have been submitted."
    )

    print(
        "Check the Earth Engine Tasks page "
        "or Google Drive for progress."
    )


# 10. RUN SCRIPT

if __name__ == "__main__":
    main()