import Layout from "../components/Layout";
import { Flame, CloudRain, Wind, AlertCircle, Compass, Thermometer } from "lucide-react";
import "../App.css";

export default function BushfireForecastDetails() {
  const regions = [
    { name: "East Gippsland", dangerRating: "Catastrophic", fdi: 104, temp: "42°C", humidity: "9%", wind: "55 km/h NW" },
    { name: "Grampians & Mallee", dangerRating: "Extreme", fdi: 88, temp: "39°C", humidity: "12%", wind: "42 km/h W" },
    { name: "Central Victoria", dangerRating: "Severe", fdi: 64, temp: "36°C", humidity: "16%", wind: "32 km/h SW" },
    { name: "South West", dangerRating: "High", fdi: 42, temp: "31°C", humidity: "22%", wind: "24 km/h S" },
  ];

  return (
    <Layout title="Bushfire Forecast Details">
      <div className="ff-dashboard">
        <section className="ff-hero" style={{ minHeight: "160px" }}>
          <div className="ff-hero-overlay"></div>
          <div className="ff-hero-content">
            <div className="ff-system-badge">METEOROLOGICAL & PREDICTIVE MODELLING</div>
            <h1>Victoria Bushfire Forecast & FDI Metrics</h1>
            <p>Bureau of Meteorology (BoM) synced Fire Danger Index calculations and wind trajectory models.</p>
          </div>
        </section>

        <div className="ff-dashboard-layout" style={{ marginTop: "16px" }}>
          <div className="ff-column-left">
            <div className="ff-panel">
              <div className="ff-panel-header">
                <h3>
                  <Flame size={18} style={{ color: "#ef233c" }} />
                  Regional Fire Danger Index (FDI) Projections
                </h3>
              </div>

              <div style={{ display: "grid", gap: "12px" }}>
                {regions.map((reg) => (
                  <div key={reg.name} style={{ padding: "14px", borderRadius: "10px", background: "var(--bg-toggle)", border: "1px solid var(--border-panel)" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                      <strong style={{ fontSize: "15px", color: "var(--text-main)" }}>{reg.name}</strong>
                      <span className="ff-badge ff-badge-critical">{reg.dangerRating}</span>
                    </div>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "8px", fontSize: "12px" }}>
                      <div><small style={{ color: "var(--text-toggle)" }}>FDI Score:</small><br /><b>{reg.fdi}</b></div>
                      <div><small style={{ color: "var(--text-toggle)" }}>Temp:</small><br /><b>{reg.temp}</b></div>
                      <div><small style={{ color: "var(--text-toggle)" }}>Humidity:</small><br /><b>{reg.humidity}</b></div>
                      <div><small style={{ color: "var(--text-toggle)" }}>Wind:</small><br /><b>{reg.wind}</b></div>
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
                  <Compass size={18} style={{ color: "#38bdf8" }} />
                  Fire Behavior Forecasting Factors
                </h3>
              </div>
              <p style={{ fontSize: "13px", color: "var(--text-toggle)", lineHeight: "1.6" }}>
                The McArthur Forest Fire Danger Index calculates fuel dryness, wind speed, relative humidity, and drought factor. Readings above 50 indicate conditions where suppression efforts often become ineffective.
              </p>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}
