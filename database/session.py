import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from database.models import Base
from config import DATABASE_URL

engine = create_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)

class DbSessionMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        with SessionLocal() as session:
            data["session"] = session
            return await handler(event, data)


def create_db() -> None:
    Base.metadata.create_all(engine)
