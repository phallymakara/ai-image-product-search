from pydantic import BaseModel
from typing import Optional, List


class TagSchema(BaseModel):
    name: str
    confidence: float


class ProductCreate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None


class ProductResponse(BaseModel):
    id: str
    productId: str
    name: str
    category: str
    tags: List[TagSchema] = []
    brands: List[str] = []
    ocr_text: Optional[str] = None
    imageUrl: Optional[str] = None
    userId: str
    image_hash: Optional[str] = None