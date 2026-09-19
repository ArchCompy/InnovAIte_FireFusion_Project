import React, { useState } from 'react';
import { AlertOctagon, ChevronRight, X } from 'lucide-react';

export default function CriticalAlertBanner({ extremeZonesCount = 1, onFocusCritical }) {
  const [dismissed, setDismissed] = useState(false);

  if (dismissed || extremeZonesCount === 0) return null;

  return (
    <div className="critical-alert-banner">
      <div className="alert-content-left">
        <div className="alert-badge">
          <AlertOctagon size={14} className="pulse-alert-icon" />
          <span>CRITICAL</span>
        </div>
        <p className="alert-message">
          <strong>Extreme Risk Active:</strong> {extremeZonesCount} zone(s) under Catastrophic conditions.
        </p>
      </div>

      <div className="alert-actions">
        <button
          type="button"
          className="alert-focus-btn"
          onClick={onFocusCritical}
          title="Zoom to primary extreme fire sector"
        >
          <span>View Sector</span>
          <ChevronRight size={13} />
        </button>
        <button
          type="button"
          className="alert-dismiss-btn"
          onClick={() => setDismissed(true)}
          title="Dismiss warning bar"
        >
          <X size={14} />
        </button>
      </div>
    </div>
  );
}
