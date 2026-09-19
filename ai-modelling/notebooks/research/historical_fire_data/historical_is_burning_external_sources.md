# Historical `is_burning` External Data Source Exploration
## Overview
This document explores historical fire datasets available outside Google Earth Engine (GEE) that could potentially support the `is_burning` data currently used in FireFusion.
The purpose of this research is to identify external sources that could provide additional fire information rather than collecting another copy of data that FireFusion already has. 

For this investigation, I focused on datasets that:
- contain historical bushfire, active fire, fire event, or inceident information
- cover Victoria
- cover the FireFusion training period of 2018-2022
- conain useful spatial or temporal fire information
- come from reliable fovernment or scientific sources
- could potentially supplement or validate the FireFusion `is_burning` labels

None of the external datasets contains a field directly called `is_burning`.
Instead, each source is assessed based on the type of fire infromation it provides and whether that information could uspport or validate the current FireFusion fire labels.

## 1. Current FireFusion Context
FireFusion already has historical fire information from satelite detection and historical bushfire records. 

The existing satellite data includes observations from:
- VIIRS NOAA-20
- VIIRS S-NPP
- MODIS Aqua
- MODIS Terra

Because these satellite sources are already in FireFusion, an additional dataset would be more useful if it provides information that is different from or independent of the existing MODIS/VIIRS detections.
For this reason, higher priority is given to official Victorian fire records and mapped fire extents. 

## 2. Victoria Governtment Fire History Scar
### Description
The Fire History Scar dataset is provided by the Victoria Governtment Department of Energy, Environment and Climate Action (DEECA).
It contains mapped fire-scar boundaries across Victoria and represents the spatial extent of recorded fires. 

The official dataset description states: 
>"This layer represents the spatial extent of fires recorded since 1903 primarily on public land."

The dataset includes bushfires and planned burns. Major CFA fires occuring on private land have also been included since 2009.

### Dataset Information
|Property|Value|
|--|--|
|Provider|Victorian Government/DEECA|
|Data type|Fire-scar polygons|
|Geographic coverage|Victoria|
|Historical coverage|Recorded fires since 1903|
|Covers 2018-2022|Yes|
|Includes bushfires|Yes|
|Includes planned burns|Yes|
|Direct `is_burning`|No|
|Main value for FireFusion|Independent spatial fire evidence|

### Why It Could Be Useful
This is one of the most relevant external sources because it provides an official mapped record showing where fires have occurred.

The existing FireFusion satellite data provides evidence such as:
```text
Satellite detected active fire here.
```

The Fire History Scar provides a different type of evidence:
```text
Official fire history shows this area was affected by fire
```

This could potentially be used to validate whether locations identified through satellite observations fall within known historical fire areas.
The fire-scar polygons could also potentially be mapped to the FireFusion modelling grid.

### Advantages
- Official Victorian Goventment source
- Specifically covers Victoria
- Covers the complete FireFusion 2018-2022 period
- Provides spatial fire polygons rather than only satellite detection point
- Provides evidence that is different from MODIS/VIIRS active-fire detections
- Available as spatial data that could be processed against the FireFusion grid
  
### Limitations
- Does not provide a direct `is_burning` value
- Represents recorded fire extent rather than continuous active-fire observations
- Does not directly provide 12-hour fire-state information
- Includes planned burns as well as bushfire, so filtering may be required
- Fire extent alone does not show exactly when every location inside the final scar was actively burning.

### Initial Assessment
**High suitablity as an external supplementary source**

This appears to be the strongest external option because it provides official spatial fire records that are different from the existing satellite detections. 
It sould be most useful for validationg or strengthening the spatial fire information rather than directly creating a 12-hour `is-burnign` value.

## 3. Victoria Goventment Fire History and Severity
### Description
The Victoria Government also provides a broarder Fire History dataset containing historical fire extents and additional fire information. 

The official dataset description states:
>"Since 2006 fire severity data has been included in the Fire History dataset."

This makes the dataset useful because it may provide additional information beyond whether an area was affected by fire.

### Dataset Information
|Property|Value|
|--|--|
|Provider|Victorian Government/DEECA|
|Data type|Historical fire extend and severity|
|Geographic coverage|Victoria|
|Historical coverage|Since 1903|
|Covers 2018-2022|Yes for general fire history|
|Direct `is_burning`|No|
|Main value for FireFusion|Fire extend and severity validation|

### Why It Could Be Useful
The fire extend information could support the same type of spatial validation as the Fire History Scar. 

The additional severity information could also be useful later if FIreFusion investigates features such as:
```text
fire intensity
fire severity
burn impact
```

This makes the dataset potentially useful beyond the current `is_burning` task.

### Advantages
- Official Victorian Government source
- Covers Victoria
- Provides historical fire extent
- Includes severity information for some fires
- Could support both fire occurence and severity validation
- Provides spatial information that could potentially be mapped to the modelling grid

### Limitations
- Does not directly provide active-fire observations
- Does not provide a direct `is-burning` field
- Severity information is not complete for every historical fire
- The dataset documentation notes missing severity information for some periods and locations, including Gippland for 2018/2019 and 2019/2020
- Includes planned burns as well as bushfires
  
### Initial Assessment
**High suitability as a supporting validation datasets**

For the current `is_burning` tasj, the Fire History Scar still has slightly higher priority because the main requirement is historical fire occurrence rather than severity.
However, the severity information could become useful for future FireFusion modelling.

## 4. CFA Incident Responses
### Description
The Country Fire Authority (CFA) provides historical incident-response data through the Victorian Government data portal.
The information comes from the Fire and Incident Reporting System (FIRS)

The official dataset description includes:
>"type of incident: bushfire/grassfire, road rescue, residential fires"

The dataset also contains information relating to ignition, firefighting and incident charasteristics.
CFA incident records have been captured since 1994.

### Dataset Information
|Property|Value|
|--|--|
|Provider|Country Fire Authority|
|Data type|Incident records|
|Geographic coverage|Victoria|
|Historical coverage|Since 1994|
|Covers 2018-2022|Yes|
|Includes bushfires/grassfire incidents|Yes|
|Direct `is_burning`|No|
|Main value for FireFusion|Event-level validation|

### Why It Could Be Useful
CFA Incident Responses provide operational evidence that an actual fire incident occurred.

For example:
```text
Satellite fire detection + CFA bushfire incident = Additional evidence of a real fire event
```

This could potentially help validate known historical fire events.

### Advantages
- Official CFA source
- Covers the complete FireFusion period
- Contains actual operational incident records
- Includes bushfire and frassfire incident classifications
- Provides information independent from satellite fire detection
- Could support event-level validation

### Limitations
- Incident based rather than grid-based
- Does not provide a continuous spatial fire surface
- Deos not directly provide `is_burning`
- Would require additional spatial and temporal processing
- Less suitable than mapped fire polygons for assigning labels to individual FireFusion grid cells

### Initial Assessment
**Medium suitability"

CFA Incident Respoonses could be useful as supporting evidence for known fire events. 
However, it is less suitable than the Victoira Fire History datasets for directly supporting spatial `is_burning` labels.

## 5. NASA FIRMS Historical Active Fire Data
### Description
NASA's Fire Information for Resource Management System (FIRMS) provides historical active-fire and hotspot observations form MODIS and VIIRS satellites.

The FIRMS archive provides historical observations from:
```text
MODIS Collection 6.1: 2000 - present

VIIRS S-NPP 375 m: 2012 - present

VIIRS NOAA-20 375 m: 2018 - present
```

The FIRMS archive describes its historical data as:
>"active fire/hotspot infromation older than the last 7 days"

Historical observations can be downloaded in formats such as CSV, shapefile and JSON.

### Dataset Information
|Property|Value|
|--|--|
|Provider|NASA|
|Data type|Active fire / hotspot|
|Geographic coverage|Global|
|MODIS historical coverage|2000-present|
|VIIRS S-NPP coverage|2012-present|
|VIIRS NOAA-20 coverage|2018-present|
|Covers 2018-2022|Yes|
|Direct `is_burning`|No|
|Main value for FireFusion|Active-fire observations|

### Why It Could Be Useful
FIRMS provides active-fire observations, which are closely related to the idea of `is_burning`.

For example:
```text
Active fire detected >> Potential evidence for is_burning = 1
```

The observations also contain spatial and temporal information that could potentially be mapped to the FireFusion grid and tiemstamps.

### Main Issue for FireFusion
The main limitaiton is that FireFusion already uses MODIS and VIIRS satellite fire detections.

The existing FireFusion historical satellite data includes:
```text
VIIRS NOAA-20
VIIRS S-NPP
MODIS Aqua
MODIS Terra
```

Because FIRMS provides oberservations from these same satellite systems, using it as an additional souce may mostly provide the same underlying information that FireFusion already has.

### Advantages
- Active-fire information is closely related to `is_burning`
- Covers the full 2018-2022 period
- Provides useful spatial and temporal fire observations
- Historical data can be downloaded in common formats
- Could potentially help recollect missing satellite observations or extend the dataset
  
### Limitations
- Significant overlap with FireFusion's existing MODIS/VIIRS data
- Does not provide a genuinely independent source of fire evidence
- A missing satellite detection cannot automatically be inter[reted as `is_burning = 0`
- Satellite detection limitation still apply
- Spatial and temporal alignment would still be required

### Initial Assessment
**Technically suitable, but lower additional value for FireFusion**

If FireFusion did not already use MODIS and VIIRS observations, FIRMS would be one of the strongest options.
Since these satellite observations are already part of the current historical fire data, FIRMS shoul dnot be preioritiesed as the main additional source. 
It could still be useful if the project needs to recollect missing observations or extend the historical period. 

## 6. Comparison of External Sources
|Source|Data Type|Covers 2018-2022|Direct `is_burning`|Adds Different Information|Main Use|Priority|
|--|--|--|--|--|--|--|
| Victorian Fire History Scar | Fire extent polygons | Yes | No | Yes | Spatial fire validation | High |
| Victorian Fire History / Severity | Fire extent + severity | Yes* | No | Yes | Fire extent/severity validation | High |
| CFA Incident Responses | Incident records | Yes | No | Yes | Event validation | Medium |
| NASA FIRMS | Active fire detections | Yes | No | Limited | Active-fire observations | Medium/Low |

\*General fire-history coverage includes the required period, but severity information is not complete for every location and year.

## 7. How These Sources Could Support `is_burning`
None of the external sources provides a FIreFusion-ready `is_burning` field. 
Instead, each source provides a different type of evidence.

### Active Fire Evidence
NASA FIRMS can help answer:
```text
Was an active fire detected at this location and time?
```
This is closely related to `is_burning`, but FireFusion already contains similar MODIS/VIIRS infromation

### Fire Extent Evidence
The Victorian Fire History datasets can help answer: 
```text
Was this location inside the recorded extent of a fire?
```
This does not show exactly whether the location was actively burning at a paticular 12-hour timestamp.
However, it provides useful independent evidence that the area was affected by a recorded fire.

### Incident Evidence
CFA Indident Responses can help answer:
```text
Was a bushfire or grassfire incident officially recorded?
```
This could support event validation but is less suitable for assigning labels directly to the modelling grid.

## 8. Main Findings
The external-source investigation found that:
- none of the external sources provides a direct FireFusion-ready `is_burning` field
- several sources provide useful information that could support or validate the existing fire labels
- the Victorian Fire History datasets provide the strongest independent spatial fire information
- CFA Incident Responses could provide additional event-level validation
- NASA FIRMS provides active-fire information but overlaps strongly with MODIS/VIIRS observations already used by FireFusion
- an additional dataset is more useful if it adds a different type of fire evidence rather than repeating the same satellite observations
- the external datasets use different spatial and temporal structures, so they cannot be directly joined with the FireFusion modelling data
- further testing is needed before deciding whether any external source should be added to the historical fire pipeline

 This means there are useful extenal sources that could potentially supplement or validate the current FireFusion historical fire data, but none should be added without first comparing it agianst the existing dataset.

## 9. References
Country Fire Authority (CFA) n.d., *CFA Incident Responses*, Victorian Government DataVic, viewed 21 August 2026, <https://discover.data.vic.gov.au/dataset/cfa-incident-responses>.

Department of Energy, Environment and Climate Action (DEECA) n.d., *Fire History - Records of Fires across Victoria*, Victorian Government DataVic, viewed 21 August 2026, <https://discover.data.vic.gov.au/dataset/fire-history-records-of-fires-across-victoria>.

Department of Energy, Environment and Climate Action (DEECA) n.d., *Fire History Scar - Records of Fires across Victoria showing the fire scars*, Victorian Government DataVic, viewed 21 August 2026, <https://discover.data.vic.gov.au/dataset/fire-history-scar-records-of-fires-across-victoria-showing-the-fire-scars>.

National Aeronautics and Space Administration (NASA) n.d., *FIRMS Archive Download*, Fire Information for Resource Management System (FIRMS), viewed 21 August 2026, <https://firms.modaps.eosdis.nasa.gov/download/>.
