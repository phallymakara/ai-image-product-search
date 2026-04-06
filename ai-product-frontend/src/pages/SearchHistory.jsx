import { useEffect, useState } from "react";
import { getSearchHistory, deleteHistory } from "../api/searchApi";
import Navbar from "../components/Navbar";

export default function SearchHistory() {
  const [history, setHistory] = useState({});
  const [filteredHistory, setFilteredHistory] = useState({});
  const [loading, setLoading] = useState(true);
  const [dateFilter, setDateFilter] = useState("");
  const [activeTab, setActiveTab] = useState("all");

  const userId = "U123";

  const fetchHistory = async () => {
    try {
      const res = await getSearchHistory(userId);
      setHistory(res.data.history);
      setFilteredHistory(res.data.history);
    } catch (err) {
      console.error("Failed to fetch history", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  useEffect(() => {
    let filtered = {};

    Object.entries(history).forEach(([date, items]) => {
      let filteredItems = items;

      if (activeTab !== "all") {
        filteredItems = items.filter(item => item.searchType === activeTab);
      }

      if (dateFilter && date !== dateFilter) {
        filteredItems = [];
      }

      if (filteredItems.length > 0) {
        filtered[date] = filteredItems;
      }
    });

    setFilteredHistory(filtered);
  }, [dateFilter, history, activeTab]);

  const handleDelete = async (searchId) => {
    try {
      await deleteHistory(userId, searchId);
      fetchHistory();
    } catch (err) {
      console.error("Delete failed", err);
    }
  };

  const formatDate = (dateStr) => {
    const date = new Date(dateStr);
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);

    if (date.toDateString() === today.toDateString()) return "Today";
    if (date.toDateString() === yesterday.toDateString()) return "Yesterday";
    return date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  };

  return (
    <div style={{ backgroundColor: "var(--bg-main)", minHeight: "100vh" }}>
      <Navbar />
      <main style={{ maxWidth: "1000px", margin: "24px auto", padding: "0 16px" }}>
        <h1 style={{ fontSize: "24px", fontWeight: "700", marginBottom: "20px", color: "var(--text-main)" }}>
          Search History
        </h1>

        <div style={{ display: "flex", gap: "12px", marginBottom: "24px", flexWrap: "wrap" }}>
          <div style={{ display: "flex", backgroundColor: "white", borderRadius: "10px", border: "1px solid var(--border-light)", overflow: "hidden" }}>
            {["all", "image", "text"].map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                style={{
                  padding: "8px 16px",
                  border: "none",
                  backgroundColor: activeTab === tab ? "var(--brand-primary)" : "transparent",
                  color: activeTab === tab ? "white" : "var(--text-muted)",
                  fontWeight: "600",
                  fontSize: "13px",
                  cursor: "pointer",
                  textTransform: "capitalize",
                }}>
                {tab === "all" ? "All" : tab === "image" ? "Image" : "Text"}
              </button>
            ))}
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "8px", backgroundColor: "white", padding: "6px 12px", borderRadius: "10px", border: "1px solid var(--border-light)", flexWrap: "wrap" }}>
            <span style={{ fontSize: "13px", fontWeight: "600", color: "var(--text-muted)" }}>Date:</span>
            <input
              type="date"
              value={dateFilter}
              onChange={(e) => setDateFilter(e.target.value)}
              style={{
                padding: "8px",
                borderRadius: "8px",
                border: "1px solid var(--border-light)",
                outline: "none",
                fontSize: "14px",
                color: "var(--text-main)",
                cursor: "pointer",
              }}
            />
            {dateFilter && (
              <button
                onClick={() => setDateFilter("")}
                style={{
                  background: "none",
                  border: "none",
                  color: "var(--brand-primary)",
                  cursor: "pointer",
                  fontSize: "14px",
                  fontWeight: "600",
                }}>
                Clear
              </button>
            )}
          </div>
        </div>

        {loading ? (
          <div style={{ textAlign: "center", padding: "60px" }}>
            <p style={{ color: "var(--text-muted)" }}>Loading...</p>
          </div>
        ) : Object.keys(filteredHistory).length === 0 ? (
          <div style={{
            textAlign: "center",
            padding: "60px 20px",
            backgroundColor: "white",
            borderRadius: "16px",
            border: "1px solid var(--border-light)",
          }}>
            <div style={{
              width: "80px",
              height: "80px",
              backgroundColor: "#f8fafc",
              borderRadius: "50%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              margin: "0 auto 20px",
            }}>
              <span style={{ fontSize: "32px", color: "var(--text-muted)" }}>—</span>
            </div>
            <h3 style={{ margin: "0 0 8px 0", color: "var(--text-main)", fontSize: "18px" }}>
              No search history yet
            </h3>
            <p style={{ margin: 0, color: "var(--text-muted)", fontSize: "14px" }}>
              Your recent searches will appear here
            </p>
          </div>
        ) : (
          Object.entries(filteredHistory).map(([date, items]) => (
            <div key={date} style={{ marginBottom: "40px" }}>
              <h2 style={{
                fontSize: "16px",
                fontWeight: "700",
                color: "var(--text-muted)",
                marginBottom: "16px",
                textTransform: "uppercase",
                letterSpacing: "0.5px",
              }}>
                {formatDate(date)}
              </h2>

              <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                {items.map((item) => (
                  <div
                    key={item.searchId}
                    style={{
                      backgroundColor: "white",
                      borderRadius: "12px",
                      padding: "12px 16px",
                      border: "1px solid var(--border-light)",
                      display: "flex",
                      alignItems: "center",
                      gap: "12px",
                      transition: "all 0.2s",
                      flexWrap: "wrap",
                    }}
                    onMouseOver={(e) => e.currentTarget.style.boxShadow = "0 4px 12px rgba(0,0,0,0.08)"}
                    onMouseOut={(e) => e.currentTarget.style.boxShadow = "none"}
                  >
                    <div style={{
                      width: "48px",
                      height: "48px",
                      borderRadius: "10px",
                      overflow: "hidden",
                      flexShrink: 0,
                      backgroundColor: "#f8fafc",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                    }}>
                      {item.searchImageUrl ? (
                        <img
                          src={item.searchImageUrl}
                          alt="search"
                          style={{ width: "100%", height: "100%", objectFit: "cover" }}
                        />
                      ) : (
                        <span style={{ fontSize: "20px", color: "var(--text-muted)" }}>
                          {item.searchType === "text" ? "Aa" : ""}
                        </span>
                      )}
                    </div>

                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "4px" }}>
                        <span style={{
                          fontSize: "9px",
                          fontWeight: "700",
                          padding: "2px 6px",
                          borderRadius: "4px",
                          backgroundColor: item.searchType === "image" ? "#dbeafe" : "#fce7f3",
                          color: item.searchType === "image" ? "#1d4ed8" : "#be185d",
                          textTransform: "uppercase",
                        }}>
                          {item.searchType}
                        </span>
                        <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                          {new Date(item.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                        </span>
                      </div>
                      <p style={{
                        margin: 0,
                        fontSize: "14px",
                        fontWeight: "600",
                        color: "var(--text-main)",
                        whiteSpace: "nowrap",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                      }}>
                        {item.searchType === "text" ? item.queryText : (item.category || "Unknown category")}
                      </p>
                    </div>

                    <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                      {item.topMatch && (
                        <div style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "8px",
                          padding: "6px 10px",
                          backgroundColor: "#f8fafc",
                          borderRadius: "8px",
                        }} className="hide-on-mobile">
                          <img
                            src={item.topMatch.imageUrl}
                            alt="match"
                            style={{
                              width: "32px",
                              height: "32px",
                              borderRadius: "6px",
                              objectFit: "cover",
                            }}
                          />
                          <div>
                            <p style={{
                              margin: 0,
                              fontSize: "12px",
                              fontWeight: "600",
                              color: "var(--text-main)",
                              maxWidth: "100px",
                              whiteSpace: "nowrap",
                              overflow: "hidden",
                              textOverflow: "ellipsis",
                            }}>
                              {item.topMatch.name}
                            </p>
                            <p style={{
                              margin: 0,
                              fontSize: "10px",
                              fontWeight: "700",
                              color: "var(--brand-secondary)",
                            }}>
                              {(item.topMatch.match_score * 100).toFixed(0)}% match
                            </p>
                          </div>
                        </div>
                      )}

                      <button
                        onClick={() => handleDelete(item.searchId)}
                        style={{
                          padding: "6px 12px",
                          backgroundColor: "transparent",
                          border: "1px solid #fee2e2",
                          color: "#ef4444",
                          borderRadius: "6px",
                          cursor: "pointer",
                          fontSize: "12px",
                          fontWeight: "600",
                          flexShrink: 0,
                        }}
                        onMouseOver={(e) => {
                          e.currentTarget.style.backgroundColor = "#fef2f2";
                        }}
                        onMouseOut={(e) => {
                          e.currentTarget.style.backgroundColor = "transparent";
                        }}
                      >
                        Remove
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))
        )}
      </main>
    </div>
  );
}
