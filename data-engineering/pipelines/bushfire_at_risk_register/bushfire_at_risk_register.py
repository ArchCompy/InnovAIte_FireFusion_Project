import urllib.request
import urllib.error
import json

# URL of the dataset

url_1 = 'https://discover.data.vic.gov.au/api/3/action/datastore_search?resource_id=a927e847-5818-43e2-8fe6-ad7e469fabd1'

url_2 = 'https://discover.data.vic.gov.au/api/3/action/datastore_search?resource_id=39f89a56-af38-49cf-98d3-26eca92c4466'


# Fetch all records using pagination

def fetch_all_records(base_url):

    records = []
    offset = 0
    limit = 1000

    while True:

        url = f"{base_url}&limit={limit}&offset={offset}"

        try:
            fileobj = urllib.request.urlopen(url, timeout=30)

        except urllib.error.URLError as error:
            print("Failed to download Bushfire At-Risk Register data.")
            print("Error:", error)
            raise

        # Convert the response to a JSON object

        data = json.load(fileobj)

        # Check whether the API request was successful

        if not data.get("success"):
            raise RuntimeError("API request was unsuccessful.")

        batch = data["result"]["records"]

        records.extend(batch)

        print(
            f"Downloaded {len(batch)} records "
            f"from offset {offset}"
        )

        # Stop when the final page contains less than the limit

        if len(batch) < limit:
            break

        offset += limit

    return records


# Download records from both datasets

records_1 = fetch_all_records(url_1)

records_2 = fetch_all_records(url_2)


# Combine the two datasets into one

records = records_1 + records_2


print(
    "Total records before duplicate check:",
    len(records)
)


# Remove duplicate facility records

unique_records = []

seen = set()

for record in records:

    key = (
        record.get("Facility name"),
        record.get("Facility address"),
        record.get("Town/Suburb")
    )

    if key not in seen:

        seen.add(key)

        unique_records.append(record)


records = unique_records


print(
    "Total records after duplicate check:",
    len(records)
)


# Validate important fields

required_fields = [
    "Facility name",
    "Facility address",
    "Town/Suburb",
    "LGA"
]


missing_required_fields = 0


for record in records:

    for field in required_fields:

        if not record.get(field):

            missing_required_fields += 1

            break


print(
    "Records with missing required fields:",
    missing_required_fields
)


# Standardise text fields

for record in records:

    if record.get("Facility name"):

        record["Facility name"] = (
            record["Facility name"].strip()
        )

    if record.get("Facility address"):

        record["Facility address"] = (
            record["Facility address"].strip()
        )

    if record.get("Town/Suburb"):

        record["Town/Suburb"] = (
            record["Town/Suburb"].strip()
        )

    if record.get("LGA"):

        record["LGA"] = (
            record["LGA"].strip()
        )


# Ensure merged records have continuous _id values

for i, record in enumerate(records, start=1):

    record["_id"] = i


# Save the data to a json file

with open(
    "bushfire_at_risk_register.json",
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        records,
        f,
        indent=4,
        ensure_ascii=False
    )


print(
    "Bushfire At-Risk Register data saved successfully."
)


# Print the 1200th record to verify the data

# print(records[1199])