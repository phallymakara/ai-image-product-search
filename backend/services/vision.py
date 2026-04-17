import logging
import requests
import time
from typing import Dict, Any, List
from core.config import settings

def analyze_image(image_bytes: bytes) -> Dict[str, Any]:
    """Analyzes an image using Azure AI Vision API."""
    if not settings.VISION_ENDPOINT or not settings.VISION_KEY:
        logging.error("Missing VISION_ENDPOINT or VISION_KEY")
        return {}

    url = f"{settings.VISION_ENDPOINT}/vision/v3.2/analyze?visualFeatures=Tags,Objects,Categories,Description,Brands"
    headers = {
        "Ocp-Apim-Subscription-Key": settings.VISION_KEY,
        "Content-Type": "application/octet-stream"
    }

    try:
        response = requests.post(url, headers=headers, data=image_bytes, timeout=10)
        response.raise_for_status()
        result = response.json()
        logging.info(f"Vision API categories: {result.get('categories', [])}")
        logging.info(f"Vision API tags: {result.get('tags', [])}")
        return result
    except requests.exceptions.RequestException as e:
        logging.error(f"Error calling Vision API: {str(e)}")
        return {}

def ocr_image(image_bytes: bytes) -> str:
    """
    Extracts text from an image using Azure Vision READ API (v3.2).
    The Read API supports 164 languages including Khmer (km).
    """
    if not settings.VISION_ENDPOINT or not settings.VISION_KEY:
        return ""

    # Step 1: Submit for analysis
    read_url = f"{settings.VISION_ENDPOINT}/vision/v3.2/read/analyze"
    headers = {
        "Ocp-Apim-Subscription-Key": settings.VISION_KEY,
        "Content-Type": "application/octet-stream"
    }

    try:
        response = requests.post(read_url, headers=headers, data=image_bytes, timeout=10)
        response.raise_for_status()
        
        operation_url = response.headers.get("Operation-Location")
        if not operation_url:
            return ""

        # Step 2: Poll for results
        for _ in range(10):
            result_res = requests.get(operation_url, headers={"Ocp-Apim-Subscription-Key": settings.VISION_KEY})
            result_data = result_res.json()

            if result_data.get("status") == "succeeded":
                text_parts = []
                for res in result_data.get("analyzeResult", {}).get("readResults", []):
                    for line in res.get("lines", []):
                        text_parts.append(line.get("text", ""))
                return " ".join(text_parts)
            
            if result_data.get("status") == "failed":
                return ""
            time.sleep(1)

    except Exception as e:
        logging.error(f"Error calling Read API: {str(e)}")
    
    return ""

def extract_tags(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extracts tags from Azure AI Vision result."""
    tags = result.get("tags", [])
    return [
        {"name": tag["name"], "confidence": round(tag["confidence"], 3)}
        for tag in tags if tag.get("confidence", 0) > 0.1
    ]

def extract_brands(result: Dict[str, Any]) -> List[str]:
    """Extracts brand names from the analysis result."""
    brands = result.get("brands", [])
    return [brand["name"] for brand in brands if "name" in brand]

def detect_category(result: Dict[str, Any], tags: List[Dict]) -> str:
    """Detects the best category from vision result."""
    categories = result.get("categories", [])
    if categories:
        raw_cat = categories[0].get("name", "")
        if raw_cat:
            return raw_cat.split("_")[0] if "_" in raw_cat else raw_cat
    if tags:
        return tags[0]["name"]
    
    all_tags = result.get("tags", [])
    if all_tags:
        return all_tags[0].get("name", "uncategorized")
    return "uncategorized"

def detect_name(result: Dict[str, Any], brands: List[str], tags: List[Dict]) -> str:
    """Detects the best product name from vision result."""
    description = result.get("description", {}).get("captions", [])
    if description:
        return description[0].get("text", "").capitalize()
    elif brands:
        return f"{brands[0]} Product"
    elif result.get("objects"):
        return result["objects"][0].get("object", "").capitalize()
    elif tags:
        return tags[0]["name"].capitalize()
    return "Unknown Product"
