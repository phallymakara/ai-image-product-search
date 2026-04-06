import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import logo from "../assets/logo_proseth.svg";

export default function Navbar() {
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);

  const isActive = (path) => location.pathname === path;

  const navItemStyle = (path) => ({
    textDecoration: "none",
    color: isActive(path) ? "white" : "rgba(255, 255, 255, 0.8)",
    fontWeight: isActive(path) ? "700" : "500",
    padding: "8px 16px",
    borderRadius: "6px",
    backgroundColor:
      isActive(path) ? "rgba(255, 255, 255, 0.2)" : "transparent",
    transition: "all 0.2s ease",
    fontSize: "14px",
  });

  return (
    <nav
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        padding: "0 20px",
        height: "64px",
        background: "linear-gradient(135deg, #006e64 0%, #01a056 100%)",
        boxShadow: "0 2px 10px rgba(0, 0, 0, 0.1)",
        color: "white",
        position: "sticky",
        top: 0,
        zIndex: 1000,
      }}>
      <div style={{ display: "flex", alignItems: "center" }}>
        <Link
          to="/"
          style={{
            textDecoration: "none",
            color: "white",
            display: "flex",
            alignItems: "center",
            gap: "10px",
          }}>
          <img src={logo} style={{ width: "150px", height: "40px" }} />
        </Link>
      </div>

      <div style={{ display: "flex", gap: "8px" }} className="desktop-nav">
        <Link to="/" style={navItemStyle("/")}>
          Home
        </Link>
        <Link to="/products" style={navItemStyle("/products")}>
          Browse
        </Link>
        <Link to="/history" style={navItemStyle("/history")}>
          History
        </Link>
      </div>

      <button
        onClick={() => setMenuOpen(!menuOpen)}
        style={{
          display: "none",
          background: "none",
          border: "none",
          color: "white",
          fontSize: "24px",
          cursor: "pointer",
          padding: "8px",
        }}
        className="mobile-menu-btn"
      >
        {menuOpen ? "✕" : "☰"}
      </button>

      {menuOpen && (
        <div
          style={{
            position: "absolute",
            top: "64px",
            left: 0,
            right: 0,
            background: "linear-gradient(135deg, #006e64 0%, #01a056 100%)",
            padding: "16px 20px",
            display: "flex",
            flexDirection: "column",
            gap: "8px",
            boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
          }}
          className="mobile-menu"
        >
          <Link
            to="/"
            onClick={() => setMenuOpen(false)}
            style={navItemStyle("/")}
          >
            Home
          </Link>
          <Link
            to="/products"
            onClick={() => setMenuOpen(false)}
            style={navItemStyle("/products")}
          >
            Browse
          </Link>
          <Link
            to="/history"
            onClick={() => setMenuOpen(false)}
            style={navItemStyle("/history")}
          >
            History
          </Link>
        </div>
      )}

      <style>{`
        @media (max-width: 640px) {
          .desktop-nav {
            display: none !important;
          }
          .mobile-menu-btn {
            display: block !important;
          }
        }
      `}</style>
    </nav>
  );
}
