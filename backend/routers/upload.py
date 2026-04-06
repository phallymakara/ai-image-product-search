import uuid
import hashlib
import logging
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends

from database.cosmos import get_product_container
from services.storage import upload_to_blob, get_blob_client
from services.vision import analyze_image, ocr_image, extract_tags, extract_brands, detect_name, detect_category

router = APIRouter(tags=["Upload"])


@router.post("/upload")
async def upload_image(
    user_id: str = Form(...),
    name: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    file: UploadFile = File(...),
    container = Depends(get_product_container),
    blob_client = Depends(get_blob_client)
):
    """
    Uploads an image, detects duplicates, analyzes with Azure Vision, and saves to Cosmos DB.
    """
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
        items = container.query_items(
            query="SELECT * FROM c WHERE c.image_hash = @hash",
            parameters=[{"name": "@hash", "value": image_hash}]
        )
        existing = [item async for item in items]
        if existing:
            return {
                "message": "Image already exists in the system", 
                "is_duplicate": True, 
                "data": existing[0]
            }
    except Exception as e:
        logging.error(f"Duplicate check failed: {str(e)}")

    product_id = f"P{str(uuid.uuid4())[:7]}"

    # 2. AI Analysis (do this BEFORE blob upload to avoid Azure Function race condition)
    analysis_result = analyze_image(file_bytes)
    ocr_text = ocr_image(file_bytes)
    tags = extract_tags(analysis_result)
    brands = extract_brands(analysis_result)

    # 3. Metadata Logic - User input takes priority over AI detection
    logging.info(f"Upload received - name: '{name}', category: '{category}'")
    
    if name and name.strip():
        final_name = name.strip()
        logging.info(f"Using user-provided name: '{final_name}'")
    else:
        final_name = detect_name(analysis_result, brands, tags)
        logging.info(f"Using AI-detected name: '{final_name}'")
    
    if category and category.strip():
        final_category = category.strip()
        logging.info(f"Using user-provided category: '{final_category}'")
    else:
        final_category = detect_category(analysis_result, tags)
        logging.info(f"Using AI-detected category: '{final_category}'")
    
    name = final_name
    category = final_category

    # 4. Save to Cosmos DB FIRST (before blob upload to prevent Azure Function race condition)
    product_data = {
        "id": product_id,
        "productId": product_id,
        "image_hash": image_hash,
        "name": name,
        "category": category,
        "tags": tags,
        "brands": brands,
        "ocr_text": ocr_text,
        "imageUrl": "",  # Will be updated after blob upload
        "userId": user_id,
        "enhanced_search": True,
        "upload_source": "api"
    }

    try:
        await container.upsert_item(product_data)
        logging.info(f"Product {product_id} saved to Cosmos DB")
    except Exception as e:
        logging.error(f"Database save failed for {product_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database save failed for {product_id}: {str(e)}")

    # 5. Upload to Storage (after DB save - Azure Function will find existing product)
    try:
        image_url = upload_to_blob(file_bytes, product_id, user_id, blob_client)
        # Update the imageUrl in Cosmos DB
        product_data["imageUrl"] = image_url
        await container.upsert_item(product_data)
        logging.info(f"Product {product_id} uploaded to blob storage and imageUrl updated")
    except Exception as e:
        logging.error(f"Storage upload failed for {product_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Storage upload failed: {str(e)}")

    return {
        "message": "Product uploaded successfully", 
        "is_duplicate": False, 
        "data": product_data
    }

    # 5. Save to Cosmos DB
    try:
        await container.upsert_item(product_data)
        logging.info(f"Product {product_id} uploaded successfully by user {user_id}")
    except Exception as e:
        logging.error(f"Database save failed for {product_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database save failed: {str(e)}")

    return {
        "message": "Product uploaded successfully", 
        "is_duplicate": False, 
        "data": product_data
    }
