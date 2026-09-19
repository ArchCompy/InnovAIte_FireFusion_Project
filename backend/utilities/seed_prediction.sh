#!/usr/bin/env bash
# Seed a sample bushfire prediction into the Redis cache.
#
# Without a cached prediction, GET /api/bushfire-forecast correctly returns an
# empty FeatureCollection, and the per-feature contract tests have nothing to
# validate (they skip). Run this to give the endpoint real data for testing and
# for demonstrating the Fire Risk Map.
#
# Usage, from the backend/ directory with the stack running:
#   ./utilities/seed_prediction.sh
#
# risk_factor uses the agreed Front-end scale: 1 = extreme through 5 = very low.
set -euo pipefail

PAYLOAD=$(cat <<'JSON'
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Polygon",
        "coordinates": [[
          [142.1560, -37.5600],
          [142.3200, -37.7400],
          [142.5100, -37.6500],
          [142.3800, -37.5100],
          [142.1560, -37.5600]
        ]]
      },
      "properties": { "risk_factor": 1, "fire_probability": 0.91 }
    },
    {
      "type": "Feature",
      "geometry": {
        "type": "Polygon",
        "coordinates": [[
          [142.7500, -37.8200],
          [142.6200, -38.0100],
          [142.9000, -38.0500],
          [142.9500, -37.8600],
          [142.7500, -37.8200]
        ]]
      },
      "properties": { "risk_factor": 3, "fire_probability": 0.42 }
    },
    {
      "type": "Feature",
      "geometry": {
        "type": "Polygon",
        "coordinates": [[
          [143.1000, -37.4000],
          [143.2500, -37.5500],
          [143.4000, -37.4200],
          [143.2800, -37.3000],
          [143.1000, -37.4000]
        ]]
      },
      "properties": { "risk_factor": 5, "fire_probability": 0.08 }
    }
  ]
}
JSON
)

echo "$PAYLOAD" | docker compose exec -T cache redis-cli -x SET predictions
echo "Seeded a 3-feature prediction (risk_factor 1, 3 and 5)."
echo
echo "Verify with:"
echo "  curl -s localhost:8080/api/bushfire-forecast"
echo
echo "Clear it again with:"
echo "  docker compose exec cache redis-cli DEL predictions"