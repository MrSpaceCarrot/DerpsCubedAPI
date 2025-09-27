# Module Imports
from urllib.parse import quote_plus
from config import settings
from sqlmodel import SQLModel, create_engine, Session
from schemas.auth import ApiKey
from schemas.games import Game
from schemas.servers import Server, ServerCategory
from schemas.users import User

# Database setup
DATABASE_URL = f"mysql+mysqlconnector://{settings.DB_USERNAME}:{quote_plus(settings.DB_PASSWORD)}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_DATABASE}"
engine = create_engine(DATABASE_URL)

def setup_database():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
