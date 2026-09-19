# IOD Processor Test Plan

## Status
Originally drafted ahead of the IOD processor being built (mirroring the
ENSO processor pattern). Ann has since pushed the real implementation
(`fetch_iod.py`, PR #235). This test suite has been updated to import and
run against the real code, and all 17 tests pass.

## Confirmed vs. Sprint 2 spec
Two real differences between the Sprint 2 plan and what was actually
built, worth the team's awareness (not bugs, just worth confirming these
were intentional design choices):

1. **No 3-month running mean.** The Sprint 2 plan described "NOAA data
   -> 3-month running mean -> phase classification." The real
   implementation classifies phase directly off the raw monthly DMI
   anomaly; there is no running-mean step anywhere in the pipeline.
2. **Not fixed "back to 1990."** The plan described monthly output back
   to 1990. The real implementation dynamically covers the latest N
   years (default 30) relative to whatever the newest data available is,
   so the start year shifts over time rather than being fixed at 1990.

## Confirmed real behaviour
- `assign_iod_phase(anom)` uses thresholds of +-0.40, returning the
  strings `'Positive IOD'`, `'Negative IOD'`, or `'Neutral'`.
- A NaN anomaly value maps to `'Neutral'` rather than raising or
  propagating NaN.
- Final output columns: `iod_id`, `time_id`, `datetime_record`,
  `record_year_month`, `dmi_anomaly`, `iod_phase`, `dmi_lag6m`,
  `original_source`.
- `dmi_lag6m` is a straightforward 6-row shift of `dmi_anomaly` after
  sorting chronologically.
- `validate_dataset(df)` asserts non-empty data, required columns
  present, and no nulls in `iod_id` / `time_id`.

## Gap worth flagging to Ann
`transform_and_standardise()` writes its output to disk internally
(`PROCESSED_DATA_DIR`, `DATASETS_IOD_DIR`) and assumes those folders
already exist. It does not call `create_directories()` itself, so
calling it in isolation (e.g. from a test, or from any future caller
that forgets the setup step) raises a confusing `OSError` rather than a
clear one. Tests work around this by redirecting those paths into a
temp folder; the real pipeline is unaffected since `main()` calls
`create_directories()` first, but it's worth a quick look.

## Confirmed edge case
An empty raw file (header row only, no data) does **not** raise an
error. It silently produces an empty, zero-row output and the function
returns successfully. This matches exactly the risk the original test
plan flagged, a silent empty-but-"successful" run is harder to catch
than a clear failure, especially once this runs unattended in an
automated pipeline. Worth a look before this connects to the daily
automation.

## Test coverage (test_fetch_iod.py, 17 tests, all passing)
1. Phase boundary tests, parametrised across the +-0.40 threshold and
   zero.
2. NaN handling.
3. Output column presence.
4. `time_id` uniqueness and format (10-digit YYYYMMDDHH).
5. Chronological sort with no duplicate timestamps.
6. `num_years` filtering (confirms it filters to the latest N years
   relative to the newest data, per the confirmed real behaviour above).
7. `dmi_lag6m` shift correctness.
8. `validate_dataset()` passing on valid data and raising on empty data
   or a missing column.
9. Empty raw file behaviour (documented as a known gap, see above).
