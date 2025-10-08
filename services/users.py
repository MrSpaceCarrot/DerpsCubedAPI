# Module Imports
import logging
from sqlmodel import Session, select
from schemas.database import engine
from schemas.users import User
from services.economy import populate_user_currencies


logger = logging.getLogger("services")

# Services
# Get or create user
def get_or_create_user(discord_id: str) -> User:
    with Session(engine) as session:
        db_user = session.exec(select(User).where(User.discord_id == discord_id)).first()
        if not db_user:
            db_user = User(discord_id=discord_id)
            session.add(db_user)
            session.commit()
            session.refresh(db_user)
            populate_user_currencies(db_user)
        return db_user
