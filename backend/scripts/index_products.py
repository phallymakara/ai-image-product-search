import asyncio
import sys
import os
import requests
import logging
from typing import List

# Add backend directory to path so we can import services
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.cosmos import get_product_container
from services.vector_service import vector_service
from services.index_service import index_service
from core.config import settings

logging.basicConfig(level=logging.INFO)

async def backfill_vectors():
    """
    Downloads all product images, generates CLIP vectors, and populates the FAISS index.
    """
    from database.cosmos import init_cosmos, get_product_container
    
    await init_cosmos()
    container = get_product_container()
    
    if not container:
        logging.error("Could not connect to Cosmos DB. Check your .env settings.")
        return

    logging.info("Starting vector backfill process...")
    
    try:
        # Clear existing index to avoid duplicates
        index_service.clear_index()
        
        # 1. Fetch all products
        items = container.query_items(
            query="SELECT c.id, c.productId, c.imageUrl FROM c"
        )
        
        products = [item async for item in items]
        logging.info(f"Found {len(products)} products to index.")

        count = 0
        for product in products:
            product_id = product.get("productId")
            image_url = product.get("imageUrl")
            
            if not image_url or not product_id:
                continue
                
            try:
                # 2. Download Image
                logging.info(f"Processing product {product_id}...")
                response = requests.get(image_url, timeout=10)
                if response.status_code != 200:
                    logging.warning(f"Failed to download image for {product_id}: {image_url}")
                    continue
                
                # 3. Generate Vector
                vector = vector_service.get_image_embedding(response.content)
                
                if vector:
                    # 4. Add to FAISS
                    index_service.add_product(product_id, vector)
                    count += 1
                
            except Exception as e:
                logging.error(f"Error indexing product {product_id}: {str(e)}")

        # 5. Save the index
        if count > 0:
            index_service.save_index()
            logging.info(f"Successfully indexed {count} products.")
        else:
            logging.info("No products were indexed.")

    except Exception as e:
        logging.error(f"Backfill failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(backfill_vectors())
