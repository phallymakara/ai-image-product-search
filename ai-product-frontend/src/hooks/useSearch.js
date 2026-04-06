import { useState } from "react";
import { searchImage, searchText } from "../api/searchApi";

export default function useSearch() {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [status, setStatus] = useState("");

  const steps = [
    "Uploading image to secure storage...",
    "Running Azure AI Vision analysis...",
    "Extracting product brands and features...",
    "Performing OCR text recognition...",
    "Scanning catalog for best matches...",
    "Ranking results by relevance score..."
  ];

  const simulateProgress = (setMsg) => {
    let i = 0;
    const interval = setInterval(() => {
      if (i < steps.length) {
        setMsg(steps[i]);
        i++;
      } else {
        clearInterval(interval);
      }
    }, 1500);
    return interval;
  };

  const performImageSearch = async (file, userId) => {
    if (!file) {
      setError("Please select a file first");
      return;
    }

    setLoading(true);
    setError(null);
    setStatus("Initializing search...");
    
    const progressInterval = simulateProgress(setStatus);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await searchImage(formData, userId);
      clearInterval(progressInterval);
      setStatus("Matches found!");
      const data = res.data.results || [];
      setResults(data);
      return data;
    } catch (err) {
      clearInterval(progressInterval);
      const msg = err.response?.data?.detail || "Image search failed";
      setError(msg);
      setStatus("");
    } finally {
      setLoading(false);
    }
  };

  const performTextSearch = async (query, userId, category = "") => {
    if (!query || query.trim() === "") {
      setError("Please enter a search term");
      return;
    }

    setLoading(true);
    setError(null);
    setStatus("Searching catalog...");

    try {
      const res = await searchText(query, userId, category);
      const data = res.data.results || [];
      setResults(data);
      setStatus("");
      return data;
    } catch (err) {
      const msg = err.response?.data?.detail || "Text search failed";
      setError(msg);
      setStatus("");
    } finally {
      setLoading(false);
    }
  };

  return { results, loading, error, status, performImageSearch, performTextSearch };
}
