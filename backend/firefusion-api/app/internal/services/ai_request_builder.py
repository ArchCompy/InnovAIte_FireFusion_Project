from collections import defaultdict
from datetime import datetime


# AI Modelling's current working request uses 30 historical
# timesteps per grid cell.
#
# The request structure can remain the same if the model's
# feature list expands in a future sprint.
DEFAULT_INPUT_STEPS = 30


class AIRequestBuilder:

    def build(
        self,
        source_records: list[dict],
        feature_names: list[str],
        feature_mapping: dict[str, str],
        input_steps: int = DEFAULT_INPUT_STEPS
    ) -> dict:
        """
        Convert prepared Data Engineering records into the GeoJSON
        request structure expected by:

            POST /predict/bushfire/forecast

        feature_mapping defines which Data Engineering field supplies
        each AI Modelling feature.

        Missing values or incomplete spatial mappings are rejected
        rather than replaced with assumptions or placeholder values.
        """

        if not source_records:
            raise ValueError(
                "No Data Engineering source records were supplied"
            )

        # Group observations by DE location so each grid location
        # becomes one Feature in the AI request.
        grouped: dict[int, list[dict]] = defaultdict(list)

        for record in source_records:
            grouped[record["location_id"]].append(record)

        features = []

        for location_id, records in grouped.items():

            # DE has confirmed datetime_record as the canonical
            # timestamp obtained through time_registry.
            #
            # AI Modelling requires observations in chronological order.
            records.sort(
                key=lambda item: item["datetime_record"]
            )

            # Current AI contract requires the most recent
            # 30 observations for each grid cell.
            records = records[-input_steps:]

            if len(records) < input_steps:
                # Do not construct an AI feature if this location
                # does not contain enough history.
                continue

            observations = []
            timestamps = []

            for record in records:

                row = []

                # Construct each observation in the exact order specified
                # by feature_names.
                for ai_feature in feature_names:

                    de_field = feature_mapping.get(ai_feature)

                    if de_field is None:
                        raise ValueError(
                            f"No Data Engineering mapping has been "
                            f"defined for AI feature '{ai_feature}'"
                        )

                    # DE has confirmed the seven ERA5 columns, but the
                    # current database values may still be null.
                    #
                    # AI Modelling requires complete feature vectors, so
                    # Backend must reject incomplete rows.
                    value = record.get(de_field)

                    if value is None:
                        raise ValueError(
                            f"Missing DE value '{de_field}' for "
                            f"AI feature '{ai_feature}'"
                        )

                    row.append(float(value))

                observations.append(row)

                timestamp = record["datetime_record"]

                # Convert database/Python datetime objects into the
                # ISO timestamp representation used by the AI request.
                if isinstance(timestamp, datetime):
                    timestamp = timestamp.isoformat()

                timestamps.append(timestamp)

            latest = records[-1]

            # Build the polygon around the canonical DE grid location.
            #
            # This geometry remains temporary until the exact shared
            # DE/AI spatial grid definition is fully agreed.
            geometry = self._build_grid_polygon(
                latitude=float(latest["grid_latitude"]),
                longitude=float(latest["grid_longitude"])
            )

            # AI Modelling requires integer grid indices.
            #
            # DE has confirmed grid_row and grid_col are intended to
            # come from location_registry, but they are not yet populated.
            # Backend must not invent these values.
            grid_row = latest.get("grid_row")
            grid_col = latest.get("grid_col")

            if grid_row is None or grid_col is None:
                raise ValueError(
                    f"Missing confirmed AI grid mapping for location_id "
                    f"{location_id}. Expected integer grid_row and grid_col "
                    f"from the Data Engineering integration."
                )

            # Add the completed grid cell only after its time-series,
            # feature values and spatial indices have been validated.
            features.append(
                {
                    "type": "Feature",
                    "geometry": geometry,
                    "properties": {
                        "id": str(location_id),
                        "observations": observations,
                        "timestamps": timestamps,
                        "grid_row": int(grid_row),
                        "grid_col": int(grid_col)
                    }
                }
            )

        if not features:
            raise ValueError(
                "No locations contained enough observations to build "
                f"the required {input_steps}-step AI request"
            )

        # feature_names explicitly defines the meaning and order
        # of every value in each observations array.
        return {
            "type": "FeatureCollection",
            "features": features,
            "feature_names": feature_names,
            "schema_version": "1.0"
        }

    @staticmethod
    def _build_grid_polygon(
        latitude: float,
        longitude: float
    ) -> dict:
        """
        Build a temporary polygon around a Data Engineering grid centre.

        The current assumption uses an approximately 0.05-degree grid.
        This should be replaced or confirmed once the canonical shared
        DE -> AI spatial grid definition is finalised.
        """

        half = 0.025

        return {
            "type": "Polygon",
            "coordinates": [[
                [longitude - half, latitude - half],
                [longitude + half, latitude - half],
                [longitude + half, latitude + half],
                [longitude - half, latitude + half],
                [longitude - half, latitude - half]
            ]]
        }