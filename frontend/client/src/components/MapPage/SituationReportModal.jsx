import React from 'react';
import { X, Printer, Download, AlertTriangle, ShieldCheck, Wind, Thermometer, Droplets, Eye } from 'lucide-react';

export default function SituationReportModal({ isOpen, onClose, weatherData, zonesData }) {
  if (!isOpen) return null;

  const nowStr = new Date().toLocaleString('en-AU', {
    dateStyle: 'full',
    timeStyle: 'medium',
    timeZone: 'Australia/Melbourne'
  });

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="sitrep-modal-backdrop" onClick={onClose}>
      <div className="sitrep-modal-content" onClick={(e) => e.stopPropagation()}>
        {/* Modal Header */}
        <div className="sitrep-modal-header no-print">
          <div>
            <h2 className="sitrep-title">Emergency Situation Report (SITREP)</h2>
            <p className="sitrep-subtitle">State Emergency Service & CFA Operational Briefing</p>
          </div>
          
          <div className="sitrep-header-actions">
            <button className="sitrep-action-btn primary" onClick={handlePrint} title="Print or Save as PDF">
              <Printer size={16} />
              <span>Print / Save PDF</span>
            </button>
            <button className="sitrep-close-btn" onClick={onClose} title="Close">
              <X size={20} />
            </button>
          </div>
        </div>

        {/* Printable Report Body */}
        <div className="sitrep-document">
          <div className="doc-header">
            <div className="doc-branding">
              <span className="doc-badge">FIREFUSION OPS</span>
              <h3>VICTORIAN BUSHFIRE EMERGENCY SITREP</h3>
            </div>
            <div className="doc-timestamp">
              <small>TIMESTAMP (AEST):</small>
              <strong>{nowStr}</strong>
            </div>
          </div>

          <hr className="doc-divider" />

          {/* Meteorological summary */}
          <section className="doc-section">
            <h4 className="doc-section-title">1. METEOROLOGICAL THREAT INDEX</h4>
            <div className="doc-grid-4">
              <div className="doc-stat-box alert">
                <span className="stat-label"><Thermometer size={14} /> Ambient Temp</span>
                <span className="stat-val">{weatherData?.temp || '42°C'}</span>
                <small className="stat-tag">Heatwave Active</small>
              </div>
              <div className="doc-stat-box warning">
                <span className="stat-label"><Wind size={14} /> Wind Speed</span>
                <span className="stat-val">{weatherData?.wind || '45 km/h NW'}</span>
                <small className="stat-tag">High Gust Exposure</small>
              </div>
              <div className="doc-stat-box danger">
                <span className="stat-label"><Droplets size={14} /> Relative Humidity</span>
                <span className="stat-val">{weatherData?.humidity || '18%'}</span>
                <small className="stat-tag">Critical Fuel Dryness</small>
              </div>
              <div className="doc-stat-box">
                <span className="stat-label"><Eye size={14} /> Visibility</span>
                <span className="stat-val">{weatherData?.visibility || '3 km'}</span>
                <small className="stat-tag">Smoke Hazard</small>
              </div>
            </div>
          </section>

          {/* Incident Table */}
          <section className="doc-section">
            <h4 className="doc-section-title">2. ACTIVE INCIDENT SECTORS & PERIMETERS</h4>
            <table className="doc-table">
              <thead>
                <tr>
                  <th>Sector / Area</th>
                  <th>Risk Rating</th>
                  <th>Est. Area</th>
                  <th>Containment</th>
                  <th>Public Action</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td><strong>Alpine National Park East</strong></td>
                  <td><span className="doc-pill extreme">Level 1: Extreme</span></td>
                  <td>4,850 ha</td>
                  <td>15%</td>
                  <td><strong className="text-red">EVACUATE IMMEDIATELY</strong></td>
                </tr>
                <tr>
                  <td><strong>Grampians (Gariwerd) West</strong></td>
                  <td><span className="doc-pill high">Level 2: High</span></td>
                  <td>2,100 ha</td>
                  <td>42%</td>
                  <td>Watch and Act - Prepare to leave</td>
                </tr>
                <tr>
                  <td><strong>Yarra Ranges Eastern Flank</strong></td>
                  <td><span className="doc-pill medium">Level 3: Medium</span></td>
                  <td>650 ha</td>
                  <td>78%</td>
                  <td>Stay Informed & Monitor</td>
                </tr>
                <tr>
                  <td><strong>Otway Coastal Ridge</strong></td>
                  <td><span className="doc-pill low">Level 4: Low</span></td>
                  <td>180 ha</td>
                  <td>96%</td>
                  <td>Under Control / Patrol</td>
                </tr>
              </tbody>
            </table>
          </section>

          {/* Strategic actions */}
          <section className="doc-section">
            <h4 className="doc-section-title">3. EVACUATION CENTERS & INFRASTRUCTURE</h4>
            <ul className="doc-bullet-list">
              <li><strong>Bairnsdale Community Relief Centre:</strong> OPEN - 65% Capacity. Medical support on site.</li>
              <li><strong>Ballarat Regional Safe Haven:</strong> OPEN - Ready for Grampians evacuees.</li>
              <li><strong>Road Closures:</strong> Great Alpine Road between Harrietville and Mount Hotham CLOSED to all civilian traffic.</li>
              <li><strong>Total Fire Ban:</strong> In effect statewide for 24 hours. No open fires or machinery operations permitted.</li>
            </ul>
          </section>

          <div className="doc-footer">
            <small>CONFIDENTIAL & AUTHORIZED FOR CFA / SES / EMERGENCY COMMAND OPERATIONS ONLY</small>
          </div>
        </div>
      </div>
    </div>
  );
}
