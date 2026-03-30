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
    image_id = str(uuid.uuid4())

    file_bytes = await file.read()

    url = upload_to_blob(file_bytes, image_id, user_id)

    return {
        "userId": user_id,
        "imageId": image_id,
        "imageUrl": url,
        "status": "uploaded to blob"
    }