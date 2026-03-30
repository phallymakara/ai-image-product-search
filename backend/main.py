from fastapi import FastAPI, UploadFile, File, Form
from azure.storage.blob import BlobServiceClient
from azure.cosmos import CosmosClient, PartitionKey
from dotenv import load_dotenv
from typing import Optional, List, Dict, Any
import uuid
import os
import requests
import logging

# Load environment variables
load_dotenv()

app = FastAPI()

# Configuration - Azure Storage
STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION")
STORAGE_CONTAINER_NAME = os.getenv("CONTAINER_NAME")

# Configuration - Azure AI Vision
VISION_ENDPOINT = os.getenv("VISION_ENDPOINT")
VISION_KEY = os.getenv("VISION_KEY")

# Configuration - Azure Cosmos DB
COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT")
COSMOS_KEY = os.getenv("COSMOS_KEY")
COSMOS_DATABASE_NAME = os.getenv("COSMOS_DATABASE_NAME", "ProductDB")
COSMOS_CONTAINER_NAME = os.getenv("COSMOS_CONTAINER_NAME", "Products")

# Clients initialization
blob_service_client = BlobServiceClient.from_connection_string(STORAGE_CONNECTION_STRING)

# Cosmos DB initialization
cosmos_client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)
database = cosmos_client.create_database_if_not_exists(id=COSMOS_DATABASE_NAME)
container = database.create_container_if_not_exists(
    id=COSMOS_CONTAINER_NAME,
    partition_key=PartitionKey(path="/category")
)


def analyze_image(image_bytes: bytes) -> Dict[str, Any]:
    """
    Analyzes an image using Azure AI Vision API.

    Args:
        image_bytes (bytes): The raw image data to be analyzed.

    Returns:
        dict: The JSON response from the Azure AI Vision API.
    """
    if not VISION_ENDPOINT or not VISION_KEY:
        logging.error("Missing VISION_ENDPOINT or VISION_KEY environment variables")
        return {}

    url = f"{VISION_ENDPOINT}/vision/v3.2/analyze?visualFeatures=Tags,Objects"

    headers = {
        "Ocp-Apim-Subscription-Key": VISION_KEY,
        "Content-Type": "application/octet-stream"
    }

    try:
        response = requests.post(url, headers=headers, data=image_bytes)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logging.error(f"Error calling Vision API: {str(e)}")
        return {}


def extract_tags(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extracts high-confidence tags from the Azure AI Vision analysis result.

    Args:
        result (dict): The JSON response from the AI Vision API.

    Returns:
        list: A list of tags with their names and confidence scores.
    """
    tags = result.get("tags", [])

    filtered = [
        {
            "name": tag["name"],
            "confidence": round(tag["confidence"], 3)
        }
        for tag in tags
        if tag["confidence"] > 0.8
    ]

    return filtered


def upload_to_blob(file_bytes: bytes, image_id: str, user_id: str) -> str:
    """
    Uploads an image as raw bytes to Azure Blob Storage with metadata.

    Args:
        file_bytes (bytes): The raw data of the image file.
        image_id (str): A unique identifier for the image.
        user_id (str): The identifier for the user who uploaded the image.

    Returns:
        str: The URL of the uploaded blob.
    """
    blob_path = f"raw/{user_id}/{image_id}.jpg"

    blob_client = blob_service_client.get_blob_client(
        container=STORAGE_CONTAINER_NAME,
        blob=blob_path
    )

    blob_client.upload_blob(file_bytes, overwrite=True, metadata={
        "userId": user_id,
        "imageId": image_id
    })

    return blob_client.url


@app.post("/upload")
async def upload_image(
    user_id: str,
    name: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    file: UploadFile = File(...)
):
    """
    API endpoint for uploading an image and storing product metadata in Cosmos DB.

    Args:
        user_id (str): The ID of the user uploading the file.
        name (str, optional): The name of the product.
        category (str, optional): The category of the product.
        file (UploadFile): The uploaded file provided in the request body.

    Returns:
        dict: A structured response containing the product ID, metadata, tags, and image URL.
    """
    # Generate unique ID
    product_id = f"P{str(uuid.uuid4())[:7]}"

    # Read image content
    file_bytes = await file.read()

    # 1. Upload to storage
    image_url = upload_to_blob(file_bytes, product_id, user_id)

    # 2. Analyze image using AI Vision
    analysis_result = analyze_image(file_bytes)
    tags = extract_tags(analysis_result)

    # 3. Identify main product
    main_product = None
    if tags:
        main_product = tags[0]

    # 4. Save to Cosmos DB
    product_data = {
        "id": product_id,  # Cosmos DB requires an 'id' field
        "productId": product_id,
        "name": name or (main_product["name"] if main_product else "Unknown"),
        "category": category or "uncategorized",
        "tags": tags,
        "main_product": main_product,
        "imageUrl": image_url,
        "userId": user_id
    }
    
    container.upsert_item(product_data)

    # Construct structured response
    return {
        "message": "Product uploaded successfully",
        "data": product_data
    }


@app.post("/search")
async def search_similar_product(file: UploadFile = File(...)):
    """
    API endpoint for searching for similar products in Cosmos DB using an image.

    Args:
        file (UploadFile): The image file to search for similar products.

    Returns:
        dict: A list of similar products found in the database.
    """
    # Read image content
    file_bytes = await file.read()

    # 1. Analyze search image
    analysis_result = analyze_image(file_bytes)
    search_tags = extract_tags(analysis_result)

    if not search_tags:
        return {"message": "No relevant product tags found in the image", "results": []}

    # Extract the main tag name for search
    search_keyword = search_tags[0]["name"]

    # 2. Search Cosmos DB using SQL query
    # Find products where search_keyword is in tags or category
    query = (
        "SELECT * FROM c WHERE "
        "EXISTS(SELECT VALUE t FROM t IN c.tags WHERE t.name = @keyword) OR "
        "c.category = @keyword"
    )
    
    parameters = [
        {"name": "@keyword", "value": search_keyword}
    ]
    
    results = list(container.query_items(
        query=query,
        parameters=parameters,
        enable_cross_partition_query=True
    ))

    # Return top matches (up to 3)
    return {
        "message": f"Found similar products for '{search_keyword}'",
        "results": results[:3]
    }
