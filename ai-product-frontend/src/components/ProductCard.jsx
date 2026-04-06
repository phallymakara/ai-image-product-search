import { useNavigate } from "react-router-dom";

export default function ProductCard({ product }) {
  const navigate = useNavigate();

  return (
    <div
      onClick={() => navigate(`/products/${product.id}`)}
      style={{
        display: "flex",
        flexDirection: "column",
        backgroundColor: "white",
        borderRadius: "var(--radius-md)",
        overflow: "hidden",
        boxShadow: "var(--shadow-sm)",
        border: "1px solid var(--border-light)",
        cursor: "pointer",
        transition: "transform 0.25s ease, boxShadow 0.25s ease",
      }}
      onMouseOver={(e) => {
        e.currentTarget.style.transform = "translateY(-6px)";
        e.currentTarget.style.boxShadow = "var(--shadow-lg)";
      }}
      onMouseOut={(e) => {
        e.currentTarget.style.transform = "translateY(0)";
        e.currentTarget.style.boxShadow = "var(--shadow-sm)";
      }}
    >
      <div style={{ position: "relative", width: "100%", paddingTop: "100%", overflow: "hidden" }}>
        <img
          src={product.imageUrl || "https://via.placeholder.com/300"}
          alt={product.name}
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            width: "100%",
            height: "100%",
            objectFit: "cover",
            backgroundColor: "#f8fafc"
          }}
        />
        {product.match_score !== undefined && (
          <div style={{
            position: "absolute",
            top: "8px",
            right: "8px",
            background: "rgba(255, 255, 255, 0.95)",
            color: "var(--brand-primary)",
            padding: "3px 8px",
            borderRadius: "12px",
            fontSize: "10px",
            fontWeight: "800",
            boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
            backdropFilter: "blur(4px)",
            border: "1px solid var(--brand-secondary)"
          }}>
            {(product.match_score * 100).toFixed(0)}% MATCH
          </div>
        )}
      </div>

      <div style={{ padding: "12px" }}>
        <span style={{ 
          fontSize: "10px", 
          textTransform: "uppercase", 
          fontWeight: "700", 
          color: "var(--text-muted)",
          letterSpacing: "0.05em",
          marginBottom: "4px",
          display: "block"
        }}>
          {product.category}
        </span>
        <h3 style={{ 
          margin: "0 0 8px 0", 
          color: "var(--text-main)", 
          fontSize: "14px",
          lineHeight: "1.4",
          height: "2.8em",
          overflow: "hidden",
          display: "-webkit-box",
          WebkitLineClamp: 2,
          WebkitBoxOrient: "vertical"
        }}>
          {product.name}
        </h3>
        
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "8px" }}>
          <div style={{ display: "flex", gap: "4px", overflow: "hidden" }}>
            {product.brands?.slice(0, 1).map(b => (
              <span key={b} style={{ fontSize: "11px", color: "var(--text-muted)", fontWeight: "500", whiteSpace: "nowrap" }}>{b}</span>
            ))}
          </div>
          <span style={{ color: "var(--brand-primary)", fontSize: "16px", fontWeight: "bold" }}>→</span>
        </div>
      </div>
    </div>
  );
}
