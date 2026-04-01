from pydantic import BaseModel
from typing import Optional


class TopMatchPreview(BaseModel):
    productId: Optional[str]
    name: Optional[str]
    imageUrl: Optional[str]
    match_score: Optional[float]


class SearchHistoryItem(BaseModel):
    searchId: str
    timestamp: str
    searchType: Optional[str] = "image"
    queryText: Optional[str] = None
    searchImageUrl: Optional[str] = None
    category: Optional[str] = None
    topMatch: Optional[TopMatchPreview] = None
    resultCount: Optional[int] = 0