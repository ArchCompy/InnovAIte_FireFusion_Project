import Layout from "../components/Layout";
import { ShieldAlert, PhoneCall, Radio, HeartPulse, FileText, CheckCircle } from "lucide-react";
import "../App.css";

export default function EmergencyAdvice() {
  const emergencyContacts = [
    { name: "Emergency Services (Police, Fire, Ambulance)", number: "000", desc: "For life-threatening emergencies only" },
    { name: "VicEmergency Hotline", number: "1800 226 226", desc: "Current bushfire updates and road closures" },
    { name: "CFA General Enquiries", number: "03 9262 8444", desc: "Country Fire Authority guidance" },
    { name: "State Emergency Service (SES)", number: "132 500", desc: "Flood, storm, and tree damage assistance" },
  ];

  const safetyChecklist = [
    "Prepare your Bushfire Survival Kit (water, battery radio, torch, medications).",
    "Identify at least two evacuation routes from your area.",
    "Keep mobile devices charged and have portable power banks ready.",
    "Clear dry leaves, twigs, and debris from gutters and around house perimeters.",
    "Do not wait until the last minute—leave early if an Emergency Warning is declared.",
  ];

  return (
    <Layout title="Emergency Advice">
      <div className="ff-dashboard">
        <section className="ff-hero" style={{ minHeight: "160px" }}>
          <div className="ff-hero-overlay"></div>
          <div className="ff-hero-content">
            <div className="ff-system-badge">CIVIL DEFENSE & COMMUNITY SAFETY</div>
            <h1>Bushfire Safety & Emergency Advice</h1>
            <p>Official guidelines, preparedness steps, and direct emergency contacts for Victoria.</p>
          </div>
        </section>

        <div className="ff-dashboard-layout" style={{ marginTop: "16px" }}>
          <div className="ff-column-left">
            <div className="ff-panel">
              <div className="ff-panel-header">
                <h3>
                  <ShieldAlert size={18} style={{ color: "#ef233c" }} />
                  Immediate Action Protocols
                </h3>
              </div>
              <div style={{ display: "grid", gap: "12px" }}>
                <div className="ff-update-card critical">
                  <div className="ff-update-body" style={{ width: "100%" }}>
                    <div>
                      <h4 style={{ margin: "0 0 6px", color: "#ef233c" }}>If Caught in a Bushfire</h4>
                      <p style={{ margin: 0, fontSize: "13px", color: "var(--text-toggle)" }}>
                        Take shelter in a sturdy building. Close all doors, windows, and vents. Fill sinks and baths with water. Protect yourself with natural fiber clothing.
                      </p>
                    </div>
                  </div>
                </div>

                <div className="ff-update-card warning">
                  <div className="ff-update-body" style={{ width: "100%" }}>
                    <div>
                      <h4 style={{ margin: "0 0 6px", color: "#f97316" }}>Travel & Driving Warnings</h4>
                      <p style={{ margin: 0, fontSize: "13px", color: "var(--text-toggle)" }}>
                        Never drive through thick smoke. Turn headlights on, keep windows up, and pull over to a clear clearing if trapped.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="ff-panel" style={{ marginTop: "14px" }}>
              <div className="ff-panel-header">
                <h3>
                  <CheckCircle size={18} style={{ color: "#22c55e" }} />
                  Bushfire Preparedness Checklist
                </h3>
              </div>
              <ul style={{ paddingLeft: "20px", margin: 0, display: "grid", gap: "10px", fontSize: "13px", color: "var(--text-main)" }}>
                {safetyChecklist.map((item, idx) => (
                  <li key={idx} style={{ lineHeight: "1.5" }}>{item}</li>
                ))}
              </ul>
            </div>
          </div>

          <div className="ff-column-right">
            <div className="ff-panel">
              <div className="ff-panel-header">
                <h3>
                  <PhoneCall size={18} style={{ color: "#3b82f6" }} />
                  Critical Contact Directory
                </h3>
              </div>
              <div style={{ display: "grid", gap: "12px" }}>
                {emergencyContacts.map((contact) => (
                  <div key={contact.name} style={{ padding: "12px", borderRadius: "8px", background: "var(--bg-toggle)", border: "1px solid var(--border-panel)" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <strong style={{ fontSize: "13px", color: "var(--text-main)" }}>{contact.name}</strong>
                      <span style={{ fontSize: "15px", fontWeight: "900", color: "#ef233c" }}>{contact.number}</span>
                    </div>
                    <small style={{ color: "var(--text-toggle)", display: "block", marginTop: "4px" }}>{contact.desc}</small>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}
