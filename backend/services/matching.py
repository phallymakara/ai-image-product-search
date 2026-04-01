from thefuzz import fuzz
from typing import List, Dict, Any


def score_product_by_image(
    product: Dict[str, Any],
    search_tags: List[str],
    search_brands: List[str],
    ocr_text: str
) -> float:
    """
    Scores a product against image search inputs.
    Score = 0.4*tags + 0.3*brands + 0.3*ocr
    """
    prod_tags = [t["name"] for t in product.get("tags", [])]
    common_tags = set(search_tags) & set(prod_tags)
    tag_score = len(common_tags) / len(set(search_tags) | set(prod_tags)) \
        if (set(search_tags) | set(prod_tags)) else 0

    prod_brands = [b.lower() for b in product.get("brands", [])]
    brand_match = 1.0 if (set(search_brands) & set(prod_brands)) else 0.0

    prod_ocr = product.get("ocr_text", "").lower()
    prod_name = product.get("name", "").lower()
    ocr_score = max(
        fuzz.partial_ratio(ocr_text, prod_ocr),
        fuzz.partial_ratio(ocr_text, prod_name)
    ) / 100.0 if ocr_text else 0

    return round((0.4 * tag_score) + (0.3 * brand_match) + (0.3 * ocr_score), 3)


def score_product_by_text(product: Dict[str, Any], query: str) -> float:
    """
    Scores a product against a text search query.
    Score = 0.5*name + 0.2*tags + 0.1*brands + 0.2*ocr
    """
    query_lower = query.lower()

    name_score = fuzz.token_set_ratio(query_lower, product.get("name", "").lower()) / 100.0

    prod_tags = [t["name"].lower() for t in product.get("tags", [])]
    tag_score = max([fuzz.token_set_ratio(query_lower, t) for t in prod_tags]) / 100.0 \
        if prod_tags else 0

    prod_brands = [b.lower() for b in product.get("brands", [])]
    brand_score = max([fuzz.token_set_ratio(query_lower, b) for b in prod_brands]) / 100.0 \
        if prod_brands else 0

    ocr_text = product.get("ocr_text", "").lower()
    ocr_score = fuzz.partial_ratio(query_lower, ocr_text) / 100.0 if ocr_text else 0

    return round((0.5 * name_score) + (0.2 * tag_score) + (0.1 * brand_score) + (0.2 * ocr_score), 3)