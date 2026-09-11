import { useEffect, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { api } from "../api/client";
import { useAsync } from "../state/useAsync";
import { FilterRail } from "./FilterRail";
import "./Shell.css";

type Theme = "system" | "light" | "dark";

const NAV = [
  { to: "/", label: "Overview", end: true },
  { to: "/studies", label: "Studies", end: false },
  { to: "/query", label: "Query", end: false },
];

export function Shell() {
  const health = useAsync(() => api.health(), []);
  // The console ships dark: the chart palette's dark steps all clear contrast
  // against this surface while three light steps do not. Following the OS by
  // default would hand most readers the weaker palette, so light and system are
  // opt-in rather than the starting point.
  const [theme, setTheme] = useState<Theme>(
    () => (localStorage.getItem("abcd-theme") as Theme) ?? "dark",
  );

  useEffect(() => {
    const root = document.documentElement;
    if (theme === "system") root.removeAttribute("data-theme");
    else root.setAttribute("data-theme", theme);
    localStorage.setItem("abcd-theme", theme);
  }, [theme]);

  return (
    <div className="shell">
      <header className="shell__bar">
        <div className="shell__brand">
          <span className="shell__mark" aria-hidden="true" />
          <span className="shell__name">ABCD</span>
          <span className="shell__tagline">B-cell receptor repertoires</span>
        </div>

        <nav className="shell__nav" aria-label="Main">
          {NAV.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.end}>
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="shell__meta">
          {health.data && (
            <span
              className="shell__status"
              title={`Read-only connection as ${health.data.database.connected_as}`}
            >
              <span className="num">{health.data.database.bcrs.toLocaleString("en")}</span>
              <span className="shell__status-unit">receptors</span>
            </span>
          )}

          <select
            className="shell__theme"
            value={theme}
            onChange={(event) => setTheme(event.target.value as Theme)}
            aria-label="Colour theme"
          >
            <option value="dark">Dark</option>
            <option value="light">Light</option>
            <option value="system">Match system</option>
          </select>
        </div>
      </header>

      {health.error && (
        <p className="shell__offline">
          The API is not responding ({health.error.message}). Start it with{" "}
          <code>uvicorn app.main:app</code> from the <code>api</code> directory.
        </p>
      )}

      <div className="shell__body">
        <FilterRail />
        <main className="shell__main">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
