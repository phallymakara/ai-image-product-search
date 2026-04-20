import os
# Fix for OpenMP duplicate library error on macOS (Torch + FAISS conflict)
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

from contextlib import asynccontextmanager
from fastapi import FastAPI
from database.cosmos import init_cosmos, close_cosmos
from services.storage import init_storage
from routers import upload, search, products

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize Azure clients on startup
    await init_cosmos()
    init_storage()
    
    # Check for initialization errors
    from database.cosmos import _init_error
    if _init_error:
        print(f"\n[CRITICAL] Cosmos DB Initialization Failed: {_init_error}\n")
    else:
        print("\n[SUCCESS] Cosmos DB connected and containers ready.\n")
        
    yield
    # Close clients on shutdown
    await close_cosmos()

app = FastAPI(
    title="AI Product Image Search",
    description="Upload product images and search similar products using Azure AI Vision",
    version="1.0.0",
    lifespan=lifespan
)

# Register routers
app.include_router(upload.router)
app.include_router(search.router)
app.include_router(products.router)

@app.get("/debug/status")
async def debug_status():
    from database.cosmos import _container, _history_container, _init_error
    from services.vector_service import vector_service
    from core.config import settings
    return {
        "cosmos": {
            "endpoint_set": bool(settings.COSMOS_ENDPOINT),
            "key_set": bool(settings.COSMOS_KEY),
            "product_container_initialized": _container is not None,
            "history_container_initialized": _history_container is not None,
            "init_error": _init_error
        },
        "vector_service": {
            "is_ready": vector_service.is_ready,
            "device": vector_service.device,
            "model_name": settings.CLIP_MODEL_NAME
        },
        "storage": {
            "connection_set": bool(settings.AZURE_STORAGE_CONNECTION)
        },
        "vision": {
            "endpoint_set": bool(settings.VISION_ENDPOINT),
            "key_set": bool(settings.VISION_KEY)
        }
    }

@app.get("/")
async def root():
    return {"message": "AI Product Search API is running"}
