import Layout from "../components/Layout";
import { Info, Target, Users, ShieldCheck, Award } from "lucide-react";
import "../App.css";

export default function AboutUs() {
  return (
    <Layout title="About Us">
      <div className="ff-dashboard">
        <section className="ff-hero" style={{ minHeight: "160px" }}>
          <div className="ff-hero-overlay"></div>
          <div className="ff-hero-content">
            <div className="ff-system-badge">INNOVAITE PROJECT • DEAKIN UNIVERSITY</div>
            <h1>About FireFusion Emergency Intelligence</h1>
            <p>Next-generation bushfire monitoring and social misinformation combat platform.</p>
          </div>
        </section>

        <div className="ff-dashboard-layout" style={{ marginTop: "16px" }}>
          <div className="ff-column-left">
            <div className="ff-panel">
              <div className="ff-panel-header">
                <h3>
                  <Target size={18} style={{ color: "#ef4444" }} />
                  Our Mission
                </h3>
              </div>
              <p style={{ fontSize: "14px", lineHeight: "1.6", color: "var(--text-main)" }}>
                FireFusion was developed to solve the dual challenges of Victorian bushfires: rapid, unpredictable fire front progression and the dangerous spread of panic-inducing misinformation across social platforms during crises.
              </p>
            </div>

            <div className="ff-panel" style={{ marginTop: "14px" }}>
              <div className="ff-panel-header">
                <h3>
                  <ShieldCheck size={18} style={{ color: "#22c55e" }} />
                  Key Capabilities
                </h3>
              </div>
              <ul style={{ paddingLeft: "20px", display: "grid", gap: "8px", fontSize: "13px", color: "var(--text-main)" }}>
                <li><b>Early Bushfire Forecast:</b> AI-driven fire spread simulations based on wind and fuel moisture.</li>
                <li><b>Misinformation Verification:</b> NLP models identify misleading evacuation notices and fake fire maps.</li>
                <li><b>Command Coordination:</b> Resource allocation monitoring for CFA, emergency response units, and air bombers.</li>
              </ul>
            </div>
          </div>

          <div className="ff-column-right">
            <div className="ff-panel">
              <div className="ff-panel-header">
                <h3>
                  <Award size={18} style={{ color: "#eab308" }} />
                  Project Leadership & Research
                </h3>
              </div>
              <p style={{ fontSize: "13px", color: "var(--text-toggle)", lineHeight: "1.6" }}>
                Built under the InnovAIte research framework, bridging real-time disaster informatics with deep learning pipelines to deliver actionable intelligence to civil defense authorities.
              </p>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}
