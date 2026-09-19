// Import the style sheet
import '../components/MapPage/MapPage.layout.css'

// Import UI components
import MapLegend from '../components/MapPage/MapLegend'
import SearchLocation from '../components/MapPage/SearchLocation'
import MapControls from '../components/MapPage/MapControls'
import IncidentDrawer from '../components/MapPage/IncidentDrawer'
import CriticalAlertBanner from '../components/MapPage/CriticalAlertBanner'
import ForecastTimeline from '../components/MapPage/ForecastTimeline'
import SituationReportModal from '../components/MapPage/SituationReportModal'

// Import Layout
import Layout from "../components/Layout"

// Import WebSocket connection dependency 
import ReconnectingWebSocket from 'reconnecting-websocket'

// Import Leaflet
import { useEffect, useRef, useState, useCallback } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

interface ZoneFeature {
  type: "Feature";
  properties: {
    id?: string;
    name?: string;
    risk_factor: number;
    center?: [number, number];
    containment?: number;
    areaHa?: number;
  };
  geometry: {
    type: "Polygon";
    coordinates: number[][][];
  };
}

const ENRICHED_SAMPLE_GEOJSON: { type: "FeatureCollection"; features: ZoneFeature[] } = {
  type: "FeatureCollection",
  features: [
    {
      type: "Feature",
      properties: {
        id: "VIC-ALP-01",
        name: "Alpine National Park East Sector",
        risk_factor: 1,
        center: [-37.42, 147.53],
        containment: 15,
        areaHa: 4850
      },
      geometry: {
        type: "Polygon",
        coordinates: [[[147.15, -37.56], [147.72, -37.74], [147.91, -37.25], [147.38, -37.11], [147.15, -37.56]]]
      }
    },
    {
      type: "Feature",
      properties: {
        id: "VIC-GRM-02",
        name: "Grampians (Gariwerd) West Sector",
        risk_factor: 2,
        center: [-37.14, 142.47],
        containment: 42,
        areaHa: 2100
      },
      geometry: {
        type: "Polygon",
        coordinates: [[[142.15, -37.16], [142.62, -37.44], [142.81, -37.05], [142.38, -36.91], [142.15, -37.16]]]
      }
    },
    {
      type: "Feature",
      properties: {
        id: "VIC-YRA-03",
        name: "Yarra Ranges Eastern Flank",
        risk_factor: 3,
        center: [-37.74, 145.39],
        containment: 78,
        areaHa: 650
      },
      geometry: {
        type: "Polygon",
        coordinates: [[[145.15, -37.86], [145.42, -37.94], [145.61, -37.65], [145.28, -37.51], [145.15, -37.86]]]
      }
    },
    {
      type: "Feature",
      properties: {
        id: "VIC-OTW-04",
        name: "Otway Coastal Ridge Sector",
        risk_factor: 4,
        center: [-38.09, 143.84],
        containment: 96,
        areaHa: 180
      },
      geometry: {
        type: "Polygon",
        coordinates: [[[143.55, -38.12], [143.92, -38.31], [144.11, -38.05], [143.78, -37.88], [143.55, -38.12]]]
      }
    }
  ]
};

// Basemap Tile Providers
const BASEMAP_TILES = {
  street: {
    url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    options: { attribution: '&copy; OpenStreetMap contributors' }
  },
  dark: {
    url: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
    options: { attribution: '&copy; CARTO & OpenStreetMap' }
  },
  satellite: {
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    options: { attribution: 'Tiles &copy; Esri, Maxar, Earthstar Geographics' }
  }
};

// Map risk level to colour
const getRiskColor = (risk: number) => {
  switch (risk) {
    case 1: return '#cc2e2e'; // Extreme
    case 2: return '#cd5c00'; // High
    case 3: return '#ffd043'; // Medium
    case 4: return '#37d90f'; // Low
    case 5: return '#95a5a6'; // Very Low
    default: return '#09a2ad'; // Unknown
  }
};

export default function MapPage() {
  const mapRef = useRef<L.Map | null>(null);
  const baseTileRef = useRef<L.TileLayer | null>(null);
  const geoJsonLayerRef = useRef<L.GeoJSON | null>(null);

  // Overlay Layer Groups
  const hotspotsLayerGroupRef = useRef<L.LayerGroup | null>(null);
  const windLayerGroupRef = useRef<L.LayerGroup | null>(null);
  const sheltersLayerGroupRef = useRef<L.LayerGroup | null>(null);

  // State Management
  const [currentBasemap, setCurrentBasemap] = useState<'street' | 'dark' | 'satellite'>('street');
  const [selectedZone, setSelectedZone] = useState<ZoneFeature | null>(null);
  const [selectedRisks, setSelectedRisks] = useState<number[]>([1, 2, 3, 4, 5]);
  const [activeLayers, setActiveLayers] = useState({
    hotspots: true,
    wind: true,
    shelters: true
  });
  const [forecastStep, setForecastStep] = useState<number>(0);
  const [isWsConnected, setIsWsConnected] = useState<boolean>(true);
  const [isSitrepOpen, setIsSitrepOpen] = useState<boolean>(false);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);
  const [geoData, setGeoData] = useState<any>(ENRICHED_SAMPLE_GEOJSON);

  // Centre map from search bar
  const centerMap = useCallback((lat: number, lon: number) => {
    if (!mapRef.current) return;
    mapRef.current.flyTo([lat, lon], 11, { duration: 1.2 });
  }, []);

  // Reset to full Victoria view
  const resetToVictoria = useCallback(() => {
    if (!mapRef.current) return;
    mapRef.current.flyTo([-37.0, 144.5], 7, { duration: 1.0 });
  }, []);

  // Zoom controls
  const handleZoomIn = () => mapRef.current?.zoomIn();
  const handleZoomOut = () => mapRef.current?.zoomOut();

  // Switch basemap tile layer
  const handleSelectBasemap = useCallback((type: 'street' | 'dark' | 'satellite') => {
    setCurrentBasemap(type);
    if (!mapRef.current) return;

    if (baseTileRef.current) {
      baseTileRef.current.remove();
    }

    const config = BASEMAP_TILES[type];
    const newTile = L.tileLayer(config.url, config.options).addTo(mapRef.current);
    baseTileRef.current = newTile;
  }, []);

  // Toggle risk level in legend
  const handleToggleRisk = useCallback((level: number) => {
    setSelectedRisks(prev => {
      if (prev.includes(level)) {
        // Don't allow deselecting all
        if (prev.length === 1) return prev;
        return prev.filter(r => r !== level);
      } else {
        return [...prev, level].sort();
      }
    });
  }, []);

  // Reset risk filter
  const handleResetRiskFilter = useCallback(() => {
    setSelectedRisks([1, 2, 3, 4, 5]);
  }, []);

  // Toggle overlay layers
  const handleToggleLayer = useCallback((layerKey: 'hotspots' | 'wind' | 'shelters') => {
    setActiveLayers(prev => {
      const updated = { ...prev, [layerKey]: !prev[layerKey] };
      if (!mapRef.current) return updated;

      if (layerKey === 'hotspots' && hotspotsLayerGroupRef.current) {
        if (updated.hotspots) mapRef.current.addLayer(hotspotsLayerGroupRef.current);
        else mapRef.current.removeLayer(hotspotsLayerGroupRef.current);
      }
      if (layerKey === 'wind' && windLayerGroupRef.current) {
        if (updated.wind) mapRef.current.addLayer(windLayerGroupRef.current);
        else mapRef.current.removeLayer(windLayerGroupRef.current);
      }
      if (layerKey === 'shelters' && sheltersLayerGroupRef.current) {
        if (updated.shelters) mapRef.current.addLayer(sheltersLayerGroupRef.current);
        else mapRef.current.removeLayer(sheltersLayerGroupRef.current);
      }
      return updated;
    });
  }, []);

  // Toggle Fullscreen
  const handleToggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().then(() => setIsFullscreen(true)).catch(() => {});
    } else {
      document.exitFullscreen().then(() => setIsFullscreen(false)).catch(() => {});
    }
  };

  // Focus a specific zone
  const handleFocusZone = useCallback((zone: any) => {
    if (!mapRef.current || !zone) return;
    const center = zone.properties?.center;
    if (center && Array.isArray(center) && center.length === 2) {
      mapRef.current.flyTo([center[0], center[1]], 10, { duration: 1.0 });
    }
  }, []);

  // Render GeoJSON risk polygons
  const renderGeoJSON = useCallback((data: any, filterRisks: number[], stepMultiplier: number = 0) => {
    if (!mapRef.current) return;

    if (geoJsonLayerRef.current) {
      geoJsonLayerRef.current.remove();
    }

    geoJsonLayerRef.current = L.geoJSON(data, {
      filter: (feature: any) => {
        const risk = feature.properties?.risk_factor;
        return filterRisks.includes(risk);
      },
      style: (feature: any) => {
        const baseRisk = feature.properties?.risk_factor || 3;
        const color = getRiskColor(baseRisk);
        // Dynamic opacity adjustment based on forecast timeline
        const fillOpacity = Math.min(0.7, 0.4 + (stepMultiplier * 0.02));
        return {
          color: color,
          fillColor: color,
          fillOpacity: fillOpacity,
          weight: 2.5,
          dashArray: stepMultiplier > 4 ? '5, 5' : undefined
        };
      },
      onEachFeature: (feature: any, layer: any) => {
        layer.on('click', () => {
          setSelectedZone(feature);
          if (feature.properties?.center) {
            mapRef.current?.panTo(feature.properties.center);
          }
        });

        // Hover effect
        layer.on('mouseover', function (this: any) {
          this.setStyle({ weight: 4, fillOpacity: 0.65 });
        });
        layer.on('mouseout', function (this: any) {
          geoJsonLayerRef.current?.resetStyle(this);
        });
      }
    }).addTo(mapRef.current);
  }, []);

  // Initialize Map
  useEffect(() => {
    const map = L.map('map', {
      zoomControl: false,
    }).setView([-37.0, 144.5], 7);

    mapRef.current = map;

    // Create Initial Tile Layer
    const baseTile = L.tileLayer(BASEMAP_TILES.street.url, BASEMAP_TILES.street.options).addTo(map);
    baseTileRef.current = baseTile;

    // 1. Hotspots Layer Group
    const hotspotsGroup = L.layerGroup();
    hotspotsLayerGroupRef.current = hotspotsGroup;

    // Add active flame hotspot markers in Alpine & Grampians
    const flameIconHtml = `
      <div class="fire-pulse-icon">
        <div class="fire-pulse-ring"></div>
        <div class="fire-pulse-core">🔥</div>
      </div>
    `;
    const flameDivIcon = L.divIcon({
      html: flameIconHtml,
      className: '',
      iconSize: [28, 28],
      iconAnchor: [14, 14]
    });

    L.marker([-37.42, 147.53], { icon: flameDivIcon })
      .bindPopup('<b>Alpine Active Fire Front</b><br>Thermal Hotspot detected by Sentinel-2<br><b>Intensity:</b> High (FRP 210 MW)')
      .addTo(hotspotsGroup);

    L.marker([-37.14, 142.47], { icon: flameDivIcon })
      .bindPopup('<b>Grampians West Fire</b><br>Active crown fire reported<br><b>Intensity:</b> Moderate (FRP 95 MW)')
      .addTo(hotspotsGroup);

    hotspotsGroup.addTo(map);

    // 2. Wind Direction Vectors Layer Group (45 km/h NW)
    const windGroup = L.layerGroup();
    windLayerGroupRef.current = windGroup;

    const windLocations: [number, number][] = [
      [-37.81, 144.96], // Melbourne
      [-37.56, 143.85], // Ballarat
      [-36.75, 144.28], // Bendigo
      [-37.50, 147.00], // Gippsland North
      [-38.15, 144.36], // Geelong
    ];

    windLocations.forEach(coords => {
      const windHtml = `
        <div class="wind-vector-icon" style="transform: rotate(135deg);">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#0284c7" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <line x1="12" y1="19" x2="12" y2="5"></line>
            <polyline points="5 12 12 5 19 12"></polyline>
          </svg>
        </div>
      `;
      const windIcon = L.divIcon({
        html: windHtml,
        className: '',
        iconSize: [24, 24],
        iconAnchor: [12, 12]
      });

      L.marker(coords, { icon: windIcon })
        .bindPopup('<b>Wind Velocity Vector</b><br>Speed: 45 km/h<br>Direction: North-West (NW)<br>Gusting up to 65 km/h')
        .addTo(windGroup);
    });

    windGroup.addTo(map);

    // 3. Shelters & Road Closures Layer Group
    const sheltersGroup = L.layerGroup();
    sheltersLayerGroupRef.current = sheltersGroup;

    const shelterLocations = [
      { coords: [-37.83, 147.62], name: 'Bairnsdale Community Relief Centre', status: 'OPEN (65% capacity)' },
      { coords: [-37.56, 143.86], name: 'Ballarat Regional Safe Haven', status: 'OPEN (Available)' },
      { coords: [-38.10, 147.06], name: 'Sale Emergency Assembly Point', status: 'ON STANDBY' }
    ];

    shelterLocations.forEach(s => {
      const shelterHtml = `<div class="shelter-map-icon">🛡️</div>`;
      const shelterIcon = L.divIcon({
        html: shelterHtml,
        className: '',
        iconSize: [26, 26],
        iconAnchor: [13, 13]
      });

      L.marker(s.coords as [number, number], { icon: shelterIcon })
        .bindPopup(`<b>Evacuation Shelter</b><br>${s.name}<br><b>Status:</b> ${s.status}`)
        .addTo(sheltersGroup);
    });

    // Roadblocks
    const roadClosures = [
      { coords: [-37.02, 147.13], name: 'Great Alpine Road (Harrietville to Mt Hotham)', reason: 'CLOSED due to active fire and zero visibility' },
      { coords: [-37.22, 142.35], name: 'Grampians Tourist Road', reason: 'CLOSED - CFA emergency vehicles only' }
    ];

    roadClosures.forEach(r => {
      const roadHtml = `<div class="roadblock-map-icon">⛔</div>`;
      const roadIcon = L.divIcon({
        html: roadHtml,
        className: '',
        iconSize: [24, 24],
        iconAnchor: [12, 12]
      });

      L.marker(r.coords as [number, number], { icon: roadIcon })
        .bindPopup(`<b>ROAD CLOSED</b><br>${r.name}<br><span style="color:#b91c1c;">${r.reason}</span>`)
        .addTo(sheltersGroup);
    });

    sheltersGroup.addTo(map);

    // Load initial forecast data
    const loadGeoJSON = async () => {
      try {
        const response = await fetch('/api/bushfire-forecast');
        if (!response.ok) throw new Error(`HTTP error ${response.status}`);
        const data = await response.json();
        setGeoData(data);
        renderGeoJSON(data, [1, 2, 3, 4, 5], 0);
      } catch (error) {
        console.warn('Backend API offline, rendering enhanced Victoria risk map:', error);
        setGeoData(ENRICHED_SAMPLE_GEOJSON);
        renderGeoJSON(ENRICHED_SAMPLE_GEOJSON, [1, 2, 3, 4, 5], 0);
      }
    };

    loadGeoJSON();

    // WebSocket set up for live updates
    const ws = new ReconnectingWebSocket('/api/ws');

    ws.onopen = () => {
      setIsWsConnected(true);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setGeoData(data);
        renderGeoJSON(data, selectedRisks, forecastStep);
      } catch (error) {
        console.error('WebSocket data error:', error);
      }
    };

    ws.onerror = (err) => {
      console.warn('WebSocket reconnecting:', err);
      setIsWsConnected(false);
    };

    ws.onclose = () => {
      setIsWsConnected(false);
    };

    return () => {
      ws.close();
      map.remove();
    };
  }, []);

  // Update polygon layers whenever selectedRisks filter or forecastStep changes
  useEffect(() => {
    if (mapRef.current && geoData) {
      renderGeoJSON(geoData, selectedRisks, forecastStep);
    }
  }, [selectedRisks, forecastStep, geoData, renderGeoJSON]);

  // Primary extreme zone helper for alert banner
  const primaryExtremeZone = ENRICHED_SAMPLE_GEOJSON.features.find(f => f.properties.risk_factor === 1);

  return (
    <Layout title="Fire Map" showTopbar={false}>
      <div className="map-page">

        {/* 1. Search Bar */}
        <SearchLocation
          onSelect={(location) => {
            if (location?.lat && location?.lon) {
              centerMap(location.lat, location.lon);
            }
          }}
        />

        {/* 2. Critical Alert Banner */}
        <CriticalAlertBanner
          extremeZonesCount={1}
          onFocusCritical={() => {
            if (primaryExtremeZone) {
              setSelectedZone(primaryExtremeZone);
              handleFocusZone(primaryExtremeZone);
            }
          }}
        />

        {/* 3. Floating Map Controls (Top Right) */}
        <MapControls
          onZoomIn={handleZoomIn}
          onZoomOut={handleZoomOut}
          onResetView={resetToVictoria}
          currentBasemap={currentBasemap}
          onSelectBasemap={handleSelectBasemap}
          layers={activeLayers}
          onToggleLayer={handleToggleLayer}
          onOpenSitrep={() => setIsSitrepOpen(true)}
          isFullscreen={isFullscreen}
          onToggleFullscreen={handleToggleFullscreen}
          isConnected={isWsConnected}
        />

        {/* 4. Interactive Incident Detail Drawer */}
        {selectedZone && (
          <IncidentDrawer
            zone={selectedZone}
            onClose={() => setSelectedZone(null)}
            onFocusZone={handleFocusZone}
          />
        )}

        {/* 5. Forecast Progression Timeline Scrubber */}
        <ForecastTimeline
          activeStep={forecastStep}
          onStepChange={setForecastStep}
        />

        {/* 6. Interactive Risk Filter Legend */}
        <MapLegend
          selectedRisks={selectedRisks}
          onToggleRisk={handleToggleRisk}
          onResetRiskFilter={handleResetRiskFilter}
        />

        {/* 7. Fullscreen Map Leaflet Canvas */}
        <div className="map-main">
          <div id="map"></div>
        </div>

        {/* 8. Emergency Situation Report (SITREP) Printable Modal */}
        <SituationReportModal
          isOpen={isSitrepOpen}
          onClose={() => setIsSitrepOpen(false)}
          weatherData={{
            temp: '42°C',
            wind: '45 km/h NW',
            humidity: '18%',
            visibility: '3 km'
          }}
          zonesData={geoData}
        />

      </div>
    </Layout>
  );
}