import logging
import requests
from typing import Dict, Any, List
from core.config import VISION_ENDPOINT, VISION_KEY
 
 
def analyze_image(image_bytes: bytes) -> Dict[str, Any]:
    """Analyzes an image using Azure AI Vision API."""
    if not VISION_ENDPOINT or not VISION_KEY:
        logging.error("Missing VISION_ENDPOINT or VISION_KEY")
        return {}
 
    url = f"{VISION_ENDPOINT}/vision/v3.2/analyze?visualFeatures=Tags,Objects,Categories,Description,Brands"
    headers = {
        "Ocp-Apim-Subscription-Key": VISION_KEY,
        "Content-Type": "application/octet-stream"
    }
 
    try:
        response = requests.post(url, headers=headers, data=image_bytes)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logging.error(f"Error calling Vision API: {str(e)}")
        return {}
 
 
def ocr_image(image_bytes: bytes) -> str:
    """Extracts text from an image using Azure Vision OCR API."""
    if not VISION_ENDPOINT or not VISION_KEY:
        return ""
 
    url = f"{VISION_ENDPOINT}/vision/v3.2/ocr?language=unk&detectOrientation=true"
    headers = {
        "Ocp-Apim-Subscription-Key": VISION_KEY,
        "Content-Type": "application/octet-stream"
    }
 
    try:
        response = requests.post(url, headers=headers, data=image_bytes)
        response.raise_for_status()
        data = response.json()
 
        text_parts = []
        for region in data.get("regions", []):
            for line in region.get("lines", []):
                for word in line.get("words", []):
                    text_parts.append(word.get("text", ""))
 
        return " ".join(text_parts)
    except Exception as e:
        logging.error(f"Error calling OCR API: {str(e)}")
        return ""
 
 
def extract_tags(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extracts tags from Azure AI Vision result."""
    tags = result.get("tags", [])
    return [
        {"name": tag["name"], "confidence": round(tag["confidence"], 3)}
        for tag in tags if tag["confidence"] > 0.5
    ]
 
 
def extract_brands(result: Dict[str, Any]) -> List[str]:
    """Extracts brand names from the analysis result."""
    brands = result.get("brands", [])
    return [brand["name"] for brand in brands]
 
 
def detect_category(result: Dict[str, Any], tags: List[Dict]) -> str:
    """Detects the best category from vision result."""
    categories = result.get("categories", [])
    if categories:
        raw_cat = categories[0].get("name", "")
        return raw_cat.split("_")[0] if "_" in raw_cat else raw_cat
    elif tags:
        return tags[0]["name"]
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