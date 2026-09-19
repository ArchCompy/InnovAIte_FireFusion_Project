-- Seed data for bushfire risk database

INSERT INTO Location_Registry (
    location_id, 
    grid_latitude, 
    grid_longitude, 
    region_name
    ) VALUES
(1, -37.8136, 144.9631, 'Melbourne'),
(2, -37.4713, 144.7857, 'Gisborne'),
(3, -37.655, 145.517, 'Yarra Valley'),
(4, -37.174, 145.9333, 'Mansfield'),
(5, -36.759, 144.28, 'Bendigo'),
(6, -37.5229, 145.9934, 'Healesville'),
(7, -38.3818, 142.4854, 'Warrnambool'),
(8, -36.364, 146.32, 'Wangaratta'),
(9, -37.5622, 143.8503, 'Ballarat'),
(10, -38.225, 145.041, 'Mornington Peninsula');


INSERT INTO Time_Registry (
    time_id, 
    datetime_record, 
    season
    ) VALUES
(101, '2025-01-15 14:00:00', 'Summer'),
(102, '2025-01-15 13:30:00', 'Summer'),
(103, '2025-02-03 15:00:00', 'Summer'),
(104, '2025-02-03 14:00:00', 'Summer'),
(105, '2025-01-28 12:00:00', 'Summer'),
(106, '2025-02-10 14:30:00', 'Summer'),
(107, '2025-12-20 13:00:00', 'Summer'),
(108, '2025-01-05 11:00:00', 'Summer'),
(109, '2025-02-14 15:00:00', 'Summer'),
(110, '2025-03-01 14:00:00', 'Autumn');


INSERT INTO Topography_Profile (
    topo_id, 
    location_id, 
    original_latitude, 
    original_longitude, 
    elevation_meters, 
    slope_angle
    ) VALUES
(1, 1, -37.8136, 144.9631, 31.0, 2.5),
(2, 2, -37.4713, 144.7857, 520.0, 18.3),
(3, 3, -37.655, 145.517, 120.0, 8.7),
(4, 4, -37.174, 145.9333, 85.0, 5.1),
(5, 5, -36.759, 144.28, 225.0, 12.4),
(6, 6, -37.5229, 145.9934, 680.0, 22.6),
(7, 7, -38.3818, 142.4854, 45.0, 3.2),
(8, 8, -36.364, 146.32, 310.0, 15.8),
(9, 9, -37.5622, 143.8503, 440.0, 19.1),
(10, 10, -38.225, 145.041, 60.0, 4.6);


INSERT INTO Weather_Observation (
    weather_id, 
    location_id, 
    time_id, 
    original_latitude, 
    original_longitude, 
    temperature_c, 
    wind_speed_kmh, 
    relative_humidity, 
    source_system
    ) VALUES
(1, 1, 101, -37.8136, 144.9631, 34.2, 28.0, 18.5, 'BOM'),
(2, 2, 102, -37.4713, 144.7857, 39.8, 24.0, 14.2, 'BOM'),
(3, 3, 103, -37.655, 145.517, 41.1, 31.0, 12.8, 'BOM'),
(4, 4, 104, -37.174, 145.9333, 29.7, 19.0, 24.1, 'BOM'),
(5, 5, 105, -36.759, 144.28, 43.5, 36.0, 9.6, 'BOM'),
(6, 6, 106, -37.5229, 145.9934, 37.9, 22.0, 13.4, 'BOM'),
(7, 7, 107, -38.3818, 142.4854, 33.8, 27.0, 20.2, 'BOM'),
(8, 8, 108, -36.364, 146.32, 42.6, 34.0, 8.1, 'BOM'),
(9, 9, 109, -37.5622, 143.8503, 40.4, 26.0, 11.7, 'BOM'),
(10, 10, 110, -38.225, 145.041, 30.5, 17.0, 22.9, 'BOM');


INSERT INTO Vegetation_Condition (
    veg_condition_id, 
    location_id, 
    time_id, 
    original_latitude, 
    original_longitude, 
    vegetation_class, 
    dryness_index, 
    soil_moisture, 
    source_system
    ) VALUES
(1, 1, 101, -37.8136, 144.9631, 'Urban parkland', 6.8, 0.18, 'Satellite composite'),
(2, 2, 102, -37.4713, 144.7857, 'Dry sclerophyll forest', 8.4, 0.09, 'Satellite composite'),
(3, 3, 103, -37.655, 145.517, 'Wet sclerophyll forest', 5.9, 0.22, 'Satellite composite'),
(4, 4, 104, -37.174, 145.9333, 'Alpine ash forest', 7.3, 0.14, 'Satellite composite'),
(5, 5, 105, -36.759, 144.28, 'Grassland', 9.1, 0.06, 'Satellite composite'),
(6, 6, 106, -37.5229, 145.9934, 'Forest regrowth', 6.2, 0.17, 'Satellite composite'),
(7, 7, 107, -38.3818, 142.4854, 'Coastal heathland', 7.8, 0.11, 'Satellite composite'),
(8, 8, 108, -36.364, 146.32, 'Dry sclerophyll forest', 8.7, 0.07, 'Satellite composite'),
(9, 9, 109, -37.5622, 143.8503, 'Grassy woodland', 7.0, 0.13, 'Satellite composite'),
(10, 10, 110, -38.225, 145.041, 'Urban grassland', 6.5, 0.16, 'Satellite composite');


INSERT INTO Infrastructure_Asset (
    asset_id, 
    location_id, 
    original_latitude, 
    original_longitude, 
    facility_name, 
    risk_category
    ) VALUES
(1, 1, -37.8136, 144.9631, 'Melbourne General Hospital', 'Hospital'),
(2, 2, -37.4713, 144.7857, 'Gisborne Primary School', 'School'),
(3, 3, -37.655, 145.517, 'Yarra Valley Water Pump Station', 'Water Supply'),
(4, 4, -37.174, 145.9333, 'Mt Buller Alpine Village', 'Tourism'),
(5, 5, -36.759, 144.28, 'Bendigo Base Hospital', 'Hospital'),
(6, 6, -37.5229, 145.9934, 'Healesville CFA Station', 'Emergency Services'),
(7, 7, -38.3818, 142.4854, 'Warrnambool Rail Hub', 'Transport'),
(8, 8, -36.364, 146.32, 'Wangaratta Substation', 'Power Infrastructure'),
(9, 9, -37.5622, 143.8503, 'Ballarat Aged Care Home', 'Aged Care'),
(10, 10, -38.225, 145.041, 'Mornington Community Centre', 'Community Facility');

INSERT INTO Fire_Incident_Record (
    incident_id, 
    location_id, 
    time_id, 
    original_latitude, 
    original_longitude, 
    confidence_score, 
    source_system) VALUES
(1, 1, 101, -37.8128, 144.962, 85.0, 'MODIS hotspot'),
(2, 2, 102, -37.4705, 144.7868, 90.0, 'VIIRS hotspot'),
(3, 3, 103, -37.6542, 145.5162, 78.0, 'CFA report'),
(4, 4, 104, -37.1732, 145.934, 92.0, 'Sentinel-2'),
(5, 5, 105, -36.7581, 144.281, 81.0, 'MODIS hotspot'),
(6, 6, 106, -37.5236, 145.9928, 88.0, 'VIIRS hotspot'),
(7, 7, 107, -38.3809, 142.4861, 74.0, 'CFA report'),
(8, 8, 108, -36.3632, 146.3192, 95.0, 'Sentinel-2'),
(9, 9, 109, -37.5614, 143.851, 83.0, 'MODIS hotspot'),
(10, 10, 110, -38.2242, 145.0417, 89.0, 'VIIRS hotspot');

