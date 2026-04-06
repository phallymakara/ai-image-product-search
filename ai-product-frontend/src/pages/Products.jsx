import { useEffect, useState } from "react";
import { getProducts, getCategories, updateProduct, deleteProduct } from "../api/productApi";
import Navbar from "../components/Navbar";
import ProductCard from "../components/ProductCard";

export default function Products() {
  const [products, setProducts] = useState([]);
  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState("");
  const [loading, setLoading] = useState(false);
  const [limit] = useState(12);
  const [offset, setOffset] = useState(0);
  const [editingProduct, setEditingProduct] = useState(null);
  const [editForm, setEditForm] = useState({ name: "", category: "" });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const fetchCats = async () => {
      try {
        const res = await getCategories();
        setCategories(res.data.categories || []);
      } catch (e) {
        console.error(e);
      }
    };
    fetchCats();
  }, []);

  const fetchProducts = async () => {
    setLoading(true);
    try {
      const res = await getProducts(selectedCategory, limit, offset);
      setProducts(res.data.products || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProducts();
  }, [offset, selectedCategory]);

  const handleEdit = (product) => {
    setEditingProduct(product);
    setEditForm({ name: product.name || "", category: product.category || "" });
  };

  const handleCancelEdit = () => {
    setEditingProduct(null);
    setEditForm({ name: "", category: "" });
  };

  const handleSaveEdit = async () => {
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
      await updateProduct(editingProduct.id, editingProduct.category, {
        name: editForm.name.trim(),
        category: editForm.category.trim(),
      });
      setEditingProduct(null);
      fetchProducts();
      alert("Product updated successfully");
    } catch (err) {
      console.error("Update failed", err);
      alert("Failed to update product");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (product) => {
    if (!window.confirm(`Are you sure you want to delete "${product.name}"?`)) return;
    try {
      await deleteProduct(product.id, product.category);
      fetchProducts();
      alert("Product deleted successfully");
    } catch (err) {
      console.error("Delete failed", err);
      alert("Failed to delete product");
    }
  };

  return (
    <div style={{ backgroundColor: "var(--bg-main)", minHeight: "100vh" }}>
      <Navbar />

      <main style={{ maxWidth: "1200px", margin: "40px auto", padding: "0 16px" }}>
        <h1 style={{ fontSize: "24px", fontWeight: "700", marginBottom: "24px", color: "var(--text-main)" }}>
          Browse Products
        </h1>

        <div style={{ marginBottom: "30px" }}>
          <div
            style={{
              display: "flex",
              gap: "8px",
              flexWrap: "wrap",
              marginBottom: "32px",
            }}>
            <button
              onClick={() => {
                setSelectedCategory("");
                setOffset(0);
              }}
              style={{
                padding: "6px 16px",
                borderRadius: "20px",
                border: "1px solid var(--border-light)",
                backgroundColor:
                  selectedCategory === "" ? "var(--brand-primary)" : "white",
                color: selectedCategory === "" ? "white" : "var(--text-main)",
                cursor: "pointer",
                fontWeight: "600",
                fontSize: "13px",
              }}>
              All Products
            </button>
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => {
                  setSelectedCategory(cat);
                  setOffset(0);
                }}
                style={{
                  padding: "6px 16px",
                  borderRadius: "20px",
                  border: "1px solid var(--border-light)",
                  backgroundColor:
                    selectedCategory === cat ? "var(--brand-primary)" : "white",
                  color:
                    selectedCategory === cat ? "white" : "var(--text-main)",
                  cursor: "pointer",
                  fontWeight: "600",
                  fontSize: "13px",
                }}>
                {cat}
              </button>
            ))}
          </div>
        </div>

        {loading ?
          <p style={{ textAlign: "center", padding: "60px", color: "var(--text-muted)" }}>Loading catalog...</p>
        : <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))",
              gap: "24px",
            }}>
            {products.map((item) => (
              <div key={item.id} style={{ position: "relative" }}>
                <ProductCard product={item} />
                <div
                  style={{
                    position: "absolute",
                    top: "8px",
                    right: "8px",
                    display: "flex",
                    gap: "6px",
                    zIndex: 10,
                  }}
                  className="product-actions"
                >
                  <button
                    onClick={() => handleEdit(item)}
                    style={{
                      width: "32px",
                      height: "32px",
                      borderRadius: "6px",
                      border: "none",
                      backgroundColor: "rgba(255,255,255,0.95)",
                      color: "var(--brand-primary)",
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      boxShadow: "0 2px 8px rgba(0,0,0,0.15)",
                      fontSize: "14px",
                    }}
                    title="Edit"
                  >
                    ✎
                  </button>
                  <button
                    onClick={() => handleDelete(item)}
                    style={{
                      width: "32px",
                      height: "32px",
                      borderRadius: "6px",
                      border: "none",
                      backgroundColor: "rgba(255,255,255,0.95)",
                      color: "#ef4444",
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      boxShadow: "0 2px 8px rgba(0,0,0,0.15)",
                      fontSize: "14px",
                    }}
                    title="Delete"
                  >
                    ✕
                  </button>
                </div>
              </div>
            ))}
          </div>
        }

        {products.length === 0 && !loading && (
          <div
            style={{
              textAlign: "center",
              padding: "60px",
              background: "white",
              borderRadius: "16px",
            }}>
            <p style={{ color: "var(--text-muted)" }}>
              No products found in this category.
            </p>
          </div>
        )}

        <div
          style={{
            marginTop: "60px",
            display: "flex",
            justifyContent: "center",
            gap: "16px",
            paddingBottom: "80px",
          }}>
          <button
            disabled={offset === 0}
            onClick={() => setOffset((o) => Math.max(0, o - limit))}
            className="btn-secondary"
            style={{ opacity: offset === 0 ? 0.5 : 1 }}>
            Previous
          </button>
          <button
            disabled={products.length < limit}
            onClick={() => setOffset((o) => o + limit)}
            className="btn-secondary"
            style={{ opacity: products.length < limit ? 0.5 : 1 }}>
            Next
          </button>
        </div>
      </main>

      {editingProduct && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(0,0,0,0.5)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: "20px",
          }}
          onClick={handleCancelEdit}
        >
          <div
            style={{
              backgroundColor: "white",
              borderRadius: "16px",
              padding: "32px",
              maxWidth: "480px",
              width: "100%",
              boxShadow: "0 20px 60px rgba(0,0,0,0.3)",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h2 style={{ margin: "0 0 24px 0", fontSize: "20px", color: "var(--text-main)" }}>
              Edit Product
            </h2>

            <div style={{ marginBottom: "16px" }}>
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
                  boxSizing: "border-box",
                }}
                placeholder="Enter product name"
              />
            </div>

            <div style={{ marginBottom: "24px" }}>
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
                  boxSizing: "border-box",
                }}
                placeholder="Enter category"
              />
            </div>

            <div style={{ display: "flex", gap: "12px" }}>
              <button
                onClick={handleSaveEdit}
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
                  fontSize: "14px",
                }}
              >
                {saving ? "Saving..." : "Save Changes"}
              </button>
              <button
                onClick={handleCancelEdit}
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
                  fontSize: "14px",
                }}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      <style>{`
        .product-actions {
          opacity: 0;
          transition: opacity 0.2s;
        }
        .product-actions:hover {
          opacity: 1 !important;
        }
        @media (max-width: 768px) {
          .product-actions {
            opacity: 1 !important;
          }
        }
      `}</style>
    </div>
  );
}
