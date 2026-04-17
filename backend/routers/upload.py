import uuid
import hashlib
import logging
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends

from database.cosmos import get_product_container
from services.storage import upload_to_blob, get_blob_client
from services.vision import analyze_image, ocr_image, extract_tags, extract_brands, detect_name, detect_category
from services.vector_service import vector_service
from services.index_service import index_service

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
    Uploads an image, detects duplicates, analyzes with Azure Vision/CLIP, and saves to Cosmos DB/FAISS.
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

    # 2. AI Analysis (Azure Vision + CLIP Vector)
    analysis_result = analyze_image(file_bytes)
    ocr_text = ocr_image(file_bytes)
    tags = extract_tags(analysis_result)
    brands = extract_brands(analysis_result)
    
    # Generate CLIP Vector
    vector = vector_service.get_image_embedding(file_bytes)

    # 3. Metadata Logic - User input takes priority over AI detection
    logging.info(f"Upload received - name: '{name}', category: '{category}'")
    
    if name and name.strip():
        final_name = name.strip()
    else:
        final_name = detect_name(analysis_result, brands, tags)
    
    if category and category.strip():
        final_category = category.strip()
    else:
        # Improved Auto-Category using CLIP Zero-Shot
        try:
            # 1. Get existing categories as targets
            cat_items = container.query_items(
                query="SELECT DISTINCT VALUE c.category FROM c WHERE IS_DEFINED(c.category)"
            )
            target_categories = [cat async for cat in cat_items if cat]
            
            # Default fallback categories if DB is empty
            if not target_categories:
                target_categories = ["Electronics", "Clothing", "Home & Garden", "Beauty", "Groceries", "Toys"]
            
            final_category = vector_service.classify_image(file_bytes, target_categories)
            logging.info(f"Using CLIP zero-shot category: '{final_category}'")
        except Exception as e:
            logging.error(f"CLIP classification failed, falling back to Vision API: {str(e)}")
            final_category = detect_category(analysis_result, tags)
    
    name = final_name
    category = final_category

    # 4. Save to Cosmos DB
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
        raise HTTPException(status_code=500, detail=f"Database save failed: {str(e)}")

    # 5. Add to Vector Index
    if vector:
        index_service.add_product(product_id, vector)
        index_service.save_index()
        logging.info(f"Product {product_id} added to FAISS index")

    # 6. Upload to Storage
    try:
        image_url = upload_to_blob(file_bytes, product_id, user_id, blob_client)
        product_data["imageUrl"] = image_url
        await container.upsert_item(product_data)
        logging.info(f"Product {product_id} uploaded to blob storage")
    except Exception as e:
        logging.error(f"Storage upload failed for {product_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Storage upload failed: {str(e)}")

    return {
        "message": "Product uploaded successfully", 
        "is_duplicate": False, 
        "data": product_data
    }
