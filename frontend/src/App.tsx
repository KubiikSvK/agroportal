import { NavLink, Route, Routes } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import MapPage from "./pages/MapPage";
import RotationPage from "./pages/RotationPage";
import FinancePage from "./pages/FinancePage";
import PrecisionPage from "./pages/PrecisionPage";
import VehiclesPage from "./pages/VehiclesPage";
import WeatherPage from "./pages/WeatherPage";

const navItems = [
  { to: "/", label: "Dashboard" },
  { to: "/map", label: "Mapa" },
  { to: "/rotation", label: "Osev" },
  { to: "/finance", label: "Finance" },
  { to: "/precision", label: "Precision" },
  { to: "/vehicles", label: "Stroje" },
  { to: "/weather", label: "Počasí" },
];

export default function App() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand__title">AgroPortál</span>
          <span className="brand__subtitle">FS25 Multiplayer HQ</span>
        </div>
        <nav className="nav">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                isActive ? "nav__link nav__link--active" : "nav__link"
              }
              end={item.to === "/"}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="content">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/map" element={<MapPage />} />
          <Route path="/rotation" element={<RotationPage />} />
          <Route path="/finance" element={<FinancePage />} />
          <Route path="/precision" element={<PrecisionPage />} />
          <Route path="/vehicles" element={<VehiclesPage />} />
          <Route path="/weather" element={<WeatherPage />} />
        </Routes>
      </main>
    </div>
  );
}
