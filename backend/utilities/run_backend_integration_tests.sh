#!/usr/bin/env bash
# Run the complete FireFusion Backend integration/resilience suite.
#
# Execute this script from the repository root after the Backend stack is up.
# Additional environment variables are documented in:
# backend/tests/integration/README.md

set -euo pipefail

echo "Running FireFusion Backend integration/resilience suite..."
python -m pytest backend/tests/integration -v
