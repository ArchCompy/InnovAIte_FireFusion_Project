import { useState } from "react";
import { Filter, Check, RotateCcw } from "lucide-react";

const LEGEND_ITEMS = [
  { level: 1, color: "#cc2e2e", label: "Level 1: Extreme" },
  { level: 2, color: "#cd5c00", label: "Level 2: High" },
  { level: 3, color: "#ffd043", label: "Level 3: Medium" },
  { level: 4, color: "#37d90f", label: "Level 4: Low" },
  { level: 5, color: "#95a5a6", label: "Level 5: Very Low" },
];

export default function MapLegend({
  selectedRisks = [1, 2, 3, 4, 5],
  onToggleRisk,
  onResetRiskFilter,
}) {
  const [collapsed, setCollapsed] = useState(false);

  const isFiltered = selectedRisks && selectedRisks.length < 5;

  return (
    <div className={`map-legend ${collapsed ? 'collapsed' : ''}`}>
      <button
        className="map-legend-toggle"
        onClick={() => setCollapsed(!collapsed)}
        title={collapsed ? "Expand Legend" : "Collapse Legend"}
      >
        {collapsed ? "▲" : "▼"}
      </button>

      {collapsed && (
        <div className="map-legend-collapsed-label">
          Legend
        </div>
      )}

      {!collapsed && (
        <>
          <div className="map-legend-header-left">
            <span className="map-legend-title">Fire Risk Rating</span>
            {isFiltered && onResetRiskFilter && (
              <button
                className="legend-reset-btn"
                onClick={onResetRiskFilter}
                title="Show all risk levels"
              >
                <RotateCcw size={11} />
                <span>Show All</span>
              </button>
            )}
          </div>

          <div className="map-legend-items">
            {LEGEND_ITEMS.map((item) => {
              const isSelected = selectedRisks.includes(item.level);
              return (
                <button
                  key={item.label}
                  type="button"
                  className={`map-legend-item-btn ${isSelected ? "selected" : "dimmed"}`}
                  onClick={() => onToggleRisk && onToggleRisk(item.level)}
                  title={`Click to toggle ${item.label} on map`}
                >
                  <span
                    className="map-legend-swatch"
                    style={{ background: item.color }}
                  />
                  <span className="item-label">{item.label}</span>
                </button>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}