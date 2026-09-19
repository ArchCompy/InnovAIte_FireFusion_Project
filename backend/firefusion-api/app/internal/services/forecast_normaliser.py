class ForecastNormaliser:
    """
    Converts the AI Modelling response into the minimal GeoJSON
    format required by the Frontend Fire Risk Map.

    AI already returns risk_factor using the Frontend convention:
        1 = extreme
        5 = very low

    Backend therefore passes the value through without conversion.
    """

    def normalise(self, ai_response: dict) -> dict:
        if ai_response.get("type") != "FeatureCollection":
            raise ValueError(
                "AI response must be a GeoJSON FeatureCollection"
            )

        features = []

        for feature in ai_response.get("features", []):
            geometry = feature.get("geometry")
            properties = feature.get("properties", {})

            if geometry is None:
                raise ValueError(
                    "AI response feature is missing geometry"
                )

            risk_factors = properties.get("risk_factor")

            if not isinstance(risk_factors, list) or not risk_factors:
                raise ValueError(
                    "AI response feature is missing risk_factor"
                )

            # Current AI horizon is 1, so the first prediction
            # is used for the Fire Risk Map.
            risk_factor = int(risk_factors[0])

            if not 1 <= risk_factor <= 5:
                raise ValueError(
                    f"Invalid risk_factor returned by AI: {risk_factor}"
                )

            features.append(
                {
                    "type": "Feature",
                    "geometry": geometry,
                    "properties": {
                        "risk_factor": risk_factor
                    }
                }
            )

        return {
            "type": "FeatureCollection",
            "features": features
        }