import os
from dotenv import load_dotenv
 
load_dotenv()
 
# Azure Storage
STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION")
STORAGE_CONTAINER_NAME = os.getenv("CONTAINER_NAME")
 
# Azure AI Vision
VISION_ENDPOINT = os.getenv("VISION_ENDPOINT", "").rstrip("/")
VISION_KEY = os.getenv("VISION_KEY")
 
# Azure Cosmos DB
COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT")
COSMOS_KEY = os.getenv("COSMOS_KEY")
COSMOS_DATABASE_NAME = os.getenv("COSMOS_DATABASE_NAME", os.getenv("COSMOS_DATABASE", "ProductDB"))
COSMOS_CONTAINER_NAME = os.getenv("COSMOS_CONTAINER_NAME", os.getenv("COSMOS_CONTAINER", "Products"))