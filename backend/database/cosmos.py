import logging
from azure.cosmos import CosmosClient, PartitionKey
from core.config import (
    COSMOS_ENDPOINT, COSMOS_KEY,
    COSMOS_DATABASE_NAME, COSMOS_CONTAINER_NAME
)
 
# Cosmos DB clients
container = None
search_history_container = None
 
def init_cosmos():
    global container, search_history_container
 
    try:
        if COSMOS_ENDPOINT and COSMOS_KEY:
            cosmos_client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)
            database = cosmos_client.create_database_if_not_exists(id=COSMOS_DATABASE_NAME)
 
            container = database.create_container_if_not_exists(
                id=COSMOS_CONTAINER_NAME,
                partition_key=PartitionKey(path="/category")
            )
            search_history_container = database.create_container_if_not_exists(
                id="SearchHistory",
                partition_key=PartitionKey(path="/userId")
            )
            logging.info("Cosmos DB initialized successfully")
    except Exception as e:
        logging.error(f"Failed to initialize Cosmos DB: {str(e)}")
 
 
def get_product_container():
    return container
 
 
def get_history_container():
    return search_history_container