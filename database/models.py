# Module Imports
from typing import Annotated
from urllib.parse import quote_plus
from fastapi import Depends
from sqlmodel import Field, Session, SQLModel, create_engine
from core.config import settings

# Database connection
DATABASE_URL = f"mysql+mysqlconnector://{settings.DB_USERNAME}:{quote_plus(settings.DB_PASSWORD)}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_DATABASE}"
engine = create_engine(DATABASE_URL)

def setup_database():
    SQLModel.metadata.create_all(engine)

# Get session
def get_session():
    with Session(engine) as session:
        yield session

SessionDep = Annotated[Session, Depends(get_session)]

# Models
class Server(SQLModel, table=True):
    __tablename__ = "servers"
    id: int = Field(primary_key=True, index=True)
    name: str | None = Field(index=True, default=None, max_length=25)
    description: str | None = Field(index=True, default=None, max_length=150)
    category: str | None = Field(index=True, default=None, max_length=25)
