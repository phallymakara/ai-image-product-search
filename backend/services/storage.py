import logging
from azure.storage.blob import BlobServiceClient
from core.config import settings

_blob_service_client = None

def init_storage():
    """Initializes Azure Blob Storage client."""
    global _blob_service_client
    try:
        if settings.AZURE_STORAGE_CONNECTION:
            _blob_service_client = BlobServiceClient.from_connection_string(settings.AZURE_STORAGE_CONNECTION)
            logging.info("Blob Storage initialized successfully")
        else:
            logging.warning("AZURE_STORAGE_CONNECTION not found. Storage operations will fail.")
    except Exception as e:
        logging.error(f"Failed to initialize Blob Storage: {str(e)}")

def upload_to_blob(file_bytes: bytes, image_id: str, user_id: str, blob_service_client = None) -> str:
    """Uploads an image to Azure Blob Storage and returns the URL."""
    client = blob_service_client or _blob_service_client
    if not client:
        raise Exception("Blob storage client not initialized")

    try:
        blob_path = f"raw/{user_id}/{image_id}.jpg"
        blob_client = client.get_blob_client(
            container=settings.CONTAINER_NAME, blob=blob_path
        )
        blob_client.upload_blob(
            file_bytes, overwrite=True,
            metadata={"userId": user_id, "imageId": image_id}
        )
        return blob_client.url
    except Exception as e:
        logging.error(f"Failed to upload to blob: {str(e)}")
        raise Exception(f"Failed to upload to blob: {str(e)}")

def upload_search_image(file_bytes: bytes, search_id: str, user_id: str, blob_service_client = None) -> str | None:
    """Uploads a search image for history preview and returns the URL."""
    client = blob_service_client or _blob_service_client
    if not client:
        return None
    try:
        blob_path = f"searches/{user_id}/{search_id}.jpg"
        blob_client = client.get_blob_client(
            container=settings.CONTAINER_NAME, blob=blob_path
        )
        blob_client.upload_blob(file_bytes, overwrite=True)
        return blob_client.url
    except Exception as e:
        logging.error(f"Failed to upload search image: {str(e)}")
        return None

def get_blob_client():
    return _blob_service_client
