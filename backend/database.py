import os
from datetime import datetime
from typing import Annotated

from fastapi import Depends
from sqlmodel import Field, Session, SQLModel, create_engine

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///booking_db.db")

engine = create_engine(DATABASE_URL)


def init_db():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


DbSession = Annotated[Session, Depends(get_session)]


class Booking(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_name: str
    start_time: datetime = Field(unique=True)
    created_at: datetime = Field(default_factory=datetime.now)
