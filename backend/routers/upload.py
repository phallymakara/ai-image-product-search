import uuid
import hashlib
import logging
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from database.cosmos import get_product_container
from services.storage import upload_to_blob
from services.vision import analyze_image, ocr_image, extract_tags, extract_brands, detect_name, detect_category

router = APIRouter(tags=["Upload"])


@router.post("/upload")
async def upload_image(
    user_id: str,
    name: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    file: UploadFile = File(...)
):
    """
    Uploads an image, detects duplicates, analyzes with Azure Vision, and saves to Cosmos DB.
    """
    container = get_product_container()
    if not container:
        logging.error("Database connection not initialized during upload.")
        raise HTTPException(status_code=500, detail="Database connection not initialized")

    try:
        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(status_code=400, detail="Empty file uploaded")
    except Exception as e:
        logging.error(f"Failed to read upload file: {str(e)}")
        raise HTTPException(status_code=400, detail="Failed to read upload file")

    # 1. Duplicate detection
    image_hash = hashlib.sha256(file_bytes).hexdigest()
    try:
        existing = list(container.query_items(
            query="SELECT * FROM c WHERE c.image_hash = @hash",
            parameters=[{"name": "@hash", "value": image_hash}],
            enable_cross_partition_query=True
        ))
        if existing:
            return {
                "message": "Image already exists in the system", 
                "is_duplicate": True, 
                "data": existing[0]
            }
    except Exception as e:
        logging.error(f"Duplicate check failed: {str(e)}")
        # Continue if duplicate check fails? Or fail? Usually safer to continue or log.

    product_id = f"P{str(uuid.uuid4())[:7]}"

    # 2. Upload to Storage
    try:
        image_url = upload_to_blob(file_bytes, product_id, user_id)
    except Exception as e:
        logging.error(f"Storage upload failed for {product_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Storage upload failed: {str(e)}")

    # 3. AI Analysis
    analysis_result = analyze_image(file_bytes)
    ocr_text = ocr_image(file_bytes)
    tags = extract_tags(analysis_result)
    brands = extract_brands(analysis_result)

    # 4. Metadata Logic
    is_name_missing = not name or name.strip() == "" or name.lower() == "string"
    is_cat_missing = not category or category.strip() == "" or category.lower() == "string"

    if is_name_missing:
        name = detect_name(analysis_result, brands, tags)
    if is_cat_missing:
        category = detect_category(analysis_result, tags)

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

    # 5. Save to Cosmos DB
    try:
        container.upsert_item(product_data)
        logging.info(f"Product {product_id} uploaded successfully by user {user_id}")
    except Exception as e:
        logging.error(f"Database save failed for {product_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database save failed: {str(e)}")

    return {
        "message": "Product uploaded successfully", 
        "is_duplicate": False, 
        "data": product_data
    }
