from fastapi import FastAPI, UploadFile, File
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv
import uuid
import os

# Load environment variables
load_dotenv()

app = FastAPI()

CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION")
CONTAINER_NAME = os.getenv("CONTAINER_NAME")

blob_service_client = BlobServiceClient.from_connection_string(CONNECTION_STRING)


def upload_to_blob(file_bytes, image_id, user_id):
    """
    Uploads an image as raw bytes to Azure Blob Storage with metadata.

    Args:
        file_bytes (bytes): The raw data of the image file.
        image_id (str): A unique identifier for the image.
        user_id (str): The identifier for the user who uploaded the image.

    Returns:
        str: The URL of the uploaded blob.
    """
    blob_path = f"raw/{user_id}/{image_id}.jpg"

    blob_client = blob_service_client.get_blob_client(
        container=CONTAINER_NAME,
        blob=blob_path
    )

    blob_client.upload_blob(file_bytes, overwrite=True,  metadata={
        "userId": user_id,
        "imageId": image_id
    })

    return blob_client.url


@app.post("/upload")
async def upload_image(user_id: str, file: UploadFile = File(...)):
    """
    API endpoint for uploading an image to storage.

    Args:
        user_id (str): The ID of the user uploading the file.
        file (UploadFile): The uploaded file provided in the request body.

    Returns:
        dict: A dictionary containing the user ID, image ID, image URL, and status.
    """
    image_id = str(uuid.uuid4())

    file_bytes = await file.read()

    url = upload_to_blob(file_bytes, image_id, user_id)

    return {
        "userId": user_id,
        "imageId": image_id,
        "imageUrl": url,
        "status": "uploaded to blob"
    }
