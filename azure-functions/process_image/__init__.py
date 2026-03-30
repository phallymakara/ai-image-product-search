import logging
import azure.functions as func

def main(myblob: func.InputStream):
    logging.info(f"Blob detected: {myblob.name}")

    image_bytes = myblob.read()

    logging.info(f"Image size: {len(image_bytes)} bytes")