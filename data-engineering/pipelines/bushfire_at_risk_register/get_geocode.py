import json
from pathlib import Path
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
from geopy.exc import GeocoderRateLimited


INPUT_FILE = "bushfire_at_risk_register.json"
OUTPUT_FILE = "facilities_at_risk_register_geocoded.json"
CACHE_FILE = "geocode_cache.json"


def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)

    if isinstance(data, dict):
        data = [data]

    return data


def save_json(data, path):
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)


def load_cache():
    if Path(CACHE_FILE).exists():
        with open(CACHE_FILE, "r", encoding="utf-8") as file:
            return json.load(file)

    return {}


def save_cache(cache):
    with open(CACHE_FILE, "w", encoding="utf-8") as file:
        json.dump(cache, file, indent=4, ensure_ascii=False)


def build_address_queries(item):
    address = item.get("Facility address", "")
    suburb = item.get("Town/Suburb", "")
    lga = item.get("LGA", "")
    facility_name = item.get("Facility name", "")

    queries = [
        f"{address}, {suburb}, VIC, Australia",
        f"{address}, {suburb}, Victoria, Australia",
        f"{facility_name}, {suburb}, VIC, Australia",
        f"{address}, {suburb}, {lga}, Victoria, Australia"
    ]

    # Remove empty or invalid queries
    return [query for query in queries if query.strip()]


def already_geocoded(item):
    return (
        item.get("latitude") is not None
        and item.get("longitude") is not None
        and item.get("geocode_status") == "matched"
    )


def geocode_facilities():
    # If output file already exists, continue from it
    if Path(OUTPUT_FILE).exists():
        print(f"Continuing from existing file: {OUTPUT_FILE}")
        data = load_json(OUTPUT_FILE)
    else:
        print(f"Starting from input file: {INPUT_FILE}")
        data = load_json(INPUT_FILE)

    cache = load_cache()

    geolocator = Nominatim(
        user_agent="firefusion_facility_geocoder_ha_nguyen",
        timeout=10
    )

    geocode = RateLimiter(
        geolocator.geocode,
        min_delay_seconds=2.5,
        max_retries=0,
        swallow_exceptions=False
    )

    total = len(data)

    for index, item in enumerate(data, start=1):
        facility_name = item.get("Facility name", "Unknown facility")

        # Skip rows already successfully geocoded
        if already_geocoded(item):
            print(f"{index}/{total} - {facility_name} - already matched")
            continue

        queries = build_address_queries(item)

        found = None
        used_query = None

        for query in queries:
            # Check cache first
            if query in cache:
                cached_result = cache[query]

                if cached_result:
                    found = cached_result
                    used_query = query
                    print(f"Cache matched: {query}")
                    break
                else:
                    print(f"Cache not matched: {query}")
                    continue

            print(f"Searching: {query}")

            try:
                location = geocode(
                    query,
                    country_codes="au",
                    addressdetails=True,
                    timeout=10
                )

            except GeocoderRateLimited:
                print("Nominatim rate limit reached.")
                print("Saving current progress and stopping geocoding.")

                save_json(data, OUTPUT_FILE)
                save_cache(cache)

                print(f"Progress saved to: {OUTPUT_FILE}")
                print("Run the script again later to continue.")

                return

            except Exception as e:
                print(f"Failed query: {query}")
                print(f"Error: {e}")
                location = None

            if location:
                found = {
                    "latitude": location.latitude,
                    "longitude": location.longitude,
                    "display_name": location.address
                }

                cache[query] = found
                save_cache(cache)

                used_query = query
                break
            else:
                cache[query] = None
                save_cache(cache)

        if found:
            item["latitude"] = found["latitude"]
            item["longitude"] = found["longitude"]
            item["geocode_status"] = "matched"
            item["geocode_source"] = "OpenStreetMap Nominatim"
            item["geocode_query"] = used_query
            item["geocode_display_name"] = found["display_name"]
        else:
            item["latitude"] = None
            item["longitude"] = None
            item["geocode_status"] = "not_matched"
            item["geocode_source"] = "OpenStreetMap Nominatim"
            item["geocode_query"] = queries[0] if queries else None
            item["geocode_display_name"] = None

        # Save progress after every row
        save_json(data, OUTPUT_FILE)

        print(f"{index}/{total} - {facility_name} - {item['geocode_status']}")

    save_json(data, OUTPUT_FILE)

    print("Finished geocoding.")
    print(f"Output saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    geocode_facilities()