import api from "./axios";

// =====================
// UPLOAD IMAGE
// =====================
export const uploadImage = async (formData) => {
  return await api.post("/upload", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
};

// =====================
// SEARCH IMAGE
// =====================
export const searchImage = async (formData, userId) => {
  return await api.post(`/search?user_id=${userId}`, formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
};

// =====================
// SEARCH BY TEXT
// =====================
export const searchText = async (query, userId, category = "") => {
  return await api.get("/search/text", {
    params: {
      user_id: userId,
      query: query,
      category: category,
    },
  });
};

// =====================
// GET RECENT SEARCHES [NEW]
// =====================
export const getRecentSearches = async (userId) => {
  return await api.get("/search/recent", {
    params: { user_id: userId },
  });
};

// =====================
// GET SEARCH HISTORY
// =====================
export const getSearchHistory = async (userId) => {
  return await api.get("/search/history", {
    params: { user_id: userId },
  });
};

// =====================
// DELETE SEARCH HISTORY
// =====================
export const deleteHistory = async (userId, searchId) => {
  return await api.delete(`/search/history/${searchId}`, {
    params: { user_id: userId },
  });
};
