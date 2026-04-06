import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { getProductById, updateProduct, deleteProduct } from "../api/productApi";
import Navbar from "../components/Navbar";

export default function ProductDetails() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [product, setProduct] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [editForm, setEditForm] = useState({ name: "", category: "" });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const fetchProduct = async () => {
      try {
        const res = await getProductById(id);
        setProduct(res.data);
        setEditForm({ name: res.data.name || "", category: res.data.category || "" });
      } catch (err) {
        console.error("Failed to fetch product", err);
      } finally {
        setLoading(false);
      }
    };
    fetchProduct();
  }, [id]);

  const handleDelete = async () => {
    if (!window.confirm("Are you sure you want to delete this product?")) return;
    try {
      await deleteProduct(product.id, product.category);
      alert("Product deleted successfully");
      navigate("/products");
    } catch (err) {
      console.error("Delete failed", err);
      alert("Failed to delete product");
    }
  };

  const handleEdit = () => {
    setEditForm({ name: product.name || "", category: product.category || "" });
    setIsEditing(true);
  };

  const handleCancel = () => {
    setIsEditing(false);
  };

  const handleSave = async () => {
    if (!editForm.name.trim()) {
      alert("Product name is required");
      return;
    }
    if (!editForm.category.trim()) {
      alert("Category is required");
      return;
    }

    setSaving(true);
    try {
      const updateData = {
        name: editForm.name.trim(),
        category: editForm.category.trim(),
      };
      await updateProduct(product.id, product.category, updateData);
      setProduct({ ...product, ...updateData });
      setIsEditing(false);
      alert("Product updated successfully");
    } catch (err) {
      console.error("Update failed", err);
      alert("Failed to update product");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div style={{ backgroundColor: "var(--bg-main)", minHeight: "100vh" }}>
        <Navbar />
        <p style={{ padding: "40px", textAlign: "center", color: "var(--text-muted)" }}>
          Loading product details...
        </p>
      </div>
    );
  }

  if (!product) {
    return (
      <div style={{ backgroundColor: "var(--bg-main)", minHeight: "100vh" }}>
        <Navbar />
        <p style={{ padding: "40px", textAlign: "center", color: "var(--text-muted)" }}>
          Product not found
        </p>
      </div>
    );
  }

  return (
    <div style={{ backgroundColor: "var(--bg-main)", minHeight: "100vh" }}>
      <Navbar />
      <main style={{ maxWidth: "1000px", margin: "40px auto", padding: "0 16px" }}>
        <button
          onClick={() => navigate(-1)}
          style={{
            marginBottom: "20px",
            background: "none",
            border: "none",
            color: "var(--brand-primary)",
            cursor: "pointer",
            fontWeight: "600",
            fontSize: "14px",
            display: "flex",
            alignItems: "center",
            gap: "4px",
          }}
        >
          ← Back
        </button>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "40px",
            backgroundColor: "white",
            padding: "32px",
            borderRadius: "16px",
            boxShadow: "var(--shadow-sm)",
            border: "1px solid var(--border-light)",
          }}
          className="product-grid"
        >
          <div style={{ position: "relative" }}>
            <img
              src={product.imageUrl}
              alt={product.name}
              style={{
                width: "100%",
                borderRadius: "12px",
                border: "1px solid var(--border-light)",
                objectFit: "cover",
              }}
              onError={(e) => {
                e.target.style.display = "none";
                e.target.nextSibling.style.display = "flex";
              }}
            />
            <div
              style={{
                display: "none",
                width: "100%",
                height: "300px",
                backgroundColor: "#f8fafc",
                borderRadius: "12px",
                alignItems: "center",
                justifyContent: "center",
                color: "var(--text-muted)",
              }}
            >
              No Image Available
            </div>
          </div>

          <div>
            {isEditing ? (
              <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                <div>
                  <label
                    style={{
                      display: "block",
                      fontSize: "12px",
                      fontWeight: "600",
                      color: "var(--text-muted)",
                      marginBottom: "6px",
                      textTransform: "uppercase",
                    }}
                  >
                    Product Name
                  </label>
                  <input
                    type="text"
                    value={editForm.name}
                    onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                    style={{
                      width: "100%",
                      padding: "12px",
                      borderRadius: "8px",
                      border: "1px solid var(--border-light)",
                      fontSize: "16px",
                      outline: "none",
                    }}
                    placeholder="Enter product name"
                  />
                </div>

                <div>
                  <label
                    style={{
                      display: "block",
                      fontSize: "12px",
                      fontWeight: "600",
                      color: "var(--text-muted)",
                      marginBottom: "6px",
                      textTransform: "uppercase",
                    }}
                  >
                    Category
                  </label>
                  <input
                    type="text"
                    value={editForm.category}
                    onChange={(e) => setEditForm({ ...editForm, category: e.target.value })}
                    style={{
                      width: "100%",
                      padding: "12px",
                      borderRadius: "8px",
                      border: "1px solid var(--border-light)",
                      fontSize: "16px",
                      outline: "none",
                    }}
                    placeholder="Enter category"
                  />
                </div>

                <div style={{ display: "flex", gap: "12px", marginTop: "8px" }}>
                  <button
                    onClick={handleSave}
                    disabled={saving}
                    style={{
                      flex: 1,
                      padding: "12px 20px",
                      backgroundColor: "var(--brand-primary)",
                      color: "white",
                      border: "none",
                      borderRadius: "8px",
                      fontWeight: "600",
                      cursor: saving ? "not-allowed" : "pointer",
                      opacity: saving ? 0.7 : 1,
                    }}
                  >
                    {saving ? "Saving..." : "Save Changes"}
                  </button>
                  <button
                    onClick={handleCancel}
                    disabled={saving}
                    style={{
                      flex: 1,
                      padding: "12px 20px",
                      backgroundColor: "white",
                      color: "var(--text-main)",
                      border: "1px solid var(--border-light)",
                      borderRadius: "8px",
                      fontWeight: "600",
                      cursor: "pointer",
                    }}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <>
                <span
                  style={{
                    fontSize: "12px",
                    color: "var(--brand-primary)",
                    fontWeight: "700",
                    textTransform: "uppercase",
                    letterSpacing: "1px",
                  }}
                >
                  {product.category}
                </span>
                <h1 style={{ marginTop: "10px", marginBottom: "20px", fontSize: "28px" }}>
                  {product.name}
                </h1>

                <div style={{ marginBottom: "24px" }}>
                  <h3 style={{ fontSize: "14px", marginBottom: "10px", color: "var(--text-muted)" }}>
                    Detected Brands
                  </h3>
                  <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                    {product.brands?.length > 0 ? (
                      product.brands.map((b) => (
                        <span
                          key={b}
                          style={{
                            padding: "4px 12px",
                            backgroundColor: "#f0f0f0",
                            borderRadius: "4px",
                            fontSize: "13px",
                          }}
                        >
                          {b}
                        </span>
                      ))
                    ) : (
                      <p style={{ fontSize: "14px", color: "var(--text-muted)" }}>No brands detected</p>
                    )}
                  </div>
                </div>

                <div style={{ marginBottom: "24px" }}>
                  <h3 style={{ fontSize: "14px", marginBottom: "10px", color: "var(--text-muted)" }}>
                    AI Tags
                  </h3>
                  <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                    {product.tags?.map((t) => (
                      <span
                        key={t.name}
                        style={{
                          padding: "4px 12px",
                          backgroundColor: "var(--brand-light)",
                          color: "var(--brand-primary)",
                          borderRadius: "4px",
                          fontSize: "13px",
                          fontWeight: "500",
                        }}
                      >
                        {t.name} ({(t.confidence * 100).toFixed(0)}%)
                      </span>
                    ))}
                  </div>
                </div>

                {product.ocr_text && (
                  <div style={{ marginBottom: "24px" }}>
                    <h3 style={{ fontSize: "14px", marginBottom: "10px", color: "var(--text-muted)" }}>
                      Detected Text
                    </h3>
                    <p
                      style={{
                        padding: "12px",
                        backgroundColor: "#fafafa",
                        borderRadius: "8px",
                        border: "1px solid var(--border-light)",
                        fontSize: "14px",
                        fontStyle: "italic",
                        margin: 0,
                      }}
                    >
                      "{product.ocr_text}"
                    </p>
                  </div>
                )}

                <div
                  style={{
                    marginTop: "32px",
                    paddingTop: "20px",
                    borderTop: "1px solid var(--border-light)",
                    display: "flex",
                    gap: "12px",
                  }}
                >
                  <button
                    onClick={handleEdit}
                    style={{
                      padding: "10px 20px",
                      backgroundColor: "var(--brand-primary)",
                      color: "white",
                      border: "none",
                      borderRadius: "8px",
                      fontWeight: "600",
                      cursor: "pointer",
                    }}
                  >
                    Edit Product
                  </button>
                  <button
                    onClick={handleDelete}
                    style={{
                      padding: "10px 20px",
                      backgroundColor: "#fee2e2",
                      color: "#ef4444",
                      border: "none",
                      borderRadius: "8px",
                      fontWeight: "600",
                      cursor: "pointer",
                    }}
                  >
                    Delete Product
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </main>

      <style>{`
        @media (max-width: 768px) {
          .product-grid {
            grid-template-columns: 1fr !important;
            padding: 20px !important;
            gap: 24px !important;
          }
        }
      `}</style>
    </div>
  );
}
