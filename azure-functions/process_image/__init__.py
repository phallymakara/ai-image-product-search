import logging
import azure.functions as func
import requests
import os
import json
from azure.cosmos import CosmosClient, PartitionKey
from dotenv import load_dotenv

# Load environment variables (Local only, Azure uses App Settings)
load_dotenv()

# Configuration
VISION_ENDPOINT = os.getenv("VISION_ENDPOINT")
VISION_KEY = os.getenv("VISION_KEY")
COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT")
COSMOS_KEY = os.getenv("COSMOS_KEY")
COSMOS_DATABASE_NAME = os.getenv("COSMOS_DATABASE_NAME", "ProductDB")
COSMOS_CONTAINER_NAME = os.getenv("COSMOS_CONTAINER_NAME", "Products")
# URL of the storage account (e.g., https://mystorage.blob.core.windows.net)
STORAGE_ACCOUNT_URL = os.getenv("STORAGE_ACCOUNT_URL", "").rstrip("/")

# --- GLOBAL INITIALIZATION (Production Best Practice) ---
# Initializing outside the main function allows connection reuse (Warm Starts)
_cosmos_container = None

def get_cosmos_container():
    global _cosmos_container
    if _cosmos_container is not None:
        return _cosmos_container
    
    if not COSMOS_ENDPOINT or not COSMOS_KEY:
        logging.error("CRITICAL: Missing COSMOS_ENDPOINT or COSMOS_KEY in environment variables.")
        return None
    
    try:
        cosmos_client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)
        database = cosmos_client.create_database_if_not_exists(id=COSMOS_DATABASE_NAME)
        _cosmos_container = database.create_container_if_not_exists(
            id=COSMOS_CONTAINER_NAME,
            partition_key=PartitionKey(path="/category")
        )
        return _cosmos_container
    except Exception as e:
        logging.error(f"CRITICAL: Failed to initialize Cosmos DB: {str(e)}")
        return None

# Call Azure AI Vision
def analyze_image(image_bytes):
    if not VISION_ENDPOINT or not VISION_KEY:
        raise ValueError("Missing VISION_ENDPOINT or VISION_KEY")

    # PRODUCTION: Use a broader set of features for high-quality metadata
    url = f"{VISION_ENDPOINT}/vision/v3.2/analyze?visualFeatures=Tags,Objects,Categories,Description"

    headers = {
        "Ocp-Apim-Subscription-Key": VISION_KEY,
        "Content-Type": "application/octet-stream"
    }

    response = requests.post(url, headers=headers, data=image_bytes)
    if response.status_code != 200:
        logging.error(f"Vision API Error: {response.status_code} - {response.text}")
        return {}

    return response.json()

# Extract metadata from blob path
def extract_metadata_from_path(blob_name):
    """
    Standard path: images-analysis/raw/{userId}/{imageId}.jpg
    """
    parts = blob_name.split("/")
    if "raw" not in parts:
        return None, None
    
    raw_index = parts.index("raw")
    if len(parts) < raw_index + 3:
        return None, None

    user_id = parts[raw_index + 1]
    image_filename = parts[raw_index + 2]
    image_id = os.path.splitext(image_filename)[0]

    return user_id, image_id

# MAIN FUNCTION (Triggered by Blob)
def main(myblob: func.InputStream):
    logging.info(f"Processing blob: {myblob.name}")

    try:
        # 1. Read image content
        image_bytes = myblob.read()
        if not image_bytes:
            logging.warning(f"Blob {myblob.name} is empty. Skipping.")
            return

        # 2. Extract metadata from path
        user_id, product_id = extract_metadata_from_path(myblob.name)
        if not product_id:
            logging.error(f"Path format invalid. Expected '.../raw/{{userId}}/{{imageId}}.jpg'. Got: {myblob.name}")
            return

        # 3. Call AI Vision
        result = analyze_image(image_bytes)
        
        # 4. Intelligent Data Extraction
        tags = result.get("tags", [])
        filtered_tags = [
            {"name": t["name"], "confidence": round(t["confidence"], 3)}
            for t in tags if t["confidence"] > 0.5
        ]
        
        # Determine Name
        description = result.get("description", {}).get("captions", [])
        name = "Unknown Product"
        if description:
            name = description[0].get("text", "").capitalize()
        elif result.get("objects"):
            name = result["objects"][0].get("object", "").capitalize()
        elif filtered_tags:
            name = filtered_tags[0]["name"].capitalize()
            
        # Determine Category
        category = "uncategorized"
        categories = result.get("categories", [])
        if categories:
            raw_cat = categories[0].get("name", "")
            category = raw_cat.split("_")[0] if "_" in raw_cat else raw_cat
        elif filtered_tags:
            category = filtered_tags[0]["name"]

        # 5. Prepare Data
        # Ensure image URL is valid; fallback to path if STORAGE_ACCOUNT_URL is missing
        image_url = f"{STORAGE_ACCOUNT_URL}/{myblob.name}" if STORAGE_ACCOUNT_URL else myblob.name

        product_data = {
            "id": product_id,
            "productId": product_id,
            "name": name,
            "category": category,
            "tags": filtered_tags,
            "imageUrl": image_url,
            "userId": user_id,
            "source": "azure-function-processor",
            "processedAt": True
        }

        # 6. Save to Cosmos DB
        container = get_cosmos_container()
        if container:
            container.upsert_item(product_data)
            logging.info(f"Successfully processed and saved product: {product_id}")
        else:
            logging.error("Failed to save to Cosmos DB: Client not initialized.")

    except Exception as e:
        logging.error(f"Critical error processing image {myblob.name}: {str(e)}")
