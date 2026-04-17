import os
import faiss
import numpy as np
import logging
from typing import List, Tuple
from core.config import settings

class IndexService:
    def __init__(self):
        self.dimension = settings.VECTOR_DIMENSION
        self.index_path = settings.FAISS_INDEX_PATH
        self.index = None
        self.product_ids = []  # Maps index position to product ID
        self._ensure_data_dir()
        self._load_index()

    def _ensure_data_dir(self):
        """Ensures the data directory exists."""
        data_dir = os.path.dirname(self.index_path)
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
            logging.info(f"Created data directory: {data_dir}")

    def _load_index(self):
        """Loads the FAISS index from disk or creates a new one."""
        if os.path.exists(self.index_path):
            try:
                self.index = faiss.read_index(self.index_path)
                # We also need to load the product_ids mapping.
                # For simplicity in this demo, we'll store them in a separate .txt file.
                ids_path = self.index_path + ".ids"
                if os.path.exists(ids_path):
                    with open(ids_path, "r") as f:
                        self.product_ids = [line.strip() for line in f.readlines()]
                logging.info(f"Loaded FAISS index with {len(self.product_ids)} items.")
            except Exception as e:
                logging.error(f"Failed to load FAISS index: {str(e)}")
                self._create_new_index()
        else:
            self._create_new_index()

    def _create_new_index(self):
        """Initializes a new FAISS index."""
        # Using IndexFlatIP for Inner Product (Cosine Similarity on normalized vectors)
        self.index = faiss.IndexFlatIP(self.dimension)
        self.product_ids = []
        logging.info("Created new empty FAISS index.")

    def save_index(self):
        """Saves the FAISS index and product ID mapping to disk."""
        try:
            faiss.write_index(self.index, self.index_path)
            ids_path = self.index_path + ".ids"
            with open(ids_path, "w") as f:
                for pid in self.product_ids:
                    f.write(f"{pid}\n")
            logging.info("Saved FAISS index to disk.")
        except Exception as e:
            logging.error(f"Failed to save FAISS index: {str(e)}")

    def add_product(self, product_id: str, vector: List[float]):
        """Adds a single product vector to the index."""
        if not vector or len(vector) != self.dimension:
            logging.error(f"Invalid vector dimension for product {product_id}")
            return

        vector_np = np.array([vector]).astype('float32')
        self.index.add(vector_np)
        self.product_ids.append(product_id)
        # self.save_index() # Save manually or periodically for performance

    def search(self, query_vector: List[float], top_k: int = 10) -> List[Tuple[str, float]]:
        """Searches for the top K similar products."""
        if self.index.ntotal == 0:
            return []

        query_np = np.array([query_vector]).astype('float32')
        distances, indices = self.index.search(query_np, top_k)
        
        results = []
        for i, idx in enumerate(indices[0]):
            if idx != -1 and idx < len(self.product_ids):
                results.append((self.product_ids[idx], float(distances[0][i])))
        
        return results

    def remove_product(self, product_id: str):
        """
        Removes a product from the index. 
        Note: FAISS IndexFlat doesn't support easy deletion. 
        In a production app, you'd likely rebuild the index or use a different index type.
        For now, we'll mark it as a 'to-do' or handle it by re-indexing.
        """
        logging.warning("Product removal from FAISS index is not implemented in this version.")

# Singleton instance
index_service = IndexService()
