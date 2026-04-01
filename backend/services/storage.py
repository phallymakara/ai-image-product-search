import logging
from azure.storage.blob import BlobServiceClient
from core.config import STORAGE_CONNECTION_STRING, STORAGE_CONTAINER_NAME

blob_service_client = None


def init_storage():
    global blob_service_client
    try:
        if STORAGE_CONNECTION_STRING:
            blob_service_client = BlobServiceClient.from_connection_string(STORAGE_CONNECTION_STRING)
            logging.info("Blob Storage initialized successfully")
    except Exception as e:
        logging.error(f"Failed to initialize Blob Storage: {str(e)}")


def upload_to_blob(file_bytes: bytes, image_id: str, user_id: str) -> str:
    """Uploads an image to Azure Blob Storage and returns the URL."""
    if not blob_service_client:
        raise Exception("Blob storage client not initialized")

    blob_path = f"raw/{user_id}/{image_id}.jpg"
    blob_client = blob_service_client.get_blob_client(
        container=STORAGE_CONTAINER_NAME, blob=blob_path
    )
    blob_client.upload_blob(
        file_bytes, overwrite=True,
        metadata={"userId": user_id, "imageId": image_id}
    )
    return blob_client.url


def upload_search_image(file_bytes: bytes, search_id: str, user_id: str) -> str | None:
    """Uploads a search image for history preview and returns the URL."""
    if not blob_service_client:
        return None
    try:
        blob_path = f"searches/{user_id}/{search_id}.jpg"
        blob_client = blob_service_client.get_blob_client(
            container=STORAGE_CONTAINER_NAME, blob=blob_path
        )
        blob_client.upload_blob(file_bytes, overwrite=True)
        return blob_client.url
    except Exception as e:
        logging.error(f"Failed to upload search image: {str(e)}")
        return None


def get_blob_client():
    return blob_service_client