import logging

class IndexService:
    """
    OBSOLETE: Indexing is now handled natively by Azure Cosmos DB Vector Search.
    This class is kept as a stub to avoid breaking existing imports until fully refactored.
    """
    def __init__(self):
        logging.info("IndexService (FAISS) is now disabled. Using Cosmos DB Vector Search.")

    def add_product(self, product_id: str, vector: list):
        pass

    def save_index(self):
        pass

    def search(self, query_vector: list, top_k: int = 10):
        return []

    def clear_index(self):
        pass

# Singleton instance
index_service = IndexService()
