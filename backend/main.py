from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from azure.storage.blob import BlobServiceClient
from azure.cosmos import CosmosClient, PartitionKey
from dotenv import load_dotenv
from typing import Optional, List, Dict, Any
import uuid
import os
import requests
import logging
import hashlib
from datetime import datetime
from collections import defaultdict
from thefuzz import fuzz

# Load environment variables
load_dotenv()

app = FastAPI()

# Configuration - Azure Storage
STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION")
STORAGE_CONTAINER_NAME = os.getenv("CONTAINER_NAME")

# Configuration - Azure AI Vision
VISION_ENDPOINT = os.getenv("VISION_ENDPOINT", "").rstrip("/")
VISION_KEY = os.getenv("VISION_KEY")

# Configuration - Azure Cosmos DB
COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT")
COSMOS_KEY = os.getenv("COSMOS_KEY")
COSMOS_DATABASE_NAME = os.getenv("COSMOS_DATABASE_NAME", os.getenv("COSMOS_DATABASE", "ProductDB"))
COSMOS_CONTAINER_NAME = os.getenv("COSMOS_CONTAINER_NAME", os.getenv("COSMOS_CONTAINER", "Products"))

# Clients initialization
blob_service_client = None
container = None
search_history_container = None

try:
    if STORAGE_CONNECTION_STRING:
        blob_service_client = BlobServiceClient.from_connection_string(STORAGE_CONNECTION_STRING)
    
    if COSMOS_ENDPOINT and COSMOS_KEY:
        cosmos_client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)
        database = cosmos_client.create_database_if_not_exists(id=COSMOS_DATABASE_NAME)
        container = database.create_container_if_not_exists(
            id=COSMOS_CONTAINER_NAME,
            partition_key=PartitionKey(path="/category")
        )
        search_history_container = database.create_container_if_not_exists(
            id="SearchHistory",
            partition_key=PartitionKey(path="/userId")
        )
except Exception as e:
    logging.error(f"Failed to initialize Azure clients: {str(e)}")


def analyze_image(image_bytes: bytes) -> Dict[str, Any]:
    """
    Analyzes an image using Azure AI Vision API with multiple features.
    """
    if not VISION_ENDPOINT or not VISION_KEY:
        logging.error("Missing VISION_ENDPOINT or VISION_KEY")
        return {}

    url = f"{VISION_ENDPOINT}/vision/v3.2/analyze?visualFeatures=Tags,Objects,Categories,Description,Brands"

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

def ocr_image(image_bytes: bytes) -> str:
    """
    Extracts text from an image using Azure Vision OCR API.
    """
    if not VISION_ENDPOINT or not VISION_KEY:
        return ""

    url = f"{VISION_ENDPOINT}/vision/v3.2/ocr?language=unk&detectOrientation=true"

    headers = {
        "Ocp-Apim-Subscription-Key": VISION_KEY,
        "Content-Type": "application/octet-stream"
    }

    try:
        response = requests.post(url, headers=headers, data=image_bytes)
        response.raise_for_status()
        data = response.json()
        
        text_parts = []
        for region in data.get("regions", []):
            for line in region.get("lines", []):
                for word in line.get("words", []):
                    text_parts.append(word.get("text", ""))
        
        return " ".join(text_parts)
    except Exception as e:
        logging.error(f"Error calling OCR API: {str(e)}")
        return ""


def extract_tags(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extracts tags from the Azure AI Vision analysis result.
    """
    tags = result.get("tags", [])
    return [
        {"name": tag["name"], "confidence": round(tag["confidence"], 3)}
        for tag in tags if tag["confidence"] > 0.5
    ]

def extract_brands(result: Dict[str, Any]) -> List[str]:
    """
    Extracts brand names from the analysis result.
    """
    brands = result.get("brands", [])
    return [brand["name"] for brand in brands]


def upload_to_blob(file_bytes: bytes, image_id: str, user_id: str) -> str:
    """
    Uploads an image to Azure Blob Storage.
    """
    if not blob_service_client:
        raise Exception("Blob storage client not initialized")
    
    blob_path = f"raw/{user_id}/{image_id}.jpg"
    blob_client = blob_service_client.get_blob_client(container=STORAGE_CONTAINER_NAME, blob=blob_path)
    blob_client.upload_blob(file_bytes, overwrite=True, metadata={"userId": user_id, "imageId": image_id})
    return blob_client.url


@app.post("/upload")
async def upload_image(
    user_id: str,
    name: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    file: UploadFile = File(...)
):
    """
    Uploads an image and extracts enhanced metadata. 
    Prevents duplicates using SHA-256 hashing.
    """
    if not container:
        raise HTTPException(status_code=500, detail="Database connection not initialized")

    file_bytes = await file.read()
    
    # --- DUPLICATE DETECTION ---
    image_hash = hashlib.sha256(file_bytes).hexdigest()
    
    # Check if this hash already exists in Cosmos DB
    query = "SELECT * FROM c WHERE c.image_hash = @hash"
    existing_items = list(container.query_items(
        query=query,
        parameters=[{"name": "@hash", "value": image_hash}],
        enable_cross_partition_query=True
    ))
    
    if existing_items:
        return {
            "message": "Image already exists in the system",
            "is_duplicate": True,
            "data": existing_items[0]
        }
    # ---------------------------

    product_id = f"P{str(uuid.uuid4())[:7]}"

    # 1. Image Analysis
    try:
        image_url = upload_to_blob(file_bytes, product_id, user_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Storage upload failed: {str(e)}")

    analysis_result = analyze_image(file_bytes)
    ocr_text = ocr_image(file_bytes)
    
    tags = extract_tags(analysis_result)
    brands = extract_brands(analysis_result)

    # 2. Intelligent Metadata Logic
    is_name_missing = not name or name.lower() == "string" or name.strip() == ""
    is_cat_missing = not category or category.lower() == "string" or category.strip() == ""

    if is_name_missing:
        description = analysis_result.get("description", {}).get("captions", [])
        if description:
            name = description[0].get("text", "").capitalize()
        elif brands:
            name = f"{brands[0]} Product"
        elif analysis_result.get("objects"):
            name = analysis_result["objects"][0].get("object", "").capitalize()
        elif tags:
            name = tags[0]["name"].capitalize()
        else:
            name = "Unknown Product"

    if is_cat_missing:
        categories = analysis_result.get("categories", [])
        if categories:
            raw_cat = categories[0].get("name", "")
            category = raw_cat.split("_")[0] if "_" in raw_cat else raw_cat
        elif tags:
            category = tags[0]["name"]
        else:
            category = "uncategorized"

    # 3. Save to Cosmos DB
    product_data = {
        "id": product_id,
        "productId": product_id,
        "image_hash": image_hash,
        "name": name,
        "category": category,
        "tags": tags,
        "brands": brands,
        "ocr_text": ocr_text,
        "imageUrl": image_url,
        "userId": user_id,
        "enhanced_search": True,
        "upload_source": "api"
    }
    
    try:
        container.upsert_item(product_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database save failed: {str(e)}")

    return {"message": "Product uploaded successfully", "is_duplicate": False, "data": product_data}


@app.post("/search")
async def search_similar_product(user_id: str, file: UploadFile = File(...), category: Optional[str] = None):
    """
    Search with Score = 0.4*tags + 0.3*ocr + 0.3*brands.
    Supports optional category filtering.
    """
    if not container:
        raise HTTPException(status_code=500, detail="Database connection not initialized")

    file_bytes = await file.read()
    search_id = f"S{str(uuid.uuid4())[:7]}"

    # 1. Upload search image for history preview
    search_image_url = None
    if blob_service_client:
        try:
            blob_path = f"searches/{user_id}/{search_id}.jpg"
            blob_client = blob_service_client.get_blob_client(container=STORAGE_CONTAINER_NAME, blob=blob_path)
            blob_client.upload_blob(file_bytes, overwrite=True)
            search_image_url = blob_client.url
        except Exception as e:
            logging.error(f"Failed to upload search image: {str(e)}")

    # 2. Analyze search image
    analysis_result = analyze_image(file_bytes)
    ocr_text = ocr_image(file_bytes).lower()
    
    search_tags_data = extract_tags(analysis_result)
    search_tags = [t["name"] for t in search_tags_data]
    search_brands = [b.lower() for b in extract_brands(analysis_result)]

    # Identify search category for logging
    detected_category = "uncategorized"
    categories = analysis_result.get("categories", [])
    if categories:
        raw_cat = categories[0].get("name", "")
        detected_category = raw_cat.split("_")[0] if "_" in raw_cat else raw_cat
    elif search_tags:
        detected_category = search_tags[0]

    # 3. Candidate Retrieval & Scoring
    top_matches = []
    total_results = 0
    
    if search_tags or search_brands:
        # Construct query with optional category filter
        query_parts = ["SELECT * FROM c WHERE (EXISTS(SELECT VALUE t FROM t IN c.tags WHERE ARRAY_CONTAINS(@tags, t.name)) OR EXISTS(SELECT VALUE b FROM b IN c.brands WHERE ARRAY_CONTAINS(@brands, b)))"]
        parameters = [
            {"name": "@tags", "value": search_tags},
            {"name": "@brands", "value": [b.capitalize() for b in search_brands]}
        ]

        if category:
            query_parts.append("AND c.category = @filter_category")
            parameters.append({"name": "@filter_category", "value": category})

        query = " ".join(query_parts)
        
        try:
            db_results = list(container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True
            ))
            
            scored_results = []
            for product in db_results:
                prod_tags = [t["name"] for t in product.get("tags", [])]
                common_tags = set(search_tags) & set(prod_tags)
                tag_score = len(common_tags) / len(set(search_tags) | set(prod_tags)) if (set(search_tags) | set(prod_tags)) else 0
                
                prod_brands = [b.lower() for b in product.get("brands", [])]
                brand_match = 1.0 if (set(search_brands) & set(prod_brands)) else 0.0
                
                prod_ocr = product.get("ocr_text", "").lower()
                prod_name = product.get("name", "").lower()
                ocr_score = max(
                    fuzz.partial_ratio(ocr_text, prod_ocr),
                    fuzz.partial_ratio(ocr_text, prod_name)
                ) / 100.0 if ocr_text else 0
                
                final_score = (0.4 * tag_score) + (0.3 * brand_match) + (0.3 * ocr_score)
                product["match_score"] = round(final_score, 3)
                scored_results.append(product)

            scored_results.sort(key=lambda x: x["match_score"], reverse=True)
            top_matches = scored_results[:5]
            total_results = len(scored_results)
        except Exception as e:
            logging.error(f"Search query failed: {str(e)}")

    # 4. Save to SearchHistory
    if search_history_container:
        top_match_preview = None
        if top_matches:
            top_match_preview = {
                "productId": top_matches[0].get("productId"),
                "name": top_matches[0].get("name"),
                "imageUrl": top_matches[0].get("imageUrl"),
                "match_score": top_matches[0].get("match_score")
            }

        search_record = {
            "id": search_id,
            "userId": user_id,
            "category": detected_category,
            "filterCategory": category, # Log if user used a filter
            "timestamp": datetime.utcnow().isoformat(),
            "searchImageUrl": search_image_url,
            "topMatch": top_match_preview,
            "resultCount": total_results
        }
        try:
            search_history_container.upsert_item(search_record)
        except Exception as e:
            logging.error(f"Failed to save search history: {str(e)}")

    return {
        "message": f"Found {total_results} matching products",
        "results": top_matches,
        "searchId": search_id,
        "filter_applied": category
    }


@app.get("/search/text")
async def search_products_by_text(user_id: str, query: str, category: Optional[str] = None, limit: int = 5):
    """
    Find similar products using text-based matching.
    Matches against name, tags, brands, and OCR text.
    Returns results in the same format as image search.
    """
    if not container:
        raise HTTPException(status_code=500, detail="Database connection not initialized")

    search_id = f"T{str(uuid.uuid4())[:7]}"
    query_lower = query.lower()

    # 1. Candidate Retrieval from Cosmos DB
    # We use a broad query to get potential candidates then rank them in memory
    query_parts = ["SELECT * FROM c WHERE (CONTAINS(LOWER(c.name), @query) OR CONTAINS(LOWER(c.ocr_text), @query) OR EXISTS(SELECT VALUE t FROM t IN c.tags WHERE CONTAINS(LOWER(t.name), @query)) OR EXISTS(SELECT VALUE b FROM b IN c.brands WHERE CONTAINS(LOWER(b), @query)))"]
    parameters = [{"name": "@query", "value": query_lower}]

    if category:
        query_parts.append("AND STRINGEQUALS(c.category, @category, true)")
        parameters.append({"name": "@category", "value": category})

    db_query = " ".join(query_parts)
    
    top_matches = []
    total_results = 0

    try:
        db_results = list(container.query_items(
            query=db_query,
            parameters=parameters,
            enable_cross_partition_query=True
        ))

        scored_results = []
        for product in db_results:
            # Calculate similarity scores
            name_score = fuzz.token_set_ratio(query_lower, product.get("name", "").lower()) / 100.0
            
            # Tag score: max similarity with any tag
            prod_tags = [t["name"].lower() for t in product.get("tags", [])]
            tag_score = max([fuzz.token_set_ratio(query_lower, t) for t in prod_tags]) / 100.0 if prod_tags else 0
            
            # Brand score: max similarity with any brand
            prod_brands = [b.lower() for b in product.get("brands", [])]
            brand_score = max([fuzz.token_set_ratio(query_lower, b) for b in prod_brands]) / 100.0 if prod_brands else 0
            
            # OCR score
            ocr_text_val = product.get("ocr_text", "").lower()
            ocr_score = fuzz.partial_ratio(query_lower, ocr_text_val) / 100.0 if ocr_text_val else 0
            
            # Weighted Final Score
            # (0.5 * name_score) + (0.2 * tag_score) + (0.1 * brand_score) + (0.2 * ocr_score)
            final_score = (0.5 * name_score) + (0.2 * tag_score) + (0.1 * brand_score) + (0.2 * ocr_score)
            
            product["match_score"] = round(final_score, 3)
            scored_results.append(product)

        # Sort and limit
        scored_results.sort(key=lambda x: x["match_score"], reverse=True)
        top_matches = scored_results[:limit]
        total_results = len(scored_results)

    except Exception as e:
        logging.error(f"Text search query failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Search failed")

    # 2. Save to SearchHistory
    if search_history_container:
        detected_category = top_matches[0].get("category", "uncategorized") if top_matches else "uncategorized"
        
        top_match_preview = None
        if top_matches:
            top_match_preview = {
                "productId": top_matches[0].get("productId"),
                "name": top_matches[0].get("name"),
                "imageUrl": top_matches[0].get("imageUrl"),
                "match_score": top_matches[0].get("match_score")
            }

        search_record = {
            "id": search_id,
            "userId": user_id,
            "queryText": query,
            "category": detected_category,
            "filterCategory": category,
            "timestamp": datetime.utcnow().isoformat(),
            "searchImageUrl": None,
            "topMatch": top_match_preview,
            "resultCount": total_results,
            "searchType": "text"
        }
        try:
            search_history_container.upsert_item(search_record)
        except Exception as e:
            logging.error(f"Failed to save text search history: {str(e)}")

    return {
        "message": f"Found {total_results} matching products",
        "results": top_matches,
        "searchId": search_id,
        "filter_applied": category,
        "search_type": "text"
    }


@app.get("/products")
async def list_products(category: Optional[str] = None, limit: int = 50, offset: int = 0):
    """
    Returns products based on a category name input. 
    Matches are case-insensitive for better user experience.
    """
    if not container:
        raise HTTPException(status_code=500, detail="Database connection not initialized")
    
    # Base query
    query_str = "SELECT * FROM c"
    params = []
    
    # If the user input a category name, filter by it (case-insensitive)
    if category:
        # Using STRINGEQUALS for case-insensitive matching in Cosmos DB
        query_str += " WHERE STRINGEQUALS(c.category, @category, true)"
        params.append({"name": "@category", "value": category})
    
    # Add pagination
    query_str += f" OFFSET {offset} LIMIT {limit}"
    
    try:
        results = list(container.query_items(
            query=query_str,
            parameters=params,
            enable_cross_partition_query=True
        ))
        
        # Clean up internal Cosmos DB fields
        for item in results:
            item.pop("_rid", None)
            item.pop("_self", None)
            item.pop("_etag", None)
            item.pop("_attachments", None)
            item.pop("_ts", None)

        return {
            "category_queried": category,
            "products": results,
            "count": len(results),
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        logging.error(f"Failed to filter products by category: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve products for this category")


@app.get("/categories")
async def list_unique_categories():
    """
    Returns a list of all unique categories available in the database.
    This is useful for populating filter dropdowns in the frontend.
    """
    if not container:
        raise HTTPException(status_code=500, detail="Database connection not initialized")
    
    # Cosmos DB query to get distinct categories
    query_str = "SELECT DISTINCT VALUE c.category FROM c WHERE IS_DEFINED(c.category)"
    
    try:
        results = list(container.query_items(
            query=query_str,
            enable_cross_partition_query=True
        ))
        
        # Sort categories for better UX
        categories = sorted([cat for cat in results if cat])
        
        return {
            "categories": categories,
            "count": len(categories)
        }
    except Exception as e:
        logging.error(f"Failed to fetch unique categories: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve categories")


@app.get("/products/trending")
async def get_trending_products():
    """
    Returns the most searched products recently by aggregating the search history.
    Fixed to last 30 days and top 5 products.
    """
    if not search_history_container or not container:
        raise HTTPException(status_code=500, detail="Database connection not initialized")
    
    # System defaults
    DAYS = 30
    LIMIT = 5
    
    # 1. Calculate the start timestamp for the lookback period
    from datetime import timedelta
    start_date = (datetime.utcnow() - timedelta(days=DAYS)).isoformat()
    
    # 2. Query SearchHistory for recent top matches
    query = "SELECT c.topMatch.productId FROM c WHERE c.timestamp >= @start_date AND IS_DEFINED(c.topMatch.productId)"
    parameters = [{"name": "@start_date", "value": start_date}]
    
    try:
        results = list(search_history_container.query_items(
            query=query,
            parameters=parameters,
            enable_cross_partition_query=True
        ))
        
        # 3. Aggregate product IDs
        id_counts = defaultdict(int)
        for item in results:
            pid = item.get("productId")
            if pid:
                id_counts[pid] += 1
        
        # 4. Sort by frequency and take the top N
        sorted_pids = sorted(id_counts.items(), key=lambda x: x[1], reverse=True)[:LIMIT]
        top_pids = [pid for pid, count in sorted_pids]
        
        if not top_pids:
            return {"trending_products": [], "count": 0}
        
        # 5. Fetch full product metadata for the top IDs
        pid_placeholders = [f"@pid{i}" for i in range(len(top_pids))]
        pid_params = [{"name": f"@pid{i}", "value": pid} for i, pid in enumerate(top_pids)]
        
        query_str = f"SELECT * FROM c WHERE c.productId IN ({', '.join(pid_placeholders)})"
        
        db_products = list(container.query_items(
            query=query_str,
            parameters=pid_params,
            enable_cross_partition_query=True
        ))
        
        # Add the search count to the product data for the UI
        trending_products = []
        for prod in db_products:
            prod_id = prod.get("productId")
            prod["search_count"] = id_counts.get(prod_id, 0)
            
            # Clean up internal Cosmos fields
            prod.pop("_rid", None)
            prod.pop("_self", None)
            prod.pop("_etag", None)
            prod.pop("_attachments", None)
            prod.pop("_ts", None)
            
            trending_products.append(prod)
            
        # Re-sort because the IN query doesn't guarantee order
        trending_products.sort(key=lambda x: x["search_count"], reverse=True)
        
        return {
            "trending_products": trending_products,
            "count": len(trending_products)
        }
    except Exception as e:
        logging.error(f"Failed to fetch trending products: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve trending products")


@app.get("/search/history")
async def get_search_history(user_id: str, category: Optional[str] = None, limit: int = 50, offset: int = 0):
    """
    Returns detailed search history grouped by day and category with optional category filtering.
    """
    if not search_history_container:
        raise HTTPException(status_code=500, detail="Search history container not initialized")
    
    # Base query
    query_str = "SELECT * FROM c WHERE c.userId = @userId"
    params = [{"name": "@userId", "value": user_id}]
    
    # Optional category filtering
    if category:
        query_str += " AND STRINGEQUALS(c.category, @category, true)"
        params.append({"name": "@category", "value": category})
    
    # Sorting and pagination
    query_str += " ORDER BY c.timestamp DESC"
    query_str += f" OFFSET {offset} LIMIT {limit}"
    
    try:
        results = list(search_history_container.query_items(
            query=query_str,
            parameters=params,
            enable_cross_partition_query=False
        ))
        
        history = defaultdict(lambda: defaultdict(list))
        for item in results:
            day = item["timestamp"].split("T")[0]
            category = item["category"]
            
            clean_item = {
                "searchId": item.get("id"),
                "timestamp": item.get("timestamp"),
                "searchImageUrl": item.get("searchImageUrl"),
                "topMatch": item.get("topMatch"),
                "resultCount": item.get("resultCount")
            }
            history[day][category].append(clean_item)
            
        return {
            "user_id": user_id,
            "history": history,
            "count": len(results),
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        logging.error(f"Failed to query search history: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve search history")


@app.delete("/search/history/{search_id}")
async def delete_search_history_item(user_id: str, search_id: str):
    """
    Deletes a specific search history item.
    """
    if not search_history_container:
        raise HTTPException(status_code=500, detail="Search history container not initialized")
    
    try:
        search_history_container.delete_item(item=search_id, partition_key=user_id)
        return {"message": "Search history item deleted successfully"}
    except Exception as e:
        logging.error(f"Failed to delete history item: {str(e)}")
        raise HTTPException(status_code=404, detail="Item not found or could not be deleted")
