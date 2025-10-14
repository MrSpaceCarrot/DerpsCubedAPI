# Module Imports
import logging
from urllib.parse import quote_plus
from config import settings
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy import func
from schemas.auth import ApiKey, RefreshToken
from schemas.economy import Currency, UserCurrency, Job, UserJob, Cooldown, BlackjackGame
from schemas.games import Game, GameTag, GameRating
from schemas.servers import Server, ServerCategory
from schemas.users import User, Permission, UserPermission


logger = logging.getLogger("services")

# Database setup
DATABASE_URL = f"mysql+mysqlconnector://{settings.DB_USERNAME}:{quote_plus(settings.DB_PASSWORD)}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_DATABASE}"
engine = create_engine(DATABASE_URL)

def setup_database():
    SQLModel.metadata.create_all(engine)

# Get session
def get_session():
    with Session(engine) as session:
        yield session
