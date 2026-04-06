import { useState, useEffect } from "react";
import { getRecentSearches, uploadImage } from "../api/searchApi";
import { getTrendingProducts } from "../api/productApi";
import useSearch from "../hooks/useSearch";
import SearchResult from "../components/SearchResult";
import Navbar from "../components/Navbar";

export default function Home() {
  const [activeTab, setActiveTab] = useState("image");
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [textQuery, setTextQuery] = useState("");
  const [uploadLoading, setUploadLoading] = useState(false);
  const [trending, setTrending] = useState([]);
  const [recentSearches, setRecentSearches] = useState([]);
  const [sideLoading, setSideLoading] = useState(false);
  const [uploadName, setUploadName] = useState("");
  const [uploadCategory, setUploadCategory] = useState("");
  const [showUploadForm, setShowUploadForm] = useState(false);

  const { results, loading, error, performImageSearch, performTextSearch } =
    useSearch();

  const USER_ID = "U123";

  const fetchSideData = async () => {
    setSideLoading(true);
    try {
      const [trendRes, recentRes] = await Promise.all([
        getTrendingProducts(),
        getRecentSearches(USER_ID),
      ]);
      setTrending(trendRes.data.trending_products || []);
      setRecentSearches(recentRes.data.recent_searches || []);
    } catch (err) {
      console.error(err);
    } finally {
      setSideLoading(false);
    }
  };

  const filteredRecent = recentSearches.filter(item => {
    if (activeTab === "image") {
      return item.searchType === "image";
    }
    return item.searchType === "text";
  });

  useEffect(() => {
    fetchSideData();
  }, []);

  const handleFileChange = (e) => {
    const selected = e.target.files[0];
    setFile(selected);
    if (selected) setPreview(URL.createObjectURL(selected));
    else setPreview(null);
  };

  const onSearch = async () => {
    if (activeTab === "image") await performImageSearch(file, USER_ID);
    else await performTextSearch(textQuery, USER_ID);
    fetchSideData();
  };

  const onUpload = async () => {
    if (!file) {
      alert("Please select an image first!");
      setActiveTab("image");
      document.getElementById("fileInput").click();
      return;
    }

    if (!showUploadForm) {
      setShowUploadForm(true);
      return;
    }

    setUploadLoading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("user_id", USER_ID);
      if (uploadName.trim()) formData.append("name", uploadName.trim());
      if (uploadCategory.trim()) formData.append("category", uploadCategory.trim());
      
      console.log("Uploading with:", { name: uploadName, category: uploadCategory });

      const res = await uploadImage(formData);

      if (res.data.is_duplicate) {
        alert("This product already exists!");
      } else {
        alert("Product uploaded successfully!");
      }

      setShowUploadForm(false);
      setUploadName("");
      setUploadCategory("");
      setFile(null);
      setPreview(null);
      fetchSideData();
    } catch (err) {
      console.error(err);
      alert("Upload failed. Please try again.");
    } finally {
      setUploadLoading(false);
    }
  };

  return (
    <div
      style={{
        backgroundColor: "var(--bg-main)",
        minHeight: "100vh",
        paddingBottom: "100px",
      }}>
      <Navbar />

      <main
        style={{ maxWidth: "850px", margin: "40px auto", padding: "0 16px" }}>
        {/* Main Search Container */}
        <div
          style={{
            backgroundColor: "white",
            padding: "24px",
            borderRadius: "var(--radius-lg)",
            boxShadow: "var(--shadow-md)",
            border: "1px solid var(--border-light)",
          }}
          className="search-container"
        >
          <div
            style={{
              display: "flex",
              gap: "10px",
              marginBottom: "24px",
              justifyContent: "center",
            }}>
            {["image", "text"].map((t) => (
              <button
                key={t}
                onClick={() => setActiveTab(t)}
                style={{
                  padding: "6px 20px",
                  borderRadius: "20px",
                  border: "none",
                  backgroundColor:
                    activeTab === t ? "var(--brand-light)" : "transparent",
                  color:
                    activeTab === t ?
                      "var(--brand-primary)"
                    : "var(--text-muted)",
                  fontWeight: "700",
                  cursor: "pointer",
                  fontSize: "12px",
                  transition: "all 0.2s",
                }}>
                {t.toUpperCase()}
              </button>
            ))}
          </div>

          {activeTab === "image" ?
            <div>
              <div
                style={{
                  border: "2px dashed #e2e8f0",
                  borderRadius: "var(--radius-md)",
                  padding: "24px",
                  cursor: "pointer",
                  marginBottom: showUploadForm ? "16px" : "20px",
                  backgroundColor: "#fcfdfe",
                  textAlign: "center",
                  minHeight: "120px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
                onClick={() => document.getElementById("fileInput").click()}>
                <input
                  id="fileInput"
                  type="file"
                  accept="image/*"
                  capture="environment"
                  style={{ display: "none" }}
                  onChange={handleFileChange}
                />
                {!preview ?
                  <p
                    style={{
                      color: "var(--text-muted)",
                      fontSize: "14px",
                      fontWeight: "500",
                      margin: 0,
                    }}>
                    Upload or drop product photo
                  </p>
                : <img
                    src={preview}
                    alt="preview"
                    style={{
                      maxWidth: "100%",
                      maxHeight: "200px",
                      borderRadius: "8px",
                    }}
                  />
                }
              </div>
              {showUploadForm && (
                <div style={{ display: "flex", gap: "12px", marginBottom: "20px", flexWrap: "wrap" }}>
                  <input
                    type="text"
                    placeholder="Product name (optional)"
                    value={uploadName}
                    onChange={(e) => setUploadName(e.target.value)}
                    style={{
                      flex: "1 1 45%",
                      minWidth: "140px",
                      padding: "10px 12px",
                      borderRadius: "8px",
                      border: "1px solid var(--border-light)",
                      fontSize: "14px",
                      outline: "none",
                    }}
                  />
                  <input
                    type="text"
                    placeholder="Category (optional)"
                    value={uploadCategory}
                    onChange={(e) => setUploadCategory(e.target.value)}
                    style={{
                      flex: "1 1 45%",
                      minWidth: "140px",
                      padding: "10px 12px",
                      borderRadius: "8px",
                      border: "1px solid var(--border-light)",
                      fontSize: "14px",
                      outline: "none",
                    }}
                  />
                </div>
              )}
            </div>
          : <div style={{ marginBottom: "20px" }}>
              <input
                type="text"
                placeholder="What are you looking for?"
                value={textQuery}
                onChange={(e) => setTextQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && onSearch()}
                style={{
                  width: "100%",
                  padding: "16px",
                  borderRadius: "12px",
                  border: "1px solid var(--border-light)",
                  fontSize: "16px",
                  boxSizing: "border-box",
                  outline: "none",
                }}
              />
            </div>
          }

          <div
            style={{
              display: "flex",
              gap: "12px",
              justifyContent: "center",
              marginBottom: "20px",
              flexWrap: "wrap",
            }}>
            <button
              onClick={onSearch}
              disabled={
                loading ||
                (activeTab === "image" && !file) ||
                (activeTab === "text" && !textQuery)
              }
              className="btn-primary"
              style={{ padding: "12px 24px", borderRadius: "30px", flex: "1 1 auto", minWidth: "140px" }}>
              {loading ? "Discovering..." : "Find Matches"}
            </button>

            {activeTab === "image" && (
              <button
                onClick={onUpload}
                disabled={uploadLoading || !file}
                className="btn-secondary"
                style={{ padding: "12px 24px", borderRadius: "30px", flex: "1 1 auto", minWidth: "140px" }}
              >
                {uploadLoading ? "Uploading..." : (showUploadForm ? "Confirm Upload" : "Upload Image")}
              </button>
            )}
          </div>

          {/* Recent Searches */}
          <div
            style={{
              borderTop: "1px solid #f1f5f9",
              paddingTop: "16px",
              display: "flex",
              alignItems: "center",
              gap: "12px",
              overflowX: "auto",
            }}>
            <span
              style={{
                fontSize: "12px",
                fontWeight: "700",
                color: "var(--text-muted)",
                whiteSpace: "nowrap",
              }}>
              RECENT:
            </span>
            <div style={{ display: "flex", gap: "8px" }}>
              {filteredRecent.slice(0, 5).map((item, i) => (
                <span
                  key={i}
                  onClick={() =>
                    item.searchType === "text" &&
                    (setTextQuery(item.queryText), setActiveTab("text"))
                  }
                  style={{
                    padding: "4px 12px",
                    backgroundColor: "#f8fafc",
                    borderRadius: "16px",
                    fontSize: "11px",
                    fontWeight: "600",
                    color: "var(--brand-primary)",
                    cursor: item.searchType === "text" ? "pointer" : "default",
                    whiteSpace: "nowrap",
                    border: "1px solid var(--border-light)",
                  }}>
                  {item.searchType === "text" ? item.queryText : item.category}
                </span>
              ))}
              {filteredRecent.length === 0 && (
                <span style={{ fontSize: "11px", color: "#cbd5e1" }}>
                  No recent searches
                </span>
              )}
            </div>
          </div>
        </div>

        <SearchResult results={results} loading={loading} error={error} />

        {/* Trending Section - Horizontal Card Grid */}
        {results.length === 0 && (
          <div style={{ marginTop: "60px" }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: "24px",
              }}>
              <h3
                style={{
                  fontSize: "20px",
                  margin: 0,
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                }}>
                <span style={{ fontSize: "22px" }}></span> Trending Products
              </h3>
              <button
                onClick={() => (window.location.href = "/products")}
                style={{
                  background: "none",
                  border: "none",
                  color: "var(--brand-primary)",
                  fontSize: "14px",
                  fontWeight: "700",
                  cursor: "pointer",
                }}>
                View All
              </button>
            </div>

            {sideLoading ?
              <p style={{ textAlign: "center", color: "var(--text-muted)" }}>
                Loading trends...
              </p>
            : <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(3, 1fr)",
                  gap: "24px",
                }}>
                {trending.slice(0, 6).map((item) => (
                  <div
                    key={item.productId}
                    style={{
                      backgroundColor: "white",
                      padding: "16px",
                      borderRadius: "var(--radius-md)",
                      boxShadow: "var(--shadow-sm)",
                      border: "1px solid var(--border-light)",
                      textAlign: "center",
                      cursor: "pointer",
                      transition: "transform 0.2s ease",
                    }}
                    onMouseOver={(e) =>
                      (e.currentTarget.style.transform = "translateY(-4px)")
                    }
                    onMouseOut={(e) =>
                      (e.currentTarget.style.transform = "translateY(0)")
                    }
                    onClick={() =>
                      (window.location.href = `/products/${item.id}`)
                    }>
                    <img
                      src={item.imageUrl}
                      style={{
                        width: "100%",
                        aspectRatio: "1",
                        objectFit: "cover",
                        borderRadius: "8px",
                        marginBottom: "12px",
                        border: "1px solid #f1f5f9",
                      }}
                    />
                    <p
                      style={{
                        margin: "0 0 4px 0",
                        fontWeight: "700",
                        fontSize: "14px",
                        color: "var(--text-main)",
                        whiteSpace: "nowrap",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                      }}>
                      {item.name}
                    </p>
                    <p
                      style={{
                        margin: 0,
                        fontSize: "12px",
                        color: "var(--text-muted)",
                        fontWeight: "500",
                      }}></p>
                  </div>
                ))}
              </div>
            }
          </div>
        )}
      </main>
    </div>
  );
}
