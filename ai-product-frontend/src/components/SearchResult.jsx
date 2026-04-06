import ProductCard from "./ProductCard";

export default function SearchResult({ results, loading, error, status }) {
  if (loading) return (
    <div style={{ 
      textAlign: "center", 
      padding: "60px 40px",
      backgroundColor: "white",
      borderRadius: "var(--radius-lg)",
      marginTop: "40px",
      boxShadow: "var(--shadow-sm)",
      border: "1px solid var(--border-light)",
      animation: "pulse 2s infinite ease-in-out"
    }}>
      {/* Animated Pulse Ring */}
      <div style={{ position: "relative", width: "80px", height: "80px", margin: "0 auto 24px" }}>
        <div style={{ 
          position: "absolute",
          width: "100%",
          height: "100%",
          borderRadius: "50%",
          background: "var(--brand-light)",
          animation: "scalePulse 1.5s infinite"
        }} />
        <div style={{ 
          position: "relative",
          width: "60px",
          height: "60px",
          border: "4px solid var(--border-light)",
          borderTop: "4px solid var(--brand-primary)",
          borderRadius: "50%",
          animation: "spin 0.8s linear infinite",
          margin: "10px"
        }} />
      </div>
      
      <p style={{ 
        color: "var(--brand-primary)", 
        fontWeight: "700", 
        fontSize: "15px",
        marginBottom: "8px"
      }}>
        {status || "Discovering matches..."}
      </p>
      
      {/* Simulated Progress Bar */}
      <div style={{ 
        width: "240px", 
        height: "6px", 
        backgroundColor: "#f1f5f9", 
        borderRadius: "10px", 
        margin: "16px auto 0",
        overflow: "hidden"
      }}>
        <div style={{ 
          width: "70%", 
          height: "100%", 
          background: "var(--brand-gradient)", 
          borderRadius: "10px",
          animation: "loadingBar 2.5s infinite ease-in-out"
        }} />
      </div>

      <style>{`
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        @keyframes scalePulse { 0% { transform: scale(0.8); opacity: 0.5; } 50% { transform: scale(1.2); opacity: 0.2; } 100% { transform: scale(0.8); opacity: 0.5; } }
        @keyframes pulse { 0% { transform: scale(1); } 50% { transform: scale(0.99); } 100% { transform: scale(1); } }
        @keyframes loadingBar { 
          0% { width: 0%; transform: translateX(-100%); } 
          50% { width: 100%; transform: translateX(0); } 
          100% { width: 0%; transform: translateX(100%); } 
        }
      `}</style>
    </div>
  );
  
  if (error) return (
    <div style={{ textAlign: "center", padding: "30px", background: "#fef2f2", borderRadius: "12px", border: "1px solid #fee2e2", color: "#b91c1c", marginTop: "40px" }}>
      <p style={{ fontWeight: "600" }}>{error}</p>
    </div>
  );
  
  if (!results || results.length === 0) return null;

  return (
    <div style={{ marginTop: "50px", animation: "fadeIn 0.5s ease" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px" }}>
        <h2 style={{ fontSize: "20px" }}>Match Results</h2>
        <span style={{ backgroundColor: "var(--bg-main)", padding: "4px 12px", borderRadius: "20px", fontSize: "12px", fontWeight: "600", color: "var(--text-muted)" }}>
          {results.length} items
        </span>
      </div>
      <div style={{ 
        display: "grid", 
        gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", 
        gap: "24px" 
      }}>
        {results.map((product) => (
          <ProductCard key={product.id || product.productId} product={product} />
        ))}
      </div>
      <style>{`@keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }`}</style>
    </div>
  );
}
