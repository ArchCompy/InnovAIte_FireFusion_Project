"""
Pytest suite for the IOD (Indian Ocean Dipole) processor.

Updated against the real implementation in fetch_iod.py (PR #235, Ann).
Loads the module directly by file path so it works regardless of whether
the pipelines/ folders are set up as proper Python packages.

Two things worth flagging to the team, confirmed while writing these
tests against the real code (see iod_test_plan.md "Confirmed vs Sprint 2
spec" section for detail):
  1. There is no 3-month running mean step; phase is classified directly
     off the raw monthly DMI anomaly.
  2. Output is not fixed "back to 1990"; it dynamically covers the latest
     N years (default 30) relative to whatever the newest data is.
"""

import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest

# Load fetch_iod.py directly by path, sibling to this test file.
_MODULE_PATH = Path(__file__).resolve().parent / "fetch_iod.py"
if not _MODULE_PATH.exists():
    pytest.skip(
        "fetch_iod.py not present on this branch yet (Ann's PR #235 "
        "hasn't merged into main). These tests activate automatically "
        "once both land together.",
        allow_module_level=True,
    )
_spec = importlib.util.spec_from_file_location("fetch_iod", _MODULE_PATH)
iod_module = importlib.util.module_from_spec(_spec)
sys.modules["fetch_iod"] = iod_module
_spec.loader.exec_module(iod_module)


def _write_raw_fixture(path, rows):
    """Write a minimal raw CSV matching what fetch_raw_data() produces:
    columns Year, Month_Name, dmi_anomaly (west/east not needed for
    transform_and_standardise, which only reads these three)."""
    df = pd.DataFrame(rows, columns=["Year", "Month_Name", "dmi_anomaly"])
    df.to_csv(path, index=False)
    return path


@pytest.fixture(autouse=True)
def _redirect_output_dirs(tmp_path, monkeypatch):
    """transform_and_standardise() writes its output to disk internally
    (PROCESSED_DATA_DIR and DATASETS_IOD_DIR) and assumes those folders
    already exist -- it does not call create_directories() itself. That
    is a real fragility worth flagging to the team: the function isn't
    safely callable in isolation without that setup step first, which a
    unit test naturally exposes. Redirect both paths into a temp folder
    for every test so we're testing the transform logic itself, not
    tripping over that missing directory-creation step."""
    processed_dir = tmp_path / "processed_out"
    iod_dir = tmp_path / "iod_out"
    processed_dir.mkdir()
    iod_dir.mkdir()
    monkeypatch.setattr(iod_module, "PROCESSED_DATA_DIR", str(processed_dir))
    monkeypatch.setattr(iod_module, "DATASETS_IOD_DIR", str(iod_dir))


@pytest.mark.parametrize(
    "value, expected_phase",
    [
        (0.40, "Positive IOD"),
        (0.41, "Positive IOD"),
        (0.39, "Neutral"),
        (-0.40, "Negative IOD"),
        (-0.41, "Negative IOD"),
        (-0.39, "Neutral"),
        (0.0, "Neutral"),
    ],
)
def test_assign_iod_phase_boundaries(value, expected_phase):
    assert iod_module.assign_iod_phase(value) == expected_phase


def test_assign_iod_phase_nan_returns_neutral():
    assert iod_module.assign_iod_phase(float("nan")) == "Neutral"


def test_output_has_expected_columns(tmp_path):
    raw = _write_raw_fixture(
        tmp_path / "raw.csv",
        [[2020, "Jan", 0.1], [2020, "Feb", 0.2], [2020, "Mar", 0.3]],
    )
    df = iod_module.transform_and_standardise(str(raw), num_years=30)
    expected_columns = {
        "iod_id", "time_id", "datetime_record", "record_year_month",
        "dmi_anomaly", "iod_phase", "dmi_lag6m", "original_source",
    }
    assert expected_columns.issubset(set(df.columns))


def test_time_id_is_unique_and_formatted(tmp_path):
    raw = _write_raw_fixture(
        tmp_path / "raw.csv",
        [[2020, "Jan", 0.1], [2020, "Feb", 0.2], [2020, "Mar", 0.3]],
    )
    df = iod_module.transform_and_standardise(str(raw), num_years=30)
    assert df["time_id"].is_unique
    assert df["time_id"].astype(str).str.match(r"^\d{10}$").all()


def test_output_sorted_chronologically_no_duplicates(tmp_path):
    raw = _write_raw_fixture(
        tmp_path / "raw.csv",
        [[2020, "Mar", 0.3], [2020, "Jan", 0.1], [2020, "Feb", 0.2]],
    )
    df = iod_module.transform_and_standardise(str(raw), num_years=30)
    assert df["datetime_record"].is_monotonic_increasing
    assert not df["datetime_record"].duplicated().any()


def test_num_years_filters_to_latest_n_years(tmp_path):
    rows = [[y, "Jan", 0.1] for y in range(1990, 2021)]
    raw = _write_raw_fixture(tmp_path / "raw.csv", rows)
    df = iod_module.transform_and_standardise(str(raw), num_years=5)
    assert df["datetime_record"].dt.year.min() == 2016
    assert df["datetime_record"].dt.year.max() == 2020


def test_dmi_lag6m_shifts_by_six_rows(tmp_path):
    rows = [[2020, m, i * 0.1] for i, m in enumerate(
        ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug"], start=1
    )]
    raw = _write_raw_fixture(tmp_path / "raw.csv", rows)
    df = iod_module.transform_and_standardise(str(raw), num_years=30)
    df = df.sort_values("datetime_record").reset_index(drop=True)
    assert df.loc[6, "dmi_lag6m"] == pytest.approx(df.loc[0, "dmi_anomaly"])


def test_validate_dataset_passes_on_valid_data(tmp_path):
    raw = _write_raw_fixture(
        tmp_path / "raw.csv",
        [[2020, "Jan", 0.1], [2020, "Feb", 0.2], [2020, "Mar", 0.3]],
    )
    df = iod_module.transform_and_standardise(str(raw), num_years=30)
    iod_module.validate_dataset(df)


def test_validate_dataset_fails_on_empty_dataframe():
    empty_df = pd.DataFrame(columns=[
        "iod_id", "time_id", "datetime_record", "record_year_month",
        "dmi_anomaly", "iod_phase", "dmi_lag6m", "original_source",
    ])
    with pytest.raises(AssertionError):
        iod_module.validate_dataset(empty_df)


def test_validate_dataset_fails_on_missing_column(tmp_path):
    raw = _write_raw_fixture(
        tmp_path / "raw.csv",
        [[2020, "Jan", 0.1], [2020, "Feb", 0.2]],
    )
    df = iod_module.transform_and_standardise(str(raw), num_years=30)
    df_missing_col = df.drop(columns=["iod_phase"])
    with pytest.raises(AssertionError):
        iod_module.validate_dataset(df_missing_col)


def test_empty_raw_file_produces_empty_output_silently(tmp_path):
    empty_file = tmp_path / "empty.csv"
    empty_file.write_text("Year,Month_Name,dmi_anomaly\n")
    df = iod_module.transform_and_standardise(str(empty_file), num_years=30)
    assert len(df) == 0