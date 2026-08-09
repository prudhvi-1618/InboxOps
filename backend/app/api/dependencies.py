from fastapi import Depends
import aiosqlite
from app.infrastructure.database.connection import get_db
from app.infrastructure.database.repository import EmailDecisionRepository


async def get_repository(db: aiosqlite.Connection = Depends(get_db)) -> EmailDecisionRepository:
    return EmailDecisionRepository(db)
