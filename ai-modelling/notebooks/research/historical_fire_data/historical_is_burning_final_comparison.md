# Historical `is_burning` Dataset Final Comparison

## Overview

This document brings together the findings from the GEE and external historical fire dataset investigations.
The purpose is to compare the most relevant options against the current FireFusion historical fire data and identify which sources are worth testing further.
The focus is on datasets that provide additional information rather than repeating fire data that FireFusion already has.

## 1. Current FireFusion Data
FireFusion currently uses historical fire information from MODIS and VIIRS satellite detections, including:
- VIIRS NOAA-20
- VIIRS S-NPP
- MODIS Aqua
- MODIS Terra

These observations provide active-fire information and are already used to support the current `is_burning` data. 
Because of this, another MODIS or VIIRS active-fire source may provide limited additional value. Sources that provide differtent fire information, such as burned area or official fire extents, are more useful to investigate.

## 2. Final Comparison
|Source|Data Type|Covers 2018-2022|Adds Different Information|Main Use|Priority|
|--|--|--|--|--|--|
| MCD64A1 | Burned area + burn date | Yes | Yes | Burned-area validation | High |
| VNP64A1 | Burned area + burn date | Yes | Yes | Burned-area validation | High |
| MOD14A1 / MYD14A1 | Active fire | Yes | Limited | Active-fire validation | Medium/Low |
| Victorian Fire History Scar | Official fire extent | Yes | Yes | Spatial fire validation | High |
| Victorian Fire History / Severity | Fire extent + severity | Yes* | Yes | Fire extent/severity validation | Medium/High |
| CFA Incident Responses | Incident records | Yes | Yes | Event-level validation | Medium |
| NASA FIRMS | Active fire | Yes | Limited | Active-fire data / gap filling | Low |

\*Fire History covers the required period, but severity information is not complete for every location and year.

## 3. Main Findings
The comparison shows that:

- FireFusion already has strong active-fire information from MODIS and VIIRS
- MOD14A1, MYD14A1 and NASA FIRMS may overlap with data already available in FireFusion
- MCD64A1 and VNP64A1 provide additional burned-area and burn-date information
- Victorian Fire History Scar provides official mapped fire extents and is a useful independent source for spatial validation
- CFA Incident Responses could provide additional event-level evidence but are less suitable for direct grid-level labelling
- None of the additional datasets provides a FireFusion-ready 12-hour `is_burning` field
- Any selected dataset would still need spatial and temporal alignment before it could be combined with the modelling data

## 4. Recommended Options
Based on the comparison, the strongest options for further testing are:

### Victorian Fire History Scar

This is the strongest external option because it provides official mapped fire extents across Victoria.

It could be used to check whether FireFusion fire locations fall within officially recorded fire areas.

### MCD64A1

This is the strongest GEE option because it provides 500 m burned-area information together with `BurnDate`.

It could provide additional evidence about where and approximately when burning occurred.

### VNP64A1

VNP64A1 is another useful burned-area option and could be tested alongside MCD64A1 to compare their fire coverage.

MOD14A1, MYD14A1, and NASA FIRMS should have lower priority because they are based on MODIS/VIIRS active-fire observations that FireFusion already uses.

## 6. Recommendation and Next Steps

The current FireFusion active-fire data should remain the main source for `is_burning`.
The additional datasets should first be treated as **supplementary or validation sources**, rather than direct replacements.

The recommended next steps are:

1. Test Victorian Fire History Scar against the current FireFusion historical fire data.
2. Test MCD64A1 for a small period in Victoria and inspect its `BurnDate` information.
3. Test VNP64A1 over the same period for comparison.
4. Check whether these sources identify useful fire information that is missing from the current dataset.
5. Determine how the selected data should be mapped to the 5 km grid and 12-hour timestamps.
6. Based on the results, decide whether the additional data should be used for validation, additional fire labels, or other modelling features.

At this stage, the strongest combination to investigate further is:

```text
Current MODIS / VIIRS active-fire data
                +
Victorian Fire History Scar
                +
MCD64A1 or VNP64A1
```

This would combine active-fire observations, official mapped fire extents, and burned-area information without relying on another copy of the same satellite detections.
