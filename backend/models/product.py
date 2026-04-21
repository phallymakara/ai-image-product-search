from pydantic import BaseModel, Field
from typing import Optional, List


class TagSchema(BaseModel):
    name: str
    confidence: float


class ProductBase(BaseModel):
    name: str
    category: str
    tags: List[TagSchema] = []
    brands: List[str] = []
    ocr_text: Optional[str] = None
    imageUrl: Optional[str] = None
    userId: str
    vector: Optional[List[float]] = None


class ProductCreate(ProductBase):
    image_hash: Optional[str] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[TagSchema]] = None
    brands: Optional[List[str]] = None
    ocr_text: Optional[str] = None
    imageUrl: Optional[str] = None
    userId: Optional[str] = None


class ProductResponse(ProductBase):
    id: str
    productId: str
    image_hash: Optional[str] = None
