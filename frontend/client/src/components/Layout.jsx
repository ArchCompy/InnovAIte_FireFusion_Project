import Sidebar from "./Sidebar";
import Topbar from "./Topbar";
import Footer from "./Footer";
import { useSidebarCollapse } from "./SidebarCollapseContext";

export default function Layout({ children, title = "Dashboard", showTopbar = true, showFooter = true }) {
  const { collapsed, toggle } = useSidebarCollapse();

  return (
    <div className="dashboard-shell">
      <Sidebar collapsed={collapsed} onToggle={toggle} />

      <main className={`main${collapsed ? " sidebar-collapsed" : ""}`}>
        {showTopbar && <Topbar title={title} />}

        {children}

        {showFooter && <Footer />}
      </main>
    </div>
  );
}