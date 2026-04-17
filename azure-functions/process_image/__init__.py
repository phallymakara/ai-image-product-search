import logging
import azure.functions as func
import requests
import os
import json
import time
from azure.cosmos import CosmosClient, PartitionKey
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
VISION_ENDPOINT = os.getenv("VISION_ENDPOINT")
VISION_KEY = os.getenv("VISION_KEY")
COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT")
COSMOS_KEY = os.getenv("COSMOS_KEY")
COSMOS_DATABASE_NAME = os.getenv("COSMOS_DATABASE_NAME", os.getenv("COSMOS_DATABASE", "ProductDB"))
COSMOS_CONTAINER_NAME = os.getenv("COSMOS_CONTAINER_NAME", os.getenv("COSMOS_CONTAINER", "Products"))
STORAGE_ACCOUNT_URL = os.getenv("STORAGE_ACCOUNT_URL", "").rstrip("/")

# --- GLOBAL INITIALIZATION ---
_cosmos_container = None

def get_cosmos_container():
    global _cosmos_container
    if _cosmos_container is not None:
        return _cosmos_container
    
    if not COSMOS_ENDPOINT or not COSMOS_KEY:
        logging.error("Missing COSMOS_ENDPOINT or COSMOS_KEY")
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
        logging.error(f"Failed to initialize Cosmos DB: {str(e)}")
        return None

# Call Azure AI Vision Analyze
def analyze_image(image_bytes):
    if not VISION_ENDPOINT or not VISION_KEY:
        raise ValueError("Missing Vision configuration")

    url = f"{VISION_ENDPOINT}/vision/v3.2/analyze?visualFeatures=Tags,Objects,Categories,Description,Brands"

    headers = {
        "Ocp-Apim-Subscription-Key": VISION_KEY,
        "Content-Type": "application/octet-stream"
    }

    response = requests.post(url, headers=headers, data=image_bytes)
    if response.status_code != 200:
        logging.error(f"Vision API Error: {response.status_code}")
        return {}

    return response.json()

# Call Azure AI Vision OCR
def ocr_image(image_bytes):
    if not VISION_ENDPOINT or not VISION_KEY:
        return ""

    # Step 1: Submit to Read API
    url = f"{VISION_ENDPOINT}/vision/v3.2/read/analyze"
    headers = {
        "Ocp-Apim-Subscription-Key": VISION_KEY,
        "Content-Type": "application/octet-stream"
    }

    try:
        response = requests.post(url, headers=headers, data=image_bytes)
        response.raise_for_status()
        
        operation_url = response.headers.get("Operation-Location")
        if not operation_url:
            return ""

        # Step 2: Poll
        for _ in range(10):
            result_res = requests.get(operation_url, headers={"Ocp-Apim-Subscription-Key": VISION_KEY})
            result_data = result_res.json()

            if result_data.get("status") == "succeeded":
                text_parts = []
                for res in result_data.get("analyzeResult", {}).get("readResults", []):
                    for line in res.get("lines", []):
                        text_parts.append(line.get("text", ""))
                return " ".join(text_parts)
            
            if result_data.get("status") == "failed":
                return ""
            time.sleep(1)

    except Exception as e:
        logging.error(f"OCR Error: {str(e)}")
    return ""

# Extract metadata from blob path
def extract_metadata_from_path(blob_name):
    parts = blob_name.split("/")
    if "raw" not in parts:
        return None, None
    raw_index = parts.index("raw")
    if len(parts) < raw_index + 3:
        return None, None
    user_id = parts[raw_index + 1]
    image_id = os.path.splitext(parts[raw_index + 2])[0]
    return user_id, image_id

# MAIN FUNCTION
def main(myblob: func.InputStream):
    logging.info(f"Processing blob: {myblob.name}")

    try:
        image_bytes = myblob.read()
        user_id, product_id = extract_metadata_from_path(myblob.name)
        if not product_id:
            return

        container = get_cosmos_container()
        if not container:
            logging.error("No Cosmos container available")
            return

        existing = None
        # Try to find existing product by querying (partition key might be different)
        try:
            items = list(container.query_items(
                query="SELECT * FROM c WHERE c.id = @id",
                parameters=[{"name": "@id", "value": product_id}],
                enable_cross_partition_query=True
            ))
            if items:
                existing = items[0]
                logging.info(f"Product {product_id} already exists with name: '{existing.get('name')}', category: '{existing.get('category')}'")
            else:
                logging.info(f"Product {product_id} does not exist yet, will create new")
        except Exception as e:
            logging.info(f"Could not query for existing product: {str(e)}")

        # Always do AI analysis (needed for tags, brands, ocr)
        analysis_result = analyze_image(image_bytes)
        ocr_text = ocr_image(image_bytes)
        new_tags = [
            {"name": t["name"], "confidence": round(t["confidence"], 3)}
            for t in analysis_result.get("tags", []) if t["confidence"] > 0.1
        ]
        new_brands = [b["name"] for b in analysis_result.get("brands", [])]

        if existing:
            # Product exists (uploaded via API) - PRESERVE user-provided name and category
            existing["tags"] = new_tags
            existing["brands"] = new_brands
            existing["ocr_text"] = ocr_text
            existing["source"] = "azure-function-processor"
            existing["enhanced_search"] = True
            existing["processedAt"] = True
            container.upsert_item(existing)
            logging.info(f"Updated existing product {product_id} (preserved user-provided name/category)")
        else:
            # New product (direct blob upload) - use AI for everything
            description = analysis_result.get("description", {}).get("captions", [])
            name = "Unknown Product"
            if description:
                name = description[0].get("text", "").capitalize()
            elif new_brands:
                name = f"{new_brands[0]} Product"
            elif analysis_result.get("objects"):
                name = analysis_result["objects"][0].get("object", "").capitalize()
            elif new_tags:
                name = new_tags[0]["name"].capitalize()
                
            category = "uncategorized"
            categories = analysis_result.get("categories", [])
            if categories:
                raw_cat = categories[0].get("name", "")
                category = raw_cat.split("_")[0] if "_" in raw_cat else raw_cat
            elif new_tags:
                category = new_tags[0]["name"]

            # 4. Prepare and Save Data
            image_url = f"{STORAGE_ACCOUNT_URL}/{myblob.name}" if STORAGE_ACCOUNT_URL else myblob.name

            product_data = {
                "id": product_id,
                "productId": product_id,
                "name": name,
                "category": category,
                "tags": new_tags,
                "brands": new_brands,
                "ocr_text": ocr_text,
                "imageUrl": image_url,
                "userId": user_id,
                "source": "azure-function-processor",
                "enhanced_search": True,
                "processedAt": True
            }

            container.upsert_item(product_data)
            logging.info(f"Created new product {product_id}")

    except Exception as e:
        logging.error(f"Error in background processor: {str(e)}")
