<#
.SYNOPSIS
Runs the FireFusion Backend integration/resilience pytest suite.

.DESCRIPTION
Run this script from the repository root after the Backend stack is running.

By default, tests that stop/start Docker dependencies are skipped.
Use -Destructive only against a local development stack.

See backend/tests/integration/README.md for environment variables and setup.
#>

param(
    [switch]$Destructive
)

$ErrorActionPreference = "Stop"

if ($Destructive) {
    # Enables tests such as the Redis stop/start recovery test.
    $env:RUN_DESTRUCTIVE_INTEGRATION = "1"
}

Write-Host "Running FireFusion Backend integration/resilience suite..."
python -m pytest backend/tests/integration -v

# Return pytest's result code to the calling shell/CI process.
exit $LASTEXITCODE
