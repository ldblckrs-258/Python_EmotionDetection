from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from pymongo.collection import Collection
from app.core.config import settings
import logging

# Initialize MongoDB client
mongo_client = None
database = None

async def connect_to_mongodb():
    """
    Connect to MongoDB Atlas.
    """
    global mongo_client, database
    try:
        # Check if connection already exists
        if mongo_client is not None:
            return

        # Create MongoDB connection
        mongo_client = AsyncIOMotorClient(settings.MONGODB_URI)
        database = mongo_client[settings.MONGODB_NAME]
        logging.info("Connected to MongoDB Atlas")
    except Exception as e:
        logging.error(f"Failed to connect to MongoDB: {e}")
        raise

async def close_mongodb_connection():
    """
    Close MongoDB connection.
    """
    global mongo_client
    if mongo_client is not None:
        mongo_client.close()
        mongo_client = None
        logging.info("Closed MongoDB connection")

def get_collection(collection_name: str) -> AsyncIOMotorCollection:
    """
    Get a MongoDB collection as AsyncIOMotorCollection.
    """
    if database is None:
        raise ValueError("Database connection not established")
    return database[collection_name]

from motor.motor_asyncio import AsyncIOMotorDatabase

def get_database() -> AsyncIOMotorDatabase:
    """
    Get the MongoDB database.
    """
    if database is None:
        raise ValueError("Database connection not established")
    return database