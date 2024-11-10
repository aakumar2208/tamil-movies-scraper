from supabase import create_client, Client
from app.core.config import settings
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class Database:
    _instance: Optional[Client] = None

    @classmethod
    def get_client(cls) -> Client:
        """
        Returns a singleton instance of the Supabase client.
        """
        if cls._instance is None:
            try:
                cls._instance = create_client(
                    supabase_url=settings.SUPABASE_URL,
                    supabase_key=settings.SUPABASE_KEY
                )
                logger.info("Successfully connected to Supabase")
            except Exception as e:
                logger.error(f"Failed to connect to Supabase: {str(e)}")
                raise
        return cls._instance

# Create a global instance of the database client
supabase = Database.get_client()

def get_db() -> Client:
    """
    Returns the Supabase client instance.
    This function is useful for dependency injection in FastAPI.
    """
    return supabase