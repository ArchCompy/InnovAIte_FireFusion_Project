import React, { useState } from 'react';
import {
  Plus,
  Minus,
  RotateCcw,
  Layers,
  Flame,
  Wind,
  ShieldAlert,
  Maximize2,
  Minimize2,
  FileText,
  Radio
} from 'lucide-react';

export default function MapControls({
  onZoomIn,
  onZoomOut,
  onResetView,
  currentBasemap,
  onSelectBasemap,
  layers,
  onToggleLayer,
  onOpenSitrep,
  isFullscreen,
  onToggleFullscreen,
  isConnected = true
}) {
  const [showLayerMenu, setShowLayerMenu] = useState(false);
  const [showBasemapMenu, setShowBasemapMenu] = useState(false);

  return (
    <div className="map-controls-container">
      {/* Top Single Horizontal Row */}
      <div className="map-controls-top-row">
        {/* Real-time Connection Indicator */}
        <div className={`map-live-badge ${isConnected ? 'live' : 'offline'}`} title={isConnected ? 'Live WebSocket active' : 'Offline / Reconnecting'}>
          <span className="live-dot" />
          <Radio size={12} className="live-icon" />
          <span className="live-text">{isConnected ? 'LIVE SYNC' : 'OFFLINE'}</span>
        </div>

        {/* Action Buttons Group */}
        <div className="map-controls-group">
          {/* SITREP Emergency Report button */}
          <button
            className="map-control-btn sitrep-btn"
            onClick={onOpenSitrep}
            title="Generate Situation Report (SITREP)"
          >
            <FileText size={15} />
            <span className="btn-label">SITREP</span>
          </button>

          {/* Basemap Switcher */}
          <div className="map-control-dropdown-wrap">
            <button
              className={`map-control-btn ${showBasemapMenu ? 'active' : ''}`}
              onClick={() => {
                setShowBasemapMenu(!showBasemapMenu);
                setShowLayerMenu(false);
              }}
              title="Switch Map Tiles (Street, Dark, Satellite)"
            >
              <Layers size={15} />
              <span className="btn-label">Basemap</span>
            </button>

            {showBasemapMenu && (
              <div className="map-dropdown-menu basemap-menu">
                <div className="dropdown-header">Map Style</div>
                <button
                  className={`dropdown-item ${currentBasemap === 'street' ? 'selected' : ''}`}
                  onClick={() => {
                    onSelectBasemap('street');
                    setShowBasemapMenu(false);
                  }}
                >
                  <span className="swatch street-swatch" />
                  <span>OpenStreetMap Standard</span>
                </button>
                <button
                  className={`dropdown-item ${currentBasemap === 'dark' ? 'selected' : ''}`}
                  onClick={() => {
                    onSelectBasemap('dark');
                    setShowBasemapMenu(false);
                  }}
                >
                  <span className="swatch dark-swatch" />
                  <span>Dark Ops Matter</span>
                </button>
                <button
                  className={`dropdown-item ${currentBasemap === 'satellite' ? 'selected' : ''}`}
                  onClick={() => {
                    onSelectBasemap('satellite');
                    setShowBasemapMenu(false);
                  }}
                >
                  <span className="swatch sat-swatch" />
                  <span>Satellite Imagery</span>
                </button>
              </div>
            )}
          </div>

          {/* Overlays / Layer Toggles */}
          <div className="map-control-dropdown-wrap">
            <button
              className={`map-control-btn ${showLayerMenu ? 'active' : ''}`}
              onClick={() => {
                setShowLayerMenu(!showLayerMenu);
                setShowBasemapMenu(false);
              }}
              title="Toggle Map Overlays"
            >
              <Flame size={15} />
              <span className="btn-label">Layers</span>
            </button>

            {showLayerMenu && (
              <div className="map-dropdown-menu layer-menu">
                <div className="dropdown-header">Overlays & Hazards</div>
                
                <label className="dropdown-checkbox-item">
                  <input
                    type="checkbox"
                    checked={layers.hotspots}
                    onChange={() => onToggleLayer('hotspots')}
                  />
                  <Flame size={14} className="item-icon text-red" />
                  <span>Thermal Hotspots</span>
                </label>

                <label className="dropdown-checkbox-item">
                  <input
                    type="checkbox"
                    checked={layers.wind}
                    onChange={() => onToggleLayer('wind')}
                  />
                  <Wind size={14} className="item-icon text-cyan" />
                  <span>Wind Vectors (45 km/h)</span>
                </label>

                <label className="dropdown-checkbox-item">
                  <input
                    type="checkbox"
                    checked={layers.shelters}
                    onChange={() => onToggleLayer('shelters')}
                  />
                  <ShieldAlert size={14} className="item-icon text-amber" />
                  <span>Shelters & Closures</span>
                </label>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Navigation & Zoom controls (Vertical stack below top row) */}
      <div className="map-controls-group nav-group">
        <button
          className="map-control-btn icon-only"
          onClick={onZoomIn}
          title="Zoom In"
        >
          <Plus size={16} />
        </button>
        <button
          className="map-control-btn icon-only"
          onClick={onZoomOut}
          title="Zoom Out"
        >
          <Minus size={16} />
        </button>
        <button
          className="map-control-btn icon-only"
          onClick={onResetView}
          title="Reset View to Victoria"
        >
          <RotateCcw size={15} />
        </button>
        <button
          className="map-control-btn icon-only"
          onClick={onToggleFullscreen}
          title={isFullscreen ? 'Exit Fullscreen' : 'Fullscreen Map'}
        >
          {isFullscreen ? <Minimize2 size={15} /> : <Maximize2 size={15} />}
        </button>
      </div>
    </div>
  );
}
