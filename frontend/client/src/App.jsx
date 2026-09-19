import MisinformationReview from "./pages/MisinformationReview.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import FireRiskMap from "./pages/FireRiskMap.tsx";
import Login from "./pages/Login.jsx";
import Signup from "./pages/Signup.jsx";
import Settings from "./pages/Settings.jsx";
import MisinfoLandingPage from "./pages/MisinformationLanding.jsx";
import Analytics from "./pages/Analytics.jsx";
import EmergencyAdvice from "./pages/EmergencyAdvice.jsx";
import BushfireForecastDetails from "./pages/BushfireForecastDetails.jsx";
import DataSourcesMethod from "./pages/DataSourcesMethod.jsx";
import AboutUs from "./pages/AboutUs.jsx";
import Feedback from "./pages/Feedback.jsx";
import { SidebarCollapseProvider } from "./components/SidebarCollapseContext.jsx";

export default function App() {
  const path = window.location.pathname;

  const renderContent = () => {
    if (path === "/fire-map") {
      return <FireRiskMap />;
    }

    if (path === "/misinfo-review") {
      return <MisinformationReview />;
    }

    if (path === "/misinformation-review") {
      return <MisinformationReview />;
    }

    if (path === "/misinfo") {
      return <MisinfoLandingPage />;
    }

    if (path === "/analytics") {
      return <Analytics />;
    }

    if (path === "/emergency-advice") {
      return <EmergencyAdvice />;
    }

    if (path === "/bushfire-forecast") {
      return <BushfireForecastDetails />;
    }

    if (path === "/data-sources") {
      return <DataSourcesMethod />;
    }

    if (path === "/about") {
      return <AboutUs />;
    }

    if (path === "/feedback") {
      return <Feedback />;
    }

    if (path === "/login") {
      return <Login />;
    }

    if (path === "/signup") {
      return <Signup />;
    }

    if (path === "/settings") {
      return <Settings />;
    }

    return <Dashboard />;
  };

  return (
    <SidebarCollapseProvider>
      {renderContent()}
    </SidebarCollapseProvider>
  );
}