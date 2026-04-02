import logging
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends

from database.cosmos import get_product_container, get_history_container

router = APIRouter(tags=["Products"])


@router.get("/products")
async def list_products(
    category: Optional[str] = None, 
    limit: int = 50, 
    offset: int = 0,
    container = Depends(get_product_container)
):
    """Returns products with optional category filtering and pagination."""
    if not container:
        raise HTTPException(status_code=500, detail="Database connection not initialized")

    query_str = "SELECT * FROM c"
    params = []

    if category:
        query_str += " WHERE STRINGEQUALS(c.category, @category, true)"
        params.append({"name": "@category", "value": category})

    query_str += f" OFFSET {offset} LIMIT {limit}"

    try:
        results = list(container.query_items(
            query=query_str, 
            parameters=params, 
            enable_cross_partition_query=True
        ))
        for item in results:
            for key in ["_rid", "_self", "_etag", "_attachments", "_ts"]:
                item.pop(key, None)

        return {
            "category_queried": category, 
            "products": results, 
            "count": len(results), 
            "limit": limit, 
            "offset": offset
        }
    except Exception as e:
        logging.error(f"Failed to list products: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve products")


@router.get("/categories")
async def list_categories(container = Depends(get_product_container)):
    """Returns all unique product categories."""
    if not container:
        raise HTTPException(status_code=500, detail="Database connection not initialized")

    try:
        results = list(container.query_items(
            query="SELECT DISTINCT VALUE c.category FROM c WHERE IS_DEFINED(c.category)",
            enable_cross_partition_query=True
        ))
        categories = sorted([cat for cat in results if cat])
        return {"categories": categories, "count": len(categories)}
    except Exception as e:
        logging.error(f"Failed to fetch categories: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve categories")


@router.get("/products/trending")
async def get_trending_products(
    container = Depends(get_product_container),
    history_container = Depends(get_history_container)
):
    """Returns the most searched products in the last 30 days."""
    if not container or not history_container:
        raise HTTPException(status_code=500, detail="Database connection not initialized")

    DAYS, LIMIT = 30, 5
    start_date = (datetime.utcnow() - timedelta(days=DAYS)).isoformat()

    try:
        # 1. Get recent search matches
        results = list(history_container.query_items(
            query="SELECT c.topMatch.productId FROM c WHERE c.timestamp >= @start_date AND IS_DEFINED(c.topMatch.productId)",
            parameters=[{"name": "@start_date", "value": start_date}],
            enable_cross_partition_query=True
        ))

        # 2. Count occurrences
        id_counts = defaultdict(int)
        for item in results:
            pid = item.get("productId")
            if pid:
                id_counts[pid] += 1

        if not id_counts:
            return {"trending_products": [], "count": 0}

        # 3. Get top product IDs
        sorted_items = sorted(id_counts.items(), key=lambda x: x[1], reverse=True)[:LIMIT]
        top_pids = [pid for pid, _ in sorted_items]

        # 4. Fetch full metadata
        pid_placeholders = [f"@pid{i}" for i in range(len(top_pids))]
        pid_params = [{"name": f"@pid{i}", "value": pid} for i, pid in enumerate(top_pids)]

        db_products = list(container.query_items(
            query=f"SELECT * FROM c WHERE c.productId IN ({', '.join(pid_placeholders)})",
            parameters=pid_params,
            enable_cross_partition_query=True
        ))

        # 5. Attach counts and cleanup
        trending_products = []
        for prod in db_products:
            prod_id = prod.get("productId")
            prod["search_count"] = id_counts.get(prod_id, 0)
            
            for key in ["_rid", "_self", "_etag", "_attachments", "_ts"]:
                prod.pop(key, None)
            
            trending_products.append(prod)

        # 6. Final sort
        trending_products.sort(key=lambda x: x["search_count"], reverse=True)
        
        return {"trending_products": trending_products, "count": len(trending_products)}
    except Exception as e:
        logging.error(f"Failed to fetch trending products: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve trending products")
