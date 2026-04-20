import logging
import asyncio
import ssl
from azure.cosmos.aio import CosmosClient
from azure.cosmos import PartitionKey
from core.config import settings

# Global variables for async clients and containers
_cosmos_client = None
_container = None
_history_container = None
_init_error = None

async def init_cosmos():
    """
    Initializes Async Cosmos DB client and containers.
    Called once during application startup.
    """
    global _cosmos_client, _container, _history_container, _init_error

    # Check if already initialized
    if _container is not None and _history_container is not None:
        return

    if not settings.COSMOS_ENDPOINT or not settings.COSMOS_KEY:
        _init_error = f"MISSING CREDENTIALS in settings. BASE_DIR used: {settings.model_config.get('env_file')}"
        logging.error(_init_error)
        return

    try:
        logging.info(f"Connecting to Cosmos DB at {settings.COSMOS_ENDPOINT}...")
        logging.info(f"Using Database: {settings.COSMOS_DATABASE}")
        logging.info(f"Target Product Container: '{settings.COSMOS_CONTAINER}'")
        logging.info(f"Target History Container: '{settings.COSMOS_HISTORY_CONTAINER}'")
        
        _cosmos_client = CosmosClient(
            settings.COSMOS_ENDPOINT, 
            credential=settings.COSMOS_KEY,
            connection_verify=False
        )
        
        # Test connection by listing databases or getting database
        database = await _cosmos_client.create_database_if_not_exists(id=settings.COSMOS_DATABASE)
        logging.info(f"Database ready: {settings.COSMOS_DATABASE}")

        # Attempt to get or create containers
        try:
            _container = await database.create_container_if_not_exists(
                id=settings.COSMOS_CONTAINER,
                partition_key=PartitionKey(path="/category")
            )
            logging.info(f"Container ready: {settings.COSMOS_CONTAINER}")
        except Exception as container_err:
            _init_error = f"Error initializing product container '{settings.COSMOS_CONTAINER}': {str(container_err)}"
            logging.error(_init_error)
            raise Exception(_init_error)

        try:
            _history_container = await database.create_container_if_not_exists(
                id=settings.COSMOS_HISTORY_CONTAINER,
                partition_key=PartitionKey(path="/userId")
            )
            logging.info(f"Container ready: {settings.COSMOS_HISTORY_CONTAINER}")
        except Exception as history_err:
            _init_error = f"Error initializing history container '{settings.COSMOS_HISTORY_CONTAINER}': {str(history_err)}"
            logging.error(_init_error)
            raise Exception(_init_error)

        _init_error = None
        logging.info(f"Async Cosmos DB initialization complete.")
        
    except Exception as e:
        _init_error = f"Initialization Exception: {str(e)}"
        logging.error(_init_error)
        # Reset to None on failure
        if _cosmos_client:
            await _cosmos_client.close()
        _cosmos_client = None
        _container = None
        _history_container = None

async def close_cosmos():
    """Closes the async Cosmos client."""
    global _cosmos_client, _container, _history_container
    if _cosmos_client:
        await _cosmos_client.close()
        logging.info("Async Cosmos DB client closed.")
    _cosmos_client = None
    _container = None
    _history_container = None

def get_product_container():
    """Returns the initialized async product container."""
    return _container

def get_history_container():
    """Returns the initialized async search history container."""
    return _history_container
