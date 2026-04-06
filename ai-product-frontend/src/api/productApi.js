import api from "./axios";

export const getProducts = (category, limit = 50, offset = 0) => {
  return api.get("/products", {
    params: { category, limit, offset },
  });
};

export const getProductById = (productId, category = "") => {
  return api.get(`/products/${productId}`, {
    params: { category },
  });
};

export const createProduct = (productData) => {
  return api.post("/products", productData);
};

export const updateProduct = (productId, category, updateData) => {
  return api.patch(`/products/${productId}`, updateData, {
    params: { category },
  });
};

export const deleteProduct = (productId, category) => {
  return api.delete(`/products/${productId}`, {
    params: { category },
  });
};

export const getTrendingProducts = () => {
  return api.get("/products/trending");
};

export const getCategories = () => {
  return api.get("/categories");
};
