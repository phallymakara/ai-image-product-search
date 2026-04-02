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
    Enhanced with fuzzy tag matching and weighted overlap.
    """
    prod_tags = [t["name"].lower() for t in product.get("tags", [])]
    search_tags_lower = [t.lower() for t in search_tags]
    
    # 1. TAG SCORE: Weighted overlap + Fuzzy check
    tag_score = 0
    if search_tags_lower:
        # Direct matches
        common_tags = set(search_tags_lower) & set(prod_tags)
        direct_match_ratio = len(common_tags) / len(search_tags_lower)
        
        # Fuzzy matches for missed tags
        missed_search = set(search_tags_lower) - common_tags
        fuzzy_extra = 0
        for s_tag in missed_search:
            best_fuzzy = max([fuzz.ratio(s_tag, p_tag) for p_tag in prod_tags]) / 100.0 if prod_tags else 0
            if best_fuzzy > 0.8:
                fuzzy_extra += best_fuzzy
        
        tag_score = min(1.0, direct_match_ratio + (fuzzy_extra / len(search_tags_lower)))

    # 2. BRAND SCORE: Exact or partial match
    prod_brands = [b.lower() for b in product.get("brands", [])]
    search_brands_lower = [b.lower() for b in search_brands]
    brand_match = 0.0
    if search_brands_lower:
        if set(search_brands_lower) & set(prod_brands):
            brand_match = 1.0
        else:
            # Check if search brand is contained in product name
            prod_name = product.get("name", "").lower()
            if any(b in prod_name for b in search_brands_lower):
                brand_match = 0.8

    # 3. OCR SCORE: Fuzzy name/ocr check
    prod_ocr = product.get("ocr_text", "").lower()
    prod_name = product.get("name", "").lower()
    ocr_score = 0
    if ocr_text:
        ocr_score = max(
            fuzz.token_set_ratio(ocr_text.lower(), prod_ocr),
            fuzz.token_set_ratio(ocr_text.lower(), prod_name)
        ) / 100.0

    # 4. WEIGHTED TOTAL
    # If no OCR or brands detected, put more weight on tags
    weights = {"tag": 0.4, "brand": 0.3, "ocr": 0.3}
    if not search_brands:
        weights["tag"] += 0.15
        weights["ocr"] += 0.15
        weights["brand"] = 0
    if not ocr_text:
        weights["tag"] += 0.15
        weights["brand"] += 0.15
        weights["ocr"] = 0

    final_score = (
        (weights["tag"] * tag_score) + 
        (weights["brand"] * brand_match) + 
        (weights["ocr"] * ocr_score)
    )
    
    return round(final_score, 3)


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
