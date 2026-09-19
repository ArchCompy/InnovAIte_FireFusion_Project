import os
import json
import subprocess
import sys
from pathlib import Path
from dotenv import load_dotenv


load_dotenv()


GEOCODED_FILE = "facilities_at_risk_register_geocoded.json"


def run_script(script_name):
    print()
    print("=" * 60)
    print(f"Running: {script_name}")
    print("=" * 60)

    result = subprocess.run(
        [sys.executable, script_name]
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"{script_name} failed."
        )


def check_geocoding_status():
    if not Path(GEOCODED_FILE).exists():
        print("Geocoded output file was not created.")
        return False

    with open(
        GEOCODED_FILE,
        "r",
        encoding="utf-8"
    ) as file:
        data = json.load(file)

    total = len(data)

    processed = 0
    matched = 0
    not_matched = 0

    for record in data:
        status = record.get("geocode_status")

        if status == "matched":
            matched += 1
            processed += 1

        elif status == "not_matched":
            not_matched += 1
            processed += 1

    remaining = total - processed

    print()
    print("Geocoding summary:")
    print(f"Total facilities: {total}")
    print(f"Processed: {processed}")
    print(f"Matched: {matched}")
    print(f"Not matched: {not_matched}")
    print(f"Remaining: {remaining}")

    if remaining > 0:
        print()
        print(
            "Geocoding is incomplete. "
            "The pipeline will stop here."
        )
        print(
            "Run the pipeline again later to continue "
            "geocoding from the saved progress."
        )

        return False

    return True


def database_credentials_available():
    required_variables = [
        "DB_HOST",
        "DB_PORT",
        "DB_NAME",
        "DB_USER",
        "DB_PASSWORD"
    ]

    missing_variables = []

    for variable in required_variables:
        if not os.getenv(variable):
            missing_variables.append(variable)

    if missing_variables:
        print()
        print("Database credentials are not configured.")

        print(
            "Missing variables:",
            ", ".join(missing_variables)
        )

        return False

    return True


def main():
    print(
        "Starting Bushfire At-Risk Register "
        "automated pipeline."
    )

    # Step 1: Extract, merge, clean and validate data

    print()
    print("STEP 1: Extracting and cleaning BARR data")

    run_script(
        "bushfire_at_risk_register.py"
    )


    # Step 2: Geocode facilities

    print()
    print("STEP 2: Geocoding facilities")

    run_script(
        "get_geocode.py"
    )


    # Check whether geocoding fully completed

    geocoding_complete = check_geocoding_status()

    if not geocoding_complete:
        print()
        print("=" * 60)
        print(
            "Pipeline paused because "
            "geocoding is incomplete."
        )
        print("=" * 60)

        return


    # Step 3: Match facilities to location_registry

    print()
    print(
        "STEP 3: Matching facilities "
        "to location_registry"
    )

    if database_credentials_available():

        run_script(
            "match_facilities_to_location_id.py"
        )

    else:

        print()
        print(
            "Skipping location_registry matching."
        )

        print(
            "Configure Supabase/PostgreSQL "
            "credentials in .env to enable this step."
        )


    print()
    print("=" * 60)
    print(
        "Bushfire At-Risk Register "
        "pipeline finished."
    )
    print("=" * 60)


if __name__ == "__main__":
    main()