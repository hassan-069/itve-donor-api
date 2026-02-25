from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
import logging

# Setup basic logging to track database connection status in the terminal
logger = logging.getLogger(__name__)

class Database:
    client: AsyncIOMotorClient = None
    db = None

# Global database instance
db_instance = Database()

async def connect_to_mongo():
    """
    Creates an asynchronous connection pool to MongoDB.
    This function will be called when the FastAPI server starts.
    """
    try:
        logger.info("Connecting to MongoDB...")
        # Initialize the Motor client using the URL from .env
        db_instance.client = AsyncIOMotorClient(settings.MONGO_URL)
        # Select the specific database
        db_instance.db = db_instance.client[settings.DB_NAME]
        logger.info("Successfully connected to MongoDB.")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise e

async def close_mongo_connection():
    """
    Closes the MongoDB connection gracefully.
    This function will be called when the FastAPI server shuts down.
    """
    if db_instance.client:
        logger.info("Closing MongoDB connection...")
        db_instance.client.close()
        logger.info("MongoDB connection closed.")

def get_database():
    """
    Dependency injection function to provide the database instance to API routes.
    """
    return db_instance.db