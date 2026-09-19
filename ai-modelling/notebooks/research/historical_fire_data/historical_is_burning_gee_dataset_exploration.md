# GEE Historical Fire Dataset Exploration for `is_burning`

## Overview
This document explores additional historical fire datasets available through Google Earth Engine (GEE) that could potentially support the `is_burning` data used in FireFusion.

The main purpose of the research is to check whether GEE has an appropriate dataset that could provide additional historical fire information for Victoria during 2018-2022.

For this investigation, I looked for datasets that:
- are available through Google Earth Engine
- contain historical active fire or burned area information
- cover Victoria, Australia
- cover the FireFusion training period of 2018-2022
- contain spatial and temporal information that could potentially be aligned with the FireFusion modelling data.

At this stage, I am exploring possible options rather than selecting a replacement for the current historical fire dataset.

## 1. What FireFusion Needs
FireFusion uses historical fire information alongside environmental datasets such as ERA5 and ERA5-Land.

The environmental data is currently structured around:
- Victoria as the study area
- a 5km modelling grid
- 12-hour time intervals
- historical coverage from 2018-2022

The historical fire data uses `is_burning` to represent fire activity.

Because of this, any additional fire dataset needs to provide enough spatial and temporal information to eventually align with this structure. The dataset does not need to already contain an `is_burning` column. Information such as active fire detections or burn dates could potentially be used to support or derive the fire label. 

## 2. Types of Fire Data Found in GEE
From my investigation, I found two main types of fire data that could be useful.

### Active Fire Data
Active fire products identify locations where a satellite detected an active fire or thermal anomaly at the time of observation.

This is the closest type of data to the idea of:
```text
is_burning = 1
```

However, no detection should not automatically mean:
```text
is_burning = 0
```

A satellite may not have observed the location at the time, or a fire may not have been detected.

### Burned Area Data
Burned area products identify locations that were affected by fire and can also provide an estimated date of burning. 

This gives useful information about **where a fire occurred and approximately when it occurred**, but it is different from detecting an actively burning fire. 

For this reason, burned area data could potentially support the historical fire labels, but it should not automatically be treated as a direct `is_burning` value.

## 3. Candidate GEE Datasets
I identified five main datasets that could be relevant to FireFusion.

### 3.1 MCD64A1 MODIS Burned Area
**GEE Dataset**
```javascript
ee.ImageCollection("MODIS/061/MCD64A1")
```

MCD64A1 is a NASA MODIS burned area dataset. It provides global burned area information together with an estimated burn date.

|Property|Value|
|--|--|
|Provider|NASA|
|Data type|Burned area|
|Spatial resolution|500 m|
|Temporal structure|Monthly product with burn date|
|Historical coverage|2000-present|
|Covers 2018-2022|Yes|

One of the most relevant bands is: 
```text
BurnDate
```

`BurnDate` gives the approximate day of the year when a pixel was identified as burned.

For example:
```text
BurnDate = 0
> pixel was not identified as burned

BurnDate = 15
> pixel was identified as burned around day 15 of the year
```

#### Why it could be useful
MCD64A1 could provide additional information about whether an area was affected by fire around a particular date. It also provides explicit unburned values and additional quality information.

#### Main limitation
MCD64A1 identifies **burned area**, not an active fire at a specific time. This means `BurnDate` would need to be interpreted carefully before using it to support an `is_burning` label.

#### Initial assessment
MCD64A1 looks like one of the stronger options for providing additional historical burned area information because it covers the full FireFusion period and provides both spatial and burn-date information.

### 3.2 VNP64A1 VIIRS Burned Area
**GEE Dataset**
```javascript
ee.ImageCollection("NASA/VIIRS/002/VNP64A1")
```

VNP64A1 is a NASA VIIRS burned area dataset. Similar to MCD64A1, it identifies burned locations and provides information about the approximate date of burning.

|Property|Value|
|--|--|
|Provider|NASA|
|Data type|Burned area|
|Spatial resolution|500 m|
|Temporal structure|Monthly product with burn date|
|Covers 2018-2022|Yes|

A relevant band is: 
```text
Burn_Date
```

which provides the ordinal day when a pixel day when a pixel was identified as burned. 

#### Why it could be useful
VNP64A1 could provide another source of historical burned area information covering the full FireFusion period. It could also be tested alongside MCD64A1 to see whether one provides better or more useful fire coverage for Victoria.

#### Main limitation
Like MCD64A1, it represents burned area rather than an active fire state.

#### Initial assessment
VNP64A1 is another strong candidate and would be useful to compare directly with MCD64A1 before selecting a burned area source. 

### 3.3 MOD14A1 MODIS Terra Active Fire
**GEE Dataset**
```javascript
ee.ImageCollection("MODIS/061/MOD14A1")
```
MOD14A1 provides MODIS Terra thermal anomaly and active fire observations

|Property|Value|
|--|--|
|Provider|NASA|
|Data type|Active fire / thermal anomaly|
|Spatial resolution|1 km|
|Temporal structure|Daily|
|Covers 2018-2022|Yes|

#### Why it could be useful
Unlike the burned area products, MOD14A1 detects active fires. This makes it more directly related to `is_burning` because it provides evidence that fire was active around the time of the satellite observation.

#### Main limitation
FireFusion already uses satellite fire information, including MODIS detections. Because of this, MOD14A1 may overlap with information already available in the current historical fire dataset. 

#### Initial Assessment
MOD14A1 is relevant to the `is_burning` problem, but I think it should first be compared with the current FireFusion satellite detections to determine whether it actually adds new information.

### 3.4 MYD14A1 MODIS Aqua Active Fire
**GEE Dataset**
```javascript
ee.ImageCollection("MODIS/061/MYD14A1")
```
MYD14A1 provides MODIS Aqua active fire and thermal anomaly observations.

|Property|Value|
|--|--|
|Provider|NASA|
|Data type|Active fire / thermal anomaly|
|Spatial resolution|1 km|
|Temporal structure|Daily|
|Covers 2018-2022|Yes|

MYD14A1 is similar to MOD14A1, but the observations come from the Aqua satellite rather than Terra. 

#### Why it could be useful
Terra and Aqua observe the Earth at different times, so using both products could potentially provide additional active fire observations.

#### Main limitation
Like MOD14A1, this dataset may overlap with the MODIS fire detections already used by FireFusion. 

#### Initial Assessment
MYD14A1 could potentially be useful together with MOD14A1, but I would first check how much additional information they provide compared with the existing historical fire data.

### 3.5 FireCCI51 Burned Area
**GEE Dataset**
```javascript
ee.ImageCollection("ESA/CCI/Fire_CCI/5_1")
```

FireCCI51 is an ESA Climate Change Initiative burned area dataset. 

|Property|Value|
|--|--|
|Provider|ESA CCI|
|Data type|Burned area|
|Spatial resolution|Approximately 250 m|
|Temporal structure|Monthly with burn date|
|Covers 2018-2020|Yes|
|Covers 2021-2022|No|

The main advantage of FireCCI51 is its finer spatial resolution and the availability of burn-date and confidence information. However, it does not cover the complete FireFusion period.

### Initial assessment
I would not prioritise FireCCI51 as the main additional dataset because it does not cover the full 2018-2022 period. It could still be useful as an additional comparison or validation source for 2018-2020.

## 4. Comparison of the Options
Based on the datasets I investigated: 
|Dataset|Data Type|Resolution|Temporal Information|Covers 2018-2022|Initial Priority|
|--|--|--|--|--|--|
|MCD64A1|Burned area|500 m|Monthly + burn day|Yes|High|
|VNP64A1|Burned area|500 m|Monthly + burn day|Yes|High|
|MOD14A1|Active fire|1 km|Daily|Yes|Medium/High|
|MYD14A1|Active fire|1 km|Daily|Yes|Medium/High|
|FireCCI51|Burned area|~250 m|Monthly + burn day|No|Low|

MCD64A1 and VNP64A1 look the most useful for investigating **additional burned area information**. MOD14A1 and MYD14A1 are more directly related to active fire, but they need to be checked against the existing FireFusion satellite data because they may contain overlapping information.

## 5. Compatibility with FireFusion
Even though several appropriate datasets are available through GEE, they cannot be directly joined with the current FireFusion modelling data without additional processing. There are two main differences that need to be considered. 

### Spatial Alignment
The FireFusion modelling data uses a 5 km grid, while the candidate fire datasets have finer native resolutions: 
```text
FireFusion modelling grid: 5 km

MCD64A1: 500 m
VNP64A1: 500 m
MOD14A1: 1 km
MYD14A1: 1 km
FireCCI51: ~250 m
```

This means multiple fire pixels could fall inside a single FireFusion grid cell. Because the datasets use different grid structures, their own `grid_id` values should not be assumed to represent matching locations. The fire observations would need to be mapped using their geographic location and the agreed FireFusion reference grid.

### Temporal Aligment
The FireFusion environmental data uses 12-hour intervals: 
```text
2018-01-01 00:00
2018-01-01 12:00
2018-01-02 00:00
2018-01-02 12:00
```

The candidate datasets use different temporal structures:
```text
MOD14A1/MYD14A1: daily active fire observations

MCD64A1/VNP64A1: monthly products with estimated burn day
```

A temporal mapping rule would therefore need to be defined before these observations could be used alongside the 12-hour environmental data.

## 6. Main Findings
From this investigation, I found that GEE does not have several datasets that could potentially provide additional historical fire information for FireFusion.

The main findings are: 
- MCD64A1, VNP64A1, MOD14A1, and MYD14A1 cover the full 2018-2022 period.
- None of the investigated datasets directly provides a FireFusion-ready `is_burning` column.
- MCD64A1 and VNP64A1 provide useful burned area and burn-date information
- MOD14A1 and MYD14A1 provide active fire information, which is more directly related to `is_burning`
- The active fire products may overlap with satellite fire detections that FireFusion already uses.
- FireCII51 does not cover the full required period.
- Any selected dataset would need spatial and temporal alignment before it could be combined with the FireFusion modelling data.

This means GEE does provide appropriate **candidate datasets**, but further testing is needed before deciding whether one should be added to the existing historical fire pipeline.























































