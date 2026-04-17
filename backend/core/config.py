import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

# Get the directory of this file (backend/core/)
# and then go up one level to get the backend/ root.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_FILE = os.path.join(BASE_DIR, ".env")

class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = "AI Product Image Search"
    DEBUG: bool = False
    
    # Azure Storage
    AZURE_STORAGE_CONNECTION: Optional[str] = None
    CONTAINER_NAME: str = "products"
    
    # Azure AI Vision
    VISION_ENDPOINT: Optional[str] = None
    VISION_KEY: Optional[str] = None
    
    # Azure Cosmos DB
    COSMOS_ENDPOINT: Optional[str] = None
    COSMOS_KEY: Optional[str] = None
    COSMOS_DATABASE: str = "ProductDB"
    COSMOS_CONTAINER: str = "Products"
    COSMOS_HISTORY_CONTAINER: str = "SearchHistory"
    
    # Storage URL (for direct link generation)
    STORAGE_ACCOUNT_URL: Optional[str] = None

    # Vector Search Settings
    CLIP_MODEL_NAME: str = "ViT-B-32"
    CLIP_PRETRAINED_DATASET: str = "laion2b_s34b_b79k"
    FAISS_INDEX_PATH: str = os.path.join(BASE_DIR, "data", "products.index")
    VECTOR_DIMENSION: int = 512

    model_config = SettingsConfigDict(
        env_file=ENV_FILE, 
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Singleton instance
settings = Settings()
