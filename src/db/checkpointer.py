from contextlib import asynccontextmanager

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from src.config import settings
from src.utils.logger import logger

_checkpointer: AsyncPostgresSaver | None = None
_checkpointer_context = None


async def init_checkpointer() -> AsyncPostgresSaver | None:
    """initialize the checkpointer (call once at startup)"""
    global _checkpointer, _checkpointer_context

    conn_string = settings.database_url

    if not conn_string:
        logger.warning("DATABASE_URL not configured, checkpointer disabled")
        return None

    try:
        _checkpointer_context = AsyncPostgresSaver.from_conn_string(conn_string)
        _checkpointer = await _checkpointer_context.__aenter__()
        await _checkpointer.setup()
        logger.info("checkpointer initialized and tables created")
        return _checkpointer
    except Exception as e:
        logger.error(f"failed to initialize checkpointer: {e}")
        _checkpointer = None
        _checkpointer_context = None
        raise


async def close_checkpointer():
    """clean up checkpointer connection (call at shutdown)"""
    global _checkpointer, _checkpointer_context
    if _checkpointer_context:
        try:
            await _checkpointer_context.__aexit__(None, None, None)
            logger.info("checkpointer closed")
        except Exception as e:
            logger.error(f"error closing checkpointer: {e}")
        finally:
            _checkpointer = None
            _checkpointer_context = None


def get_checkpointer() -> AsyncPostgresSaver | None:
    """get the checkpointer instance (must call init_checkpointer first)"""
    if _checkpointer is None:
        logger.warning("checkpointer not initialized, returning None")
    return _checkpointer


@asynccontextmanager
async def get_fresh_checkpointer():
    """create a fresh checkpointer connection for a single request"""
    conn_string = settings.database_url
    if not conn_string:
        yield None
        return

    async with AsyncPostgresSaver.from_conn_string(conn_string) as checkpointer:
        yield checkpointer
