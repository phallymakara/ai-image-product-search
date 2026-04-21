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
    Semantic Image-based product search using Cosmos DB Vector Search.
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

    # 2. Vector Embedding Generation
    image_vector = vector_service.get_image_embedding(file_bytes)
    if not image_vector:
        raise HTTPException(status_code=500, detail="Failed to generate image vector")

    # 3. CONTEXTUAL ANALYSIS (Azure Vision)
    analysis_result = analyze_image(file_bytes)
    ocr_text = ocr_image(file_bytes).lower()
    search_tags_data = extract_tags(analysis_result)
    search_tags = [t["name"] for t in search_tags_data]
    search_brands = [b.lower() for b in extract_brands(analysis_result)]
    detected_category = detect_category(analysis_result, search_tags_data)

    # 4. COSMOS DB VECTOR SEARCH
    query_parts = [
        "SELECT TOP 40 c.id, c.productId, c.name, c.category, c.tags, c.brands, c.ocr_text, c.imageUrl, c.userId, "
        "VectorDistance(c.vector, @dist) AS vector_score FROM c "
    ]
    parameters = [{"name": "@dist", "value": image_vector}]

    if category:
        query_parts.append("WHERE STRINGEQUALS(c.category, @category, true) ")
        parameters.append({"name": "@category", "value": category})

    query_parts.append("ORDER BY VectorDistance(c.vector, @dist)")
    
    try:
        items = container.query_items(query=" ".join(query_parts), parameters=parameters)
        db_results = [item async for item in items]
    except Exception as e:
        logging.error(f"Cosmos DB vector search failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Vector search failed")

    # 5. HYBRID SCORING & DEDUPLICATION
    unique_products = {}
    for product in db_results:
        pid = product["productId"]
        v_score = product.get("vector_score", 0.0)
        
        # Convert vector score (distance) to similarity (0 to 1)
        # Note: VectorDistance for cosine returns (1 - cosine_similarity)
        similarity = 1.0 - v_score
        
        product["match_score"] = score_product_by_image(
            product, search_tags, search_brands, ocr_text, vector_score=similarity
        )
        
        if pid not in unique_products or product["match_score"] > unique_products[pid]["match_score"]:
            unique_products[pid] = product
    
    final_results = sorted(unique_products.values(), key=lambda x: x["match_score"], reverse=True)
    top_matches = final_results[:15]
    total_results = len(final_results)

    for m in top_matches:
        for key in ["_rid", "_self", "_etag", "_attachments", "_ts", "vector"]:
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
    Hybrid Text-based search using Cosmos DB Vector Search.
    """
    if not container:
        raise HTTPException(status_code=500, detail="Database connection not initialized")

    search_id = f"T{str(uuid.uuid4())[:7]}"
    query_lower = query.strip().lower()

    if not query_lower:
        raise HTTPException(status_code=400, detail="Search query cannot be empty")

    # 1. Vector Search (Text-to-Image)
    query_vector = vector_service.get_text_embedding(query_lower)
    
    # 2. COSMOS DB VECTOR SEARCH
    query_parts = [
        "SELECT TOP @limit c.id, c.productId, c.name, c.category, c.tags, c.brands, c.ocr_text, c.imageUrl, c.userId, "
        "VectorDistance(c.vector, @dist) AS vector_score FROM c "
    ]
    parameters = [
        {"name": "@dist", "value": query_vector},
        {"name": "@limit", "value": limit * 2}
    ]

    if category:
        query_parts.append("WHERE STRINGEQUALS(c.category, @category, true) ")
        parameters.append({"name": "@category", "value": category})

    query_parts.append("ORDER BY VectorDistance(c.vector, @dist)")

    try:
        items = container.query_items(query=" ".join(query_parts), parameters=parameters)
        db_results = [item async for item in items]
    except Exception as e:
        logging.error(f"Cosmos DB text vector search failed: {str(e)}")
        db_results = []

    # 3. KEYWORD SEARCH (Fallback / Hybrid)
    keyword_query = (
        "SELECT * FROM c WHERE (CONTAINS(LOWER(c.name), @query) OR CONTAINS(LOWER(c.ocr_text), @query) "
        "OR EXISTS(SELECT VALUE t FROM t IN c.tags WHERE CONTAINS(LOWER(t.name), @query)) "
        "OR EXISTS(SELECT VALUE b FROM b IN c.brands WHERE CONTAINS(LOWER(b), @query)))"
    )
    keyword_params = [{"name": "@query", "value": query_lower}]
    if category:
        keyword_query += " AND STRINGEQUALS(c.category, @category, true)"
        keyword_params.append({"name": "@category", "value": category})

    try:
        kw_items = container.query_items(query=keyword_query, parameters=keyword_params)
        keyword_results = [item async for item in kw_items]
        
        # Merge keyword results into db_results
        existing_pids = {p["productId"] for p in db_results}
        for p in keyword_results:
            if p["productId"] not in existing_pids:
                db_results.append(p)
    except Exception as e:
        logging.error(f"Text keyword search failed: {str(e)}")

    # 4. SCORING & DEDUPLICATION
    unique_products = {}
    for product in db_results:
        pid = product.get("productId")
        v_dist = product.get("vector_score", 1.0) # Default to 1.0 distance (0 similarity)
        similarity = 1.0 - v_dist if "vector_score" in product else 0.0
        
        product["match_score"] = score_product_by_text(product, query_lower, vector_score=similarity)
        
        if pid not in unique_products or product["match_score"] > unique_products[pid]["match_score"]:
            unique_products[pid] = product

    final_results = sorted(unique_products.values(), key=lambda x: x["match_score"], reverse=True)
    top_matches = final_results[:limit]
    total_results = len(final_results)
    
    for m in top_matches:
        for key in ["_rid", "_self", "_etag", "_attachments", "_ts", "vector"]:
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
