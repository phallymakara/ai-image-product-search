import uuid
import logging
from datetime import datetime
from collections import defaultdict
from typing import Optional, List
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends

from database.cosmos import get_product_container, get_history_container
from services.storage import upload_search_image, get_blob_client
from services.vision import analyze_image, ocr_image, extract_tags, extract_brands, detect_category
from services.matching import score_product_by_image, score_product_by_text
from services.vector_service import vector_service
from services.index_service import index_service

router = APIRouter(tags=["Search"])

async def get_products_by_ids(container, product_ids: List[str]):
    """Helper to fetch multiple products by their productId."""
    if not product_ids:
        return []
    try:
        query = "SELECT * FROM c WHERE ARRAY_CONTAINS(@ids, c.productId)"
        items = container.query_items(
            query=query,
            parameters=[{"name": "@ids", "value": product_ids}]
        )
        return [item async for item in items]
    except Exception as e:
        logging.error(f"Failed to fetch products by IDs: {str(e)}")
        return []

@router.post("/search")
async def search_similar_product(
    user_id: str,
    file: UploadFile = File(...),
    category: Optional[str] = None,
    container = Depends(get_product_container),
    history_container = Depends(get_history_container),
    blob_client = Depends(get_blob_client)
):
    """
    Semantic Image-based product search:
    1. CLIP Vector Retrieval (Semantic)
    2. Azure Vision Analysis (Contextual Re-ranking)
    """
    if not container:
        raise HTTPException(status_code=500, detail="Database connection not initialized")

    try:
        file_bytes = await file.read()
    except Exception as e:
        logging.error(f"Failed to read search file: {str(e)}")
        raise HTTPException(status_code=400, detail="Failed to read search file")

    search_id = f"S{str(uuid.uuid4())[:7]}"

    # 1. Upload for history
    search_image_url = upload_search_image(file_bytes, search_id, user_id, blob_client)

    # 2. SEMANTIC RETRIEVAL (CLIP + FAISS)
    # This replaces the broad SQL keyword search
    image_vector = vector_service.get_image_embedding(file_bytes)
    vector_results = index_service.search(image_vector, top_k=40)
    
    if not vector_results:
        return {"message": "No visually similar products found", "results": [], "searchId": search_id}
        
    vector_map = {pid: score for pid, score in vector_results}
    
    # 3. CONTEXTUAL ANALYSIS (Azure Vision)
    # Used for boosting results with specific OCR text or Brands
    analysis_result = analyze_image(file_bytes)
    ocr_text = ocr_image(file_bytes).lower()
    search_tags_data = extract_tags(analysis_result)
    search_tags = [t["name"] for t in search_tags_data]
    search_brands = [b.lower() for b in extract_brands(analysis_result)]
    detected_category = detect_category(analysis_result, search_tags_data)

    # 4. FETCH & HYBRID SCORING
    # Fetch ONLY the semantic candidates from Cosmos DB
    db_results = await get_products_by_ids(container, list(vector_map.keys()))
    
    scored_products = []
    for product in db_results:
        pid = product.get("productId")
        v_score = vector_map.get(pid, 0.0)
        
        # Apply the weighted scoring logic (Vector + Tags + OCR + Brand)
        product["match_score"] = score_product_by_image(
            product, search_tags, search_brands, ocr_text, vector_score=v_score
        )
        scored_products.append(product)

    # Deduplicate by productId (keep highest score)
    unique_products = {}
    for p in scored_products:
        pid = p["productId"]
        if pid not in unique_products or p["match_score"] > unique_products[pid]["match_score"]:
            unique_products[pid] = p
    
    final_results = list(unique_products.values())

    # 5. FILTER & RANKING
    # Filter by category if requested by user
    if category:
        final_results = [p for p in final_results if p.get("category", "").lower() == category.lower()]

    # Sort by the final combined score
    final_results.sort(key=lambda x: x["match_score"], reverse=True)
    
    top_matches = final_results[:15]
    total_results = len(final_results)
    
    # Cleanup Cosmos internal fields
    for m in top_matches:
        for key in ["_rid", "_self", "_etag", "_attachments", "_ts"]:
            m.pop(key, None)

    # 6. HISTORY LOGGING
    if history_container:
        top_match_preview = {
            "productId": top_matches[0].get("productId"),
            "name": top_matches[0].get("name"),
            "imageUrl": top_matches[0].get("imageUrl"),
            "match_score": top_matches[0].get("match_score")
        } if top_matches else None
        
        try:
            await history_container.upsert_item({
                "id": search_id,
                "userId": user_id,
                "category": detected_category,
                "filterCategory": category,
                "timestamp": datetime.utcnow().isoformat(),
                "searchImageUrl": search_image_url,
                "topMatch": top_match_preview,
                "resultCount": total_results,
                "searchType": "image"
            })
        except Exception as e:
            logging.error(f"Failed to save search history for {search_id}: {str(e)}")

    return {
        "message": f"Found {total_results} matching products",
        "results": top_matches,
        "searchId": search_id,
        "filter_applied": category,
        "search_type": "image"
    }


@router.get("/search/text")
async def search_by_text(
    user_id: str,
    query: str,
    category: Optional[str] = None,
    limit: int = 15,
    container = Depends(get_product_container),
    history_container = Depends(get_history_container)
):
    """
    Hybrid Text-based product search: CLIP Vectors + Keyword Matching.
    """
    if not container:
        raise HTTPException(status_code=500, detail="Database connection not initialized")

    search_id = f"T{str(uuid.uuid4())[:7]}"
    query_lower = query.strip().lower()

    if not query_lower:
        raise HTTPException(status_code=400, detail="Search query cannot be empty")

    # 1. Vector Search (Text-to-Image)
    query_vector = vector_service.get_text_embedding(query_lower)
    vector_results = index_service.search(query_vector, top_k=limit * 2)
    vector_map = {pid: score for pid, score in vector_results}
    
    # 2. Fetch Initial Candidates
    db_results = await get_products_by_ids(container, list(vector_map.keys()))

    # 3. Keyword Search
    query_parts = [
        "SELECT * FROM c WHERE (CONTAINS(LOWER(c.name), @query) OR CONTAINS(LOWER(c.ocr_text), @query) "
        "OR EXISTS(SELECT VALUE t FROM t IN c.tags WHERE CONTAINS(LOWER(t.name), @query)) "
        "OR EXISTS(SELECT VALUE b FROM b IN c.brands WHERE CONTAINS(LOWER(b), @query)))"
    ]
    parameters = [{"name": "@query", "value": query_lower}]

    if category:
        query_parts.append("AND STRINGEQUALS(c.category, @category, true)")
        parameters.append({"name": "@category", "value": category})

    try:
        items = container.query_items(query=" ".join(query_parts), parameters=parameters)
        keyword_results = [item async for item in items]
        
        # Merge keyword results
        existing_ids = {p["productId"] for p in db_results}
        for p in keyword_results:
            if p["productId"] not in existing_ids:
                db_results.append(p)
                
    except Exception as e:
        logging.error(f"Text search keyword query failed: {str(e)}")

    # 4. Scoring & Ranking
    scored_products = []
    for product in db_results:
        pid = product.get("productId")
        v_score = vector_map.get(pid, 0.0)
        product["match_score"] = score_product_by_text(product, query_lower, vector_score=v_score)
        scored_products.append(product)

    # Deduplicate by productId (keep highest score)
    unique_products = {}
    for p in scored_products:
        pid = p["productId"]
        if pid not in unique_products or p["match_score"] > unique_products[pid]["match_score"]:
            unique_products[pid] = p
    
    final_results = list(unique_products.values())
    final_results.sort(key=lambda x: x["match_score"], reverse=True)
    
    top_matches = final_results[:limit]
    total_results = len(final_results)
    
    for m in top_matches:
        for key in ["_rid", "_self", "_etag", "_attachments", "_ts"]:
            m.pop(key, None)

    # 5. History Logging
    if history_container:
        top_match_preview = {
            "productId": top_matches[0].get("productId"),
            "name": top_matches[0].get("name"),
            "imageUrl": top_matches[0].get("imageUrl"),
            "match_score": top_matches[0].get("match_score")
        } if top_matches else None
        
        try:
            await history_container.upsert_item({
                "id": search_id,
                "userId": user_id,
                "queryText": query,
                "category": top_matches[0].get("category", "uncategorized") if top_matches else "uncategorized",
                "filterCategory": category,
                "timestamp": datetime.utcnow().isoformat(),
                "searchImageUrl": None,
                "topMatch": top_match_preview,
                "resultCount": total_results,
                "searchType": "text"
            })
        except Exception as e:
            logging.error(f"Failed to save text search history for {search_id}: {str(e)}")

    return {
        "message": f"Found {total_results} matching products",
        "results": top_matches,
        "searchId": search_id,
        "filter_applied": category,
        "search_type": "text"
    }


@router.get("/search/history")
async def get_search_history(
    user_id: str,
    category: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    history_container = Depends(get_history_container)
):
    """Returns search history grouped by day."""
    if not history_container:
        raise HTTPException(status_code=500, detail="Search history container not initialized")

    query_str = "SELECT * FROM c WHERE c.userId = @userId"
    params = [{"name": "@userId", "value": user_id}]

    if category:
        query_str += " AND STRINGEQUALS(c.category, @category, true)"
        params.append({"name": "@category", "value": category})

    query_str += f" ORDER BY c.timestamp DESC OFFSET {offset} LIMIT {limit}"

    try:
        items = history_container.query_items(
            query=query_str, parameters=params
        )
        results = [item async for item in items]
        
        history = defaultdict(list)
        for item in results:
            day = item["timestamp"].split("T")[0]
            history[day].append({
                "searchId": item.get("id"),
                "timestamp": item.get("timestamp"),
                "searchType": item.get("searchType", "image"),
                "queryText": item.get("queryText"),
                "searchImageUrl": item.get("searchImageUrl"),
                "category": item.get("category"),
                "topMatch": item.get("topMatch"),
                "resultCount": item.get("resultCount")
            })
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


@router.get("/search/recent")
async def get_recent_searches(
    user_id: str,
    history_container = Depends(get_history_container)
):
    """Returns a list of recent searches with their type for filtering."""
    if not history_container:
        raise HTTPException(status_code=500, detail="Search history container not initialized")

    try:
        items = history_container.query_items(
            query="SELECT c.searchType, c.queryText, c.category, c.timestamp FROM c WHERE c.userId = @userId ORDER BY c.timestamp DESC OFFSET 0 LIMIT 10",
            parameters=[{"name": "@userId", "value": user_id}]
        )
        results = [item async for item in items]
        
        return {"user_id": user_id, "recent_searches": results, "count": len(results)}
    except Exception as e:
        logging.error(f"Failed to fetch recent searches for {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve recent searches")


@router.delete("/search/history/{search_id}")
async def delete_search_history_item(
    user_id: str, 
    search_id: str,
    history_container = Depends(get_history_container)
):
    """Deletes a specific search history item."""
    if not history_container:
        raise HTTPException(status_code=500, detail="Search history container not initialized")

    try:
        await history_container.delete_item(item=search_id, partition_key=user_id)
        return {"message": "Search history item deleted successfully"}
    except Exception as e:
        logging.error(f"Failed to delete history item {search_id}: {str(e)}")
        raise HTTPException(status_code=404, detail="Item not found or could not be deleted")
