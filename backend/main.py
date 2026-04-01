from fastapi import FastAPI
from database.cosmos import init_cosmos
from services.storage import init_storage
from routers import upload, search, products

app = FastAPI(
    title="AI Product Image Search",
    description="Upload product images and search similar products using Azure AI Vision",
    version="1.0.0"
)

# Initialize Azure clients on startup
@app.on_event("startup")
async def startup_event():
    init_cosmos()
    init_storage()

# Register routers
app.include_router(upload.router)
app.include_router(search.router)
app.include_router(products.router)

@app.get("/")
async def root():
    return {"message": "AI Product Search API is running"}