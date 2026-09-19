import Layout from "../components/Layout";
import { Database, Server, Cpu, RefreshCw, CheckCircle2 } from "lucide-react";
import "../App.css";

export default function DataSourcesMethod() {
  const sources = [
    { title: "Bureau of Meteorology (BoM)", type: "Weather & Climate API", status: "Active (Synced 2m ago)", coverage: "Wind, Temp, Humidity, FDI" },
    { title: "Country Fire Authority (CFA)", type: "Incident Dispatch Feed", status: "Active (Live)", coverage: "Fire Fronts & Response Units" },
    { title: "VicEmergency Open Data", type: "State Warning System", status: "Active (Live)", coverage: "Evacuation Warnings & Advice" },
    { title: "NASA FIRMS / MODIS", type: "Satellite Thermal Anomalies", status: "Active (Synced 12m ago)", coverage: "Thermal Hotspots & Smoke Plumes" },
    { title: "FireFusion AI NLP Engine", type: "Misinformation Filter", status: "Active (99.2% Accuracy)", coverage: "Social Media Verification Pipeline" },
  ];

  return (
    <Layout title="Data Sources & Methodology">
      <div className="ff-dashboard">
        <section className="ff-hero" style={{ minHeight: "160px" }}>
          <div className="ff-hero-overlay"></div>
          <div className="ff-hero-content">
            <div className="ff-system-badge">SYSTEM ARCHITECTURE & INGESTION PIPELINE</div>
            <h1>Data Sources & Forecasting Methodology</h1>
            <p>Transparency report on satellite, agency telemetry, and neural fusion algorithms.</p>
          </div>
        </section>

        <div className="ff-dashboard-layout" style={{ marginTop: "16px" }}>
          <div className="ff-column-left">
            <div className="ff-panel">
              <div className="ff-panel-header">
                <h3>
                  <Database size={18} style={{ color: "#38bdf8" }} />
                  Connected Primary Data Feeds
                </h3>
              </div>

              <div style={{ display: "grid", gap: "10px" }}>
                {sources.map((src) => (
                  <div key={src.title} style={{ padding: "12px 14px", borderRadius: "8px", background: "var(--bg-toggle)", border: "1px solid var(--border-panel)" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <strong style={{ fontSize: "14px", color: "var(--text-main)" }}>{src.title}</strong>
                      <span style={{ fontSize: "11px", fontWeight: "700", color: "#22c55e", display: "flex", alignItems: "center", gap: "4px" }}>
                        <CheckCircle2 size={13} />
                        {src.status}
                      </span>
                    </div>
                    <div style={{ display: "flex", gap: "16px", marginTop: "6px", fontSize: "12px", color: "var(--text-toggle)" }}>
                      <span>Type: <b>{src.type}</b></span>
                      <span>Attributes: <b>{src.coverage}</b></span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="ff-column-right">
            <div className="ff-panel">
              <div className="ff-panel-header">
                <h3>
                  <Cpu size={18} style={{ color: "#a855f7" }} />
                  Fusion & Misinformation Pipeline
                </h3>
              </div>
              <p style={{ fontSize: "13px", color: "var(--text-toggle)", lineHeight: "1.6" }}>
                FireFusion uses a multi-modal neural fusion layer that aggregates satellite thermal hotspots, weather forecasts, and crowdsourced emergency reports to cross-validate incidents before sounding high-priority alarms.
              </p>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}
