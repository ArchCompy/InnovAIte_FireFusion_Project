import React from 'react';
import {
  X,
  AlertTriangle,
  Flame,
  Wind,
  ShieldCheck,
  MapPin,
  Clock,
  PhoneCall,
  Crosshair,
  ExternalLink
} from 'lucide-react';

const RISK_MAP = {
  1: {
    label: 'Level 1: Extreme',
    color: '#cc2e2e',
    bg: '#fee2e2',
    threat: 'Out of Control - Rapid Spread',
    evacuationAdvice: 'EVACUATE IMMEDIATELY. Leaving now is the safest option. Catastrophic fire behaviour expected.',
    containment: 15,
    areaHa: 4850
  },
  2: {
    label: 'Level 2: High',
    color: '#cd5c00',
    bg: '#ffedd5',
    threat: 'Active Fire Front - Uncontained',
    evacuationAdvice: 'PREPARE TO LEAVE. Watch and Act. Conditions are dangerous and deteriorating.',
    containment: 42,
    areaHa: 2100
  },
  3: {
    label: 'Level 3: Medium',
    color: '#eab308',
    bg: '#fef9c3',
    threat: 'Controlled Perimeter',
    evacuationAdvice: 'STAY INFORMED. Monitor conditions. Follow advice of local emergency services.',
    containment: 78,
    areaHa: 650
  },
  4: {
    label: 'Level 4: Low',
    color: '#22c55e',
    bg: '#dcfce7',
    threat: 'Under Control / Mopping Up',
    evacuationAdvice: 'NORMAL AWARENESS. No immediate threat to lives or homes.',
    containment: 96,
    areaHa: 180
  },
  5: {
    label: 'Level 5: Very Low',
    color: '#64748b',
    bg: '#f1f5f9',
    threat: 'Safe / Low Hazard',
    evacuationAdvice: 'Standard seasonal vigilance. Check local fire restrictions.',
    containment: 100,
    areaHa: 0
  }
};

export default function IncidentDrawer({ zone, onClose, onFocusZone }) {
  if (!zone) return null;

  const riskNum = zone.properties?.risk_factor || 3;
  const meta = RISK_MAP[riskNum] || RISK_MAP[3];

  const zoneName = zone.properties?.name || `Victorian Fire Sector ${zone.properties?.id || '#' + riskNum}`;
  const coordinatesStr = zone.properties?.center 
    ? `${zone.properties.center[0].toFixed(3)}° S, ${zone.properties.center[1].toFixed(3)}° E`
    : 'Victoria, Australia';

  return (
    <aside className="incident-drawer-wrap" aria-label="Incident Detail Panel">
      {/* Header */}
      <div className="incident-drawer-header">
        <div className="header-badge-row">
          <span
            className="incident-risk-pill"
            style={{ backgroundColor: meta.color, color: '#fff' }}
          >
            <AlertTriangle size={14} />
            {meta.label}
          </span>
          <span className="incident-updated-tag">
            <Clock size={12} />
            Updated 3m ago
          </span>
        </div>

        <button
          className="incident-close-btn"
          onClick={onClose}
          aria-label="Close Incident Panel"
          title="Close details"
        >
          <X size={18} />
        </button>
      </div>

      <div className="incident-drawer-body">
        {/* Title and location */}
        <h2 className="incident-zone-title">{zoneName}</h2>
        <div className="incident-location-row">
          <MapPin size={14} className="text-orange" />
          <span>{coordinatesStr}</span>
        </div>

        {/* Warning Banner */}
        <div
          className="incident-advice-box"
          style={{ borderColor: meta.color, backgroundColor: meta.bg }}
        >
          <div className="advice-headline" style={{ color: meta.color }}>
            <Flame size={16} />
            <strong>{meta.threat}</strong>
          </div>
          <p className="advice-text">{meta.evacuationAdvice}</p>
        </div>

        {/* Metrics Grid */}
        <div className="incident-metrics-grid">
          <div className="metric-card">
            <span className="metric-label">Estimated Burn Area</span>
            <strong className="metric-value">{meta.areaHa.toLocaleString()} ha</strong>
          </div>
          <div className="metric-card">
            <span className="metric-label">Containment Line</span>
            <strong className="metric-value">{meta.containment}%</strong>
          </div>
          <div className="metric-card">
            <span className="metric-label">Wind Gust Exposure</span>
            <strong className="metric-value">45 km/h NW</strong>
          </div>
          <div className="metric-card">
            <span className="metric-label">Relative Humidity</span>
            <strong className="metric-value">18% (Critical)</strong>
          </div>
        </div>

        {/* Containment progress */}
        <div className="containment-bar-section">
          <div className="containment-labels">
            <span>Containment Progress</span>
            <span>{meta.containment}%</span>
          </div>
          <div className="containment-track">
            <div
              className="containment-fill"
              style={{
                width: `${meta.containment}%`,
                backgroundColor: meta.color
              }}
            />
          </div>
        </div>

        {/* Action Checklist */}
        <div className="incident-checklist-section">
          <h3 className="section-title">Responder & Public Directives</h3>
          <ul className="directives-list">
            <li>
              <ShieldCheck size={14} className="text-green" />
              <span>Evacuation route: Princess & Western Highway corridors</span>
            </li>
            <li>
              <ShieldCheck size={14} className="text-green" />
              <span>Activate neighborhood safe havens and relief centers</span>
            </li>
            <li>
              <ShieldCheck size={14} className="text-green" />
              <span>Close local forest access roads and regional tracks</span>
            </li>
          </ul>
        </div>

        {/* Footer actions */}
        <div className="incident-actions-row">
          <button
            className="incident-primary-btn"
            onClick={() => onFocusZone(zone)}
            title="Recenter and zoom directly into this zone"
          >
            <Crosshair size={15} />
            <span>Focus Zone</span>
          </button>
          
          <a
            href="tel:000"
            className="incident-emergency-call-btn"
            title="Emergency Services (000)"
          >
            <PhoneCall size={15} />
            <span>Call 000</span>
          </a>
        </div>
      </div>
    </aside>
  );
}
