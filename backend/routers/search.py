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

router = APIRouter(tags=["Search"])


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
    Image-based product search. 
    Score = 0.4*tags + 0.3*brands + 0.3*ocr.
    Supports OCR-only search if no tags/brands are found.
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

    # 2. Analyze
    analysis_result = analyze_image(file_bytes)
    ocr_text = ocr_image(file_bytes).lower()
    search_tags_data = extract_tags(analysis_result)
    search_tags = [t["name"] for t in search_tags_data]
    search_brands = [b.lower() for b in extract_brands(analysis_result)]
    detected_category = detect_category(analysis_result, search_tags_data)

    top_matches = []
    total_results = 0

    # 3. Dynamic Query Construction
    # We query if there's ANY evidence (tags, brands, or OCR text)
    if search_tags or search_brands or ocr_text:
        query_parts = ["SELECT * FROM c WHERE ("]
        conditions = []
        parameters = []

        if search_tags:
            conditions.append("EXISTS(SELECT VALUE t FROM t IN c.tags WHERE ARRAY_CONTAINS(@tags, t.name))")
            parameters.append({"name": "@tags", "value": search_tags})

        if search_brands:
            conditions.append("EXISTS(SELECT VALUE b FROM b IN c.brands WHERE ARRAY_CONTAINS(@brands, b))")
            parameters.append({"name": "@brands", "value": [b.capitalize() for b in search_brands]})

        if ocr_text:
            # Broad search on name or ocr_text for candidates
            # Using CONTAINS for initial filtering to keep candidates manageable
            conditions.append("CONTAINS(LOWER(c.ocr_text), @ocr) OR CONTAINS(LOWER(c.name), @ocr)")
            parameters.append({"name": "@ocr", "value": ocr_text[:30]}) # Use first 30 chars for broad filter

        query_parts.append(" OR ".join(conditions))
        query_parts.append(")")

        if category:
            query_parts.append("AND STRINGEQUALS(c.category, @filter_category, true)")
            parameters.append({"name": "@filter_category", "value": category})

        query = " ".join(query_parts)

        try:
            db_results = list(container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True
            ))
            
            # Score each product
            for product in db_results:
                product["match_score"] = score_product_by_image(product, search_tags, search_brands, ocr_text)

            # Filter results for high confidence (only return matches with score > 0.5)
            db_results = [p for p in db_results if p.get("match_score", 0) > 0.5]
            
            db_results.sort(key=lambda x: x["match_score"], reverse=True)
            top_matches = db_results[:5]
            total_results = len(db_results)
        except Exception as e:
            logging.error(f"Search query failed for {search_id}: {str(e)}")

    # 4. History Logging
    if history_container:
        top_match_preview = None
        if top_matches:
            top_match_preview = {
                "productId": top_matches[0].get("productId"),
                "name": top_matches[0].get("name"),
                "imageUrl": top_matches[0].get("imageUrl"),
                "match_score": top_matches[0].get("match_score")
            }
        try:
            history_container.upsert_item({
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
    limit: int = 5,
    container = Depends(get_product_container),
    history_container = Depends(get_history_container)
):
    """
    Text-based product search. 
    Score = 0.5*name + 0.2*tags + 0.1*brands + 0.2*ocr.
    """
    if not container:
        raise HTTPException(status_code=500, detail="Database connection not initialized")

    search_id = f"T{str(uuid.uuid4())[:7]}"
    query_lower = query.strip().lower()

    if not query_lower:
        raise HTTPException(status_code=400, detail="Search query cannot be empty")

    # Construct efficient query
    query_parts = [
        "SELECT * FROM c WHERE (CONTAINS(LOWER(c.name), @query) OR CONTAINS(LOWER(c.ocr_text), @query) "
        "OR EXISTS(SELECT VALUE t FROM t IN c.tags WHERE CONTAINS(LOWER(t.name), @query)) "
        "OR EXISTS(SELECT VALUE b FROM b IN c.brands WHERE CONTAINS(LOWER(b), @query)))"
    ]
    parameters = [{"name": "@query", "value": query_lower}]

    if category:
        query_parts.append("AND STRINGEQUALS(c.category, @category, true)")
        parameters.append({"name": "@category", "value": category})

    top_matches = []
    total_results = 0

    try:
        db_results = list(container.query_items(
            query=" ".join(query_parts),
            parameters=parameters,
            enable_cross_partition_query=True
        ))
        
        for product in db_results:
            product["match_score"] = score_product_by_text(product, query_lower)

        db_results.sort(key=lambda x: x["match_score"], reverse=True)
        top_matches = db_results[:limit]
        total_results = len(db_results)
    except Exception as e:
        logging.error(f"Text search failed for {search_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Search failed")

    # History Logging
    if history_container:
        top_match_preview = None
        if top_matches:
            top_match_preview = {
                "productId": top_matches[0].get("productId"),
                "name": top_matches[0].get("name"),
                "imageUrl": top_matches[0].get("imageUrl"),
                "match_score": top_matches[0].get("match_score")
            }
        try:
            history_container.upsert_item({
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
        results = list(history_container.query_items(
            query=query_str, parameters=params, enable_cross_partition_query=False
        ))
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
    """Returns a simple list of recent search terms (text queries or image categories)."""
    if not history_container:
        raise HTTPException(status_code=500, detail="Search history container not initialized")

    try:
        results = list(history_container.query_items(
            query="SELECT c.searchType, c.queryText, c.category FROM c WHERE c.userId = @userId ORDER BY c.timestamp DESC OFFSET 0 LIMIT 10",
            parameters=[{"name": "@userId", "value": user_id}],
            enable_cross_partition_query=False
        ))
        recent_terms = [
            item.get("queryText") if item.get("searchType") == "text"
            else f"Image: {item.get('category', 'Unknown')}"
            for item in results
        ]
        return {"user_id": user_id, "recent_searches": recent_terms, "count": len(recent_terms)}
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
        history_container.delete_item(item=search_id, partition_key=user_id)
        return {"message": "Search history item deleted successfully"}
    except Exception as e:
        logging.error(f"Failed to delete history item {search_id}: {str(e)}")
        raise HTTPException(status_code=404, detail="Item not found or could not be deleted")
