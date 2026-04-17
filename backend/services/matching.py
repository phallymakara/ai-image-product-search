from thefuzz import fuzz
import re
from typing import List, Dict, Any

try:
    from khmernltk import word_tokenize
    KHMER_AVAILABLE = True
except ImportError:
    KHMER_AVAILABLE = False

def contains_khmer(text: str) -> bool:
    """Checks if a string contains Khmer characters (Unicode range U+1780 to U+17FF)."""
    return bool(re.search(r'[\u1780-\u17FF]', text))

def smart_tokenize(text: str) -> List[str]:
    """Tokenizes text based on language detection."""
    if not text:
        return []
    
    # If Khmer is detected and library is available, use special tokenizer
    if contains_khmer(text) and KHMER_AVAILABLE:
        try:
            return word_tokenize(text)
        except Exception:
            # Fallback to character-based or space-based if khmer-nltk fails
            return text.split()
    
    # Default to space-based tokenization for English/others
    return text.split()

def get_token_score(query: str, target: str, scorer=fuzz.token_set_ratio) -> float:
    """
    Enhanced token-based scoring that handles Khmer by pre-segmenting tokens.
    """
    if not query or not target:
        return 0.0
    
    # If Khmer is involved, we join segmented tokens with spaces so fuzz.token_set_ratio 
    # can work correctly (it normally splits by space).
    if contains_khmer(query) or contains_khmer(target):
        q_tokens = " ".join(smart_tokenize(query))
        t_tokens = " ".join(smart_tokenize(target))
        return scorer(q_tokens, t_tokens) / 100.0
    
    return scorer(query, target) / 100.0

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
            # Use improved ratio for Khmer if needed
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
            get_token_score(ocr_text.lower(), prod_ocr),
            get_token_score(ocr_text.lower(), prod_name)
        )

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

    name_score = get_token_score(query_lower, product.get("name", "").lower())

    prod_tags = [t["name"].lower() for t in product.get("tags", [])]
    tag_score = max([get_token_score(query_lower, t) for t in prod_tags]) if prod_tags else 0

    prod_brands = [b.lower() for b in product.get("brands", [])]
    brand_score = max([get_token_score(query_lower, b) for b in prod_brands]) if prod_brands else 0

    ocr_text = product.get("ocr_text", "").lower()
    ocr_score = get_token_score(query_lower, ocr_text, scorer=fuzz.partial_ratio) if ocr_text else 0

    return round((0.5 * name_score) + (0.2 * tag_score) + (0.1 * brand_score) + (0.2 * ocr_score), 3)

