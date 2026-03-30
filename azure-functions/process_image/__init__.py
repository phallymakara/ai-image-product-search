import logging
import azure.functions as func
import requests
import os


# Call Azure AI Vision
def analyze_image(image_bytes):
    endpoint = os.getenv("VISION_ENDPOINT")
    key = os.getenv("VISION_KEY")

    if not endpoint or not key:
        raise ValueError("Missing VISION_ENDPOINT or VISION_KEY")

    url = f"{endpoint}/vision/v3.2/analyze?visualFeatures=Tags,Objects"

    headers = {
        "Ocp-Apim-Subscription-Key": key,
        "Content-Type": "application/octet-stream"
    }

    response = requests.post(url, headers=headers, data=image_bytes)

    if response.status_code != 200:
        logging.error(f"Vision API Error: {response.text}")
        return {}

    return response.json()


# Extract high-confidence tags WITH confidence
def extract_tags(result):
    tags = result.get("tags", [])

    filtered = [
        {
            "name": tag["name"],
            "confidence": round(tag["confidence"], 3)
        }
        for tag in tags
        if tag["confidence"] > 0.8
    ]

    return filtered


# Get main product (highest confidence)
def get_main_product(tags):
    if not tags:
        return None
    return tags[0]   # already sorted by AI


# Extract metadata from blob path
def extract_metadata(blob_name):
    # example: images-analysis/raw/U123/abc.jpg
    parts = blob_name.split("/")

    if len(parts) < 4:
        return None, None

    user_id = parts[2]
    image_name = parts[3]

    return user_id, image_name


# MAIN FUNCTION
def main(myblob: func.InputStream):
    logging.info(f"Blob detected: {myblob.name}")

    try:
        # Read image
        image_bytes = myblob.read()

        # Extract metadata
        user_id, image_id = extract_metadata(myblob.name)

        # Call AI Vision
        result = analyze_image(image_bytes)

        # Process result
        tags = extract_tags(result)
        main_product = get_main_product(tags)

        # Final structured output
        output = {
            "userId": user_id,
            "imageId": image_id,
            "main_product": main_product,
            "keywords": tags
        }

        # Log final result
        logging.info(f"FINAL OUTPUT: {output}")

    except Exception as e:
        logging.error(f"Error processing image: {str(e)}")