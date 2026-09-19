"""Tests for the FireFusion misinformation demonstration interface."""

from __future__ import annotations

import json
from urllib.error import URLError
from unittest.mock import MagicMock, patch

import pytest

from demo.misinformation_app import (
    analyse_claim,
    build_request_payload,
    format_label,
    validate_claim,
)


def test_validate_claim_returns_cleaned_text() -> None:
    result = validate_claim("  An official bushfire warning is active.  ")

    assert result == "An official bushfire warning is active."


@pytest.mark.parametrize("claim", ["", "   ", None])
def test_validate_claim_rejects_empty_or_invalid_input(claim) -> None:
    with pytest.raises(
        ValueError,
        match="Please enter a claim",
    ):
        validate_claim(claim)


def test_validate_claim_rejects_very_short_text() -> None:
    with pytest.raises(
        ValueError,
        match="at least 10 characters",
    ):
        validate_claim("Fire")


def test_build_request_payload_matches_api_schema() -> None:
    payload = build_request_payload(
        "The highway has been closed because of a bushfire."
    )

    assert payload["id"].startswith("demo-")
    assert payload["author_name"] == "Demo user"
    assert payload["platform"] == "FireFusion demo"
    assert payload["content"] == (
        "The highway has been closed because of a bushfire."
    )
    assert payload["share_count"] == 0
    assert payload["post_url"] == ""


def test_format_label_creates_readable_text() -> None:
    assert format_label("non_misinformation") == "Non Misinformation"
    assert format_label("misinformation") == "Misinformation"


@patch("demo.misinformation_app.urlopen")
def test_analyse_claim_returns_successful_api_response(mock_urlopen) -> None:
    api_response = {
        "label": "misinformation",
        "confidence": 0.86,
        "probabilities": {
            "non_misinformation": 0.14,
            "misinformation": 0.86,
        },
        "risk_score": 0.86,
        "severity": "HIGH",
    }

    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(api_response).encode("utf-8")
    mock_urlopen.return_value.__enter__.return_value = mock_response

    result = analyse_claim(
        "An unverified post says the evacuation warning was cancelled."
    )

    assert result == api_response
    assert result["label"] == "misinformation"
    assert result["confidence"] == pytest.approx(0.86)
    mock_urlopen.assert_called_once()


@patch(
    "demo.misinformation_app.urlopen",
    side_effect=URLError("Connection refused"),
)
def test_analyse_claim_handles_unavailable_api(mock_urlopen) -> None:
    with pytest.raises(
        ConnectionError,
        match="Could not connect to the prediction API",
    ):
        analyse_claim(
            "An unverified bushfire evacuation claim was published."
        )


@patch("demo.misinformation_app.urlopen")
def test_analyse_claim_rejects_incomplete_api_response(mock_urlopen) -> None:
    incomplete_response = {
        "label": "misinformation",
        "confidence": 0.75,
    }

    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(
        incomplete_response
    ).encode("utf-8")
    mock_urlopen.return_value.__enter__.return_value = mock_response

    with pytest.raises(
        RuntimeError,
        match="missing required fields",
    ):
        analyse_claim(
            "An unverified bushfire warning was shared online."
        )
@patch("demo.misinformation_app.urlopen")
def test_analyse_claim_rejects_null_model_output(mock_urlopen) -> None:
    invalid_response = {
        "label": "non_misinformation",
        "confidence": None,
        "probabilities": {
            "non_misinformation": None,
            "misinformation": None,
        },
        "risk_score": None,
        "severity": "LOW",
    }

    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(
        invalid_response
    ).encode("utf-8")
    mock_urlopen.return_value.__enter__.return_value = mock_response

    with pytest.raises(RuntimeError, match="invalid confidence"):
        analyse_claim(
            "Authorities issued an emergency bushfire warning."
        )