import {
  Home,
  Map,
  Shield,
  FileText,
  Bell,
  Settings,
  LogOut,
  Thermometer,
  Wind,
  Droplets,
  Eye,
  ChevronRight,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react";

const menuItems = [
  {
    label: "Dashboard",
    icon: Home,
    badge: null,
    path: "/",
    activePaths: ["/", "/dashboard"],
  },
  {
    label: "Fire Map",
    icon: Map,
    badge: "7",
    path: "/fire-map",
    activePaths: ["/fire-map"],
  },
  {
    label: "Misinformation Review",
    icon: Shield,
    badge: "14",
    path: "/misinfo",
    activePaths: ["/misinfo", "/misinfo-review", "/misinformation-review"],
  },
  {
    label: "Reports",
    icon: FileText,
    badge: null,
    path: "/analytics",
    activePaths: ["/analytics", "/reports"],
  },
];

function InfoBox({ icon: Icon, title, value }) {
  return (
    <div className="info-box">
      <Icon size={16} />
      <div className="info-box-copy">
        <span className="info-box-title">{title}</span>
        <b className="info-box-value">{value}</b>
      </div>
    </div>
  );
}

export default function Sidebar({ collapsed, onToggle }) {
  const currentPath = window.location.pathname;

  const handleNavigate = (path) => {
    window.location.href = path;
  };

  const handleSignOut = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    sessionStorage.clear();

    window.location.replace("/login");
  };

  return (
    <aside className={`sidebar${collapsed ? " collapsed" : ""}`}>
      <div className="sidebar-header">
        <div className="brand">
          <div className="brand-logo">FF</div>

          {!collapsed && (
            <div>
              <h1>FireFusion</h1>
              <p>Emergency Operations</p>
            </div>
          )}
        </div>

        <button
          className="sidebar-toggle"
          onClick={onToggle}
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? (
            <PanelLeftOpen size={18} />
          ) : (
            <PanelLeftClose size={18} />
          )}
        </button>
      </div>

      {!collapsed && <p className="section-title">Main Menu</p>}

      <nav className={`nav-list${collapsed ? " nav-list--collapsed" : ""}`}>
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = item.activePaths.includes(currentPath);

          return (
            <button
              key={item.label}
              className={`nav-item ${isActive ? "active" : ""}${
                collapsed ? " nav-item--icon-only" : ""
              }`}
              title={collapsed ? item.label : undefined}
              onClick={() => handleNavigate(item.path)}
            >
              <span>
                <Icon size={17} />
                {!collapsed && item.label}
              </span>

              {!collapsed && item.badge && <b>{item.badge}</b>}
              {!collapsed && isActive && <ChevronRight size={16} />}
            </button>
          );
        })}
      </nav>

      {!collapsed && (
        <>
          <div className="ban-card">
            <h3>
              <span></span>Total Fire Ban
            </h3>
            <p>No fires permitted</p>
            <small>Catastrophic conditions.</small>
          </div>

          <div className="weather-grid">
            <InfoBox icon={Thermometer} title="Temperature" value="42°C" />
            <InfoBox icon={Wind} title="Wind Speed" value="45 km/h" />
            <InfoBox icon={Droplets} title="Humidity" value="18%" />
            <InfoBox icon={Eye} title="Visibility" value="3 km" />
          </div>

          <p className="last-update">Last updated: 14:30</p>

          <div className="sidebar-bottom">
            <p className="section-title">System</p>

            <button className="nav-item" title="View emergency system notifications">
              <span>
                <Bell size={17} /> Notifications
              </span>
              <b>3</b>
            </button>

            <button
              className={`nav-item ${
                currentPath === "/settings" ? "active" : ""
              }`}
              onClick={() => handleNavigate("/settings")}
            >
              <span>
                <Settings size={17} /> Settings
              </span>
            </button>

            <div className="profile-card">
              <div>JD</div>
              <span>
                <strong>Gaveesha Nuwansara</strong>
                <small>Emergency Manager</small>
              </span>
            </div>

            <button className="signout" onClick={handleSignOut}>
              <LogOut size={16} />
              Sign Out
            </button>

            <small className="version">
              Version 2.4.1
              <br />
              Last sync: 2 min ago
            </small>
          </div>
        </>
      )}
    </aside>
  );
}