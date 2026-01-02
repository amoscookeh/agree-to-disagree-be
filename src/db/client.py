from supabase import Client, create_client

from src.config import settings
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class SupabaseClient:
    _instance: Client | None = None

    @classmethod
    def get_client(cls) -> Client:
        if cls._instance is None:
            cls._instance = create_client(settings.supabase_url, settings.supabase_key)
            logger.info("supabase client initialized")
        return cls._instance


def get_supabase() -> Client:
    return SupabaseClient.get_client()
