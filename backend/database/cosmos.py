import logging
from azure.cosmos import CosmosClient, PartitionKey
from core.config import settings

# Global variables for containers
_container = None
_history_container = None

def init_cosmos():
    """
    Initializes Cosmos DB client and containers.
    Called once during application startup.
    """
    global _container, _history_container

    if not settings.COSMOS_ENDPOINT or not settings.COSMOS_KEY:
        logging.warning("Cosmos DB credentials not found. Database operations will fail.")
        return

    try:
        cosmos_client = CosmosClient(settings.COSMOS_ENDPOINT, settings.COSMOS_KEY)
        database = cosmos_client.create_database_if_not_exists(id=settings.COSMOS_DATABASE)

        _container = database.create_container_if_not_exists(
            id=settings.COSMOS_CONTAINER,
            partition_key=PartitionKey(path="/category")
        )
        _history_container = database.create_container_if_not_exists(
            id=settings.COSMOS_HISTORY_CONTAINER,
            partition_key=PartitionKey(path="/userId")
        )
        logging.info(f"Cosmos DB initialized: {settings.COSMOS_DATABASE}")
    except Exception as e:
        logging.error(f"Failed to initialize Cosmos DB: {str(e)}")

def get_product_container():
    """Returns the initialized product container."""
    if _container is None:
        logging.error("Product container accessed before initialization.")
    return _container

def get_history_container():
    """Returns the initialized search history container."""
    if _history_container is None:
        logging.error("History container accessed before initialization.")
    return _history_container
