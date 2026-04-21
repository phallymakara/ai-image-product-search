import uuid
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends

from database.cosmos import get_product_container, get_history_container
from models.product import ProductCreate, ProductUpdate, ProductResponse

router = APIRouter(tags=["Products"])


@router.post("/products", response_model=ProductResponse, status_code=201)
async def create_product(
    product: ProductCreate,
    container = Depends(get_product_container)
):
    """Manually creates a new product."""
    if not container:
        raise HTTPException(status_code=500, detail="Database connection not initialized")
    
    product_id = f"P{str(uuid.uuid4())[:7]}"
    product_data = product.dict()
    product_data["id"] = product_id
    product_data["productId"] = product_id

    try:
        new_product = await container.upsert_item(product_data)
        return new_product
    except Exception as e:
        logging.error(f"Failed to create product: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create product")


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
        history_items = history_container.query_items(
            query="SELECT c.topMatch.productId FROM c WHERE c.timestamp >= @start_date AND IS_DEFINED(c.topMatch.productId)",
            parameters=[{"name": "@start_date", "value": start_date}]
        )
        results = [item async for item in history_items]

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

        product_items = container.query_items(
            query=f"SELECT * FROM c WHERE c.productId IN ({', '.join(pid_placeholders)})",
            parameters=pid_params
        )
        db_products = [item async for item in product_items]

        # 5. Attach counts and cleanup
        trending_products = []
        for prod in db_products:
            prod_id = prod.get("productId")
            prod["search_count"] = id_counts.get(prod_id, 0)
            
            for key in ["_rid", "_self", "_etag", "_attachments", "_ts"]:
                prod.pop(key, None)
            
            trending_products.append(prod)

        trending_products.sort(key=lambda x: x["search_count"], reverse=True)
        return {"trending_products": trending_products, "count": len(trending_products)}
    except Exception as e:
        logging.error(f"Failed to fetch trending products: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve trending products")


@router.get("/categories")
async def list_categories(container = Depends(get_product_container)):
    """Returns all unique product categories."""
    if not container:
        raise HTTPException(status_code=500, detail="Database connection not initialized")

    try:
        items = container.query_items(
            query="SELECT DISTINCT VALUE c.category FROM c WHERE IS_DEFINED(c.category)"
        )
        results = [cat async for cat in items]
        categories = sorted([cat for cat in results if cat])
        return {"categories": categories, "count": len(categories)}
    except Exception as e:
        logging.error(f"Failed to fetch categories: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve categories")


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
        items = container.query_items(query=query_str, parameters=params)
        results = [item async for item in items]
        
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


@router.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: str, 
    category: Optional[str] = None,
    container = Depends(get_product_container)
):
    """
    Retrieves a single product by its ID or productId.
    """
    logging.info(f"API CALL: get_product ID={product_id}, CAT={category}")
    if not container:
        raise HTTPException(status_code=500, detail="Database connection not initialized")
    
    try:
        # 1. Try direct lookup if category is provided
        if category and category.strip():
            try:
                product = await container.read_item(item=product_id, partition_key=category)
                logging.info(f"Found product via read_item: {product_id}")
                return product
            except Exception:
                logging.warning(f"read_item failed for {product_id} in {category}, falling back to query")

        # 2. Query by 'id' across all partitions
        query = "SELECT * FROM c WHERE c.id = @id"
        items = container.query_items(
            query=query,
            parameters=[{"name": "@id", "value": product_id}]
        )
        results = [item async for item in items]
        if results:
            logging.info(f"Found product via c.id: {product_id}")
            return results[0]

        # 3. Query by 'productId' fallback
        query = "SELECT * FROM c WHERE c.productId = @id"
        items = container.query_items(
            query=query,
            parameters=[{"name": "@id", "value": product_id}]
        )
        results = [item async for item in items]
        if results:
            logging.info(f"Found product via c.productId: {product_id}")
            return results[0]

        # 4. Not found
        logging.warning(f"Product {product_id} not found after all attempts.")
        raise HTTPException(status_code=404, detail="Product not found")

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"CRITICAL ERROR in get_product: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.patch("/products/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    category: str,
    product_update: ProductUpdate,
    container = Depends(get_product_container)
):
    """Updates specific fields of a product."""
    if not container:
        raise HTTPException(status_code=500, detail="Database connection not initialized")
    
    try:
        existing_product = await container.read_item(item=product_id, partition_key=category)
        update_data = product_update.dict(exclude_unset=True)
        for key, value in update_data.items():
            existing_product[key] = value
        
        updated_product = await container.upsert_item(existing_product)
        return updated_product
    except Exception as e:
        logging.error(f"Failed to update product {product_id}: {str(e)}")
        raise HTTPException(status_code=404, detail="Product not found or update failed")


@router.delete("/products/{product_id}", status_code=204)
async def delete_product(
    product_id: str,
    category: str,
    container = Depends(get_product_container)
):
    """Deletes a product from the database."""
    if not container:
        raise HTTPException(status_code=500, detail="Database connection not initialized")
    
    try:
        await container.delete_item(item=product_id, partition_key=category)
        return None
    except Exception as e:
        logging.error(f"Failed to delete product {product_id}: {str(e)}")
        raise HTTPException(status_code=404, detail="Product not found or deletion failed")
