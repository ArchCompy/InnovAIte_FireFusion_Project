import { useState } from "react";
import Layout from "../components/Layout";
import { MessageSquare, Star, Send, CheckCircle2 } from "lucide-react";
import "../App.css";

export default function Feedback() {
  const [submitted, setSubmitted] = useState(false);
  const [rating, setRating] = useState(5);
  const [category, setCategory] = useState("Dashboard UI");
  const [comment, setComment] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    setSubmitted(true);
  };

  return (
    <Layout title="User Feedback">
      <div className="ff-dashboard">
        <section className="ff-hero" style={{ minHeight: "160px" }}>
          <div className="ff-hero-overlay"></div>
          <div className="ff-hero-content">
            <div className="ff-system-badge">OPERATIONAL EVALUATION</div>
            <h1>System Feedback & Incident Reporting</h1>
            <p>Help us improve FireFusion's emergency intelligence and telemetry accuracy.</p>
          </div>
        </section>

        <div className="ff-dashboard-layout" style={{ marginTop: "16px" }}>
          <div className="ff-column-left">
            <div className="ff-panel">
              <div className="ff-panel-header">
                <h3>
                  <MessageSquare size={18} style={{ color: "#38bdf8" }} />
                  Submit Feedback
                </h3>
              </div>

              {submitted ? (
                <div style={{ textAlign: "center", padding: "30px 10px" }}>
                  <CheckCircle2 size={44} style={{ color: "#22c55e", margin: "0 auto 12px" }} />
                  <h4 style={{ color: "var(--text-main)", margin: "0 0 6px" }}>Feedback Received</h4>
                  <p style={{ color: "var(--text-toggle)", fontSize: "13px" }}>Thank you for helping us optimize our bushfire intelligence platform.</p>
                  <button 
                    className="ff-details-btn" 
                    style={{ marginTop: "10px" }}
                    onClick={() => { setSubmitted(false); setComment(""); }}
                  >
                    Submit Another Response
                  </button>
                </div>
              ) : (
                <form onSubmit={handleSubmit} style={{ display: "grid", gap: "14px" }}>
                  <div>
                    <label style={{ fontSize: "12px", fontWeight: "700", color: "var(--text-main)", display: "block", marginBottom: "6px" }}>Category</label>
                    <select 
                      value={category} 
                      onChange={(e) => setCategory(e.target.value)}
                      style={{ width: "100%", padding: "9px", borderRadius: "8px", background: "var(--bg-toggle)", border: "1px solid var(--border-panel)", color: "var(--text-main)" }}
                    >
                      <option>Dashboard UI & Visualization</option>
                      <option>Fire Danger Index Accuracy</option>
                      <option>Misinformation Verification</option>
                      <option>Telemetry Data Latency</option>
                      <option>Other Suggestions</option>
                    </select>
                  </div>

                  <div>
                    <label style={{ fontSize: "12px", fontWeight: "700", color: "var(--text-main)", display: "block", marginBottom: "6px" }}>Experience Rating</label>
                    <div style={{ display: "flex", gap: "8px" }}>
                      {[1, 2, 3, 4, 5].map((star) => (
                        <button
                          type="button"
                          key={star}
                          onClick={() => setRating(star)}
                          style={{
                            border: 0,
                            background: "transparent",
                            cursor: "pointer",
                            color: star <= rating ? "#f59e0b" : "#64748b"
                          }}
                        >
                          <Star size={24} fill={star <= rating ? "#f59e0b" : "none"} />
                        </button>
                      ))}
                    </div>
                  </div>

                  <div>
                    <label style={{ fontSize: "12px", fontWeight: "700", color: "var(--text-main)", display: "block", marginBottom: "6px" }}>Detailed Comments</label>
                    <textarea 
                      rows={4} 
                      value={comment}
                      onChange={(e) => setComment(e.target.value)}
                      required
                      placeholder="Share your feedback, report UI issues or telemetry inconsistencies..."
                      style={{ width: "100%", padding: "10px", borderRadius: "8px", background: "var(--bg-toggle)", border: "1px solid var(--border-panel)", color: "var(--text-main)", fontSize: "13px" }}
                    />
                  </div>

                  <button 
                    type="submit" 
                    className="ff-sim-btn" 
                    style={{ justifySelf: "start", display: "inline-flex", alignItems: "center", gap: "8px", padding: "10px 18px" }}
                  >
                    <Send size={15} />
                    Submit Feedback
                  </button>
                </form>
              )}
            </div>
          </div>

          <div className="ff-column-right">
            <div className="ff-panel">
              <div className="ff-panel-header">
                <h3>Community Involvement</h3>
              </div>
              <p style={{ fontSize: "13px", color: "var(--text-toggle)", lineHeight: "1.6" }}>
                User feedback plays a crucial role in calibrating our predictive models and verifying crowdsourced incident flags across rural and regional Victoria.
              </p>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}
