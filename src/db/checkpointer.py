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

    _checkpointer_context = AsyncPostgresSaver.from_conn_string(conn_string)
    _checkpointer = await _checkpointer_context.__aenter__()
    await _checkpointer.setup()
    logger.info("checkpointer initialized and tables created")
    return _checkpointer


async def close_checkpointer():
    """clean up checkpointer connection (call at shutdown)"""
    global _checkpointer, _checkpointer_context
    if _checkpointer_context:
        await _checkpointer_context.__aexit__(None, None, None)
        _checkpointer = None
        _checkpointer_context = None
        logger.info("checkpointer closed")


def get_checkpointer() -> AsyncPostgresSaver | None:
    """get the checkpointer instance (must call init_checkpointer first)"""
    return _checkpointer
