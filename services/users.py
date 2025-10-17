# Module Imports
import logging
import requests
from sqlmodel import Session, select
from config import settings
from schemas.database import engine
from schemas.users import User, Permission, UserPermission
from services.economy import populate_user_currencies


logger = logging.getLogger("services")

# Services
# Get or create user
def get_or_create_user(discord_id: str) -> User:
    with Session(engine) as session:
        db_user = session.exec(select(User).where(User.discord_id == discord_id)).first()
        if not db_user:
            db_user = User(discord_id=discord_id)
            
            # Get discord username, return none if an invalid id was provided
            response = requests.get(f"https://discord.com/api/v10/users/{discord_id}", headers={"Authorization": f"Bot {settings.DISCORD_BOT_TOKEN}"})
            if response.ok:
                db_user.username = response.json()["username"]
                db_user.display_name = response.json()["global_name"]
            else:
                return None

            session.add(db_user)
            session.commit()
            session.refresh(db_user)
            populate_user_currencies(db_user)
            set_default_user_permissions(db_user)
        return db_user

# Set default permissions for a user
def set_default_user_permissions(user: User) -> None:
    with Session(engine) as session:
        db_permissions = session.exec(select(Permission)).all()
        for permission in db_permissions:
            if permission.assigned_by_default == True:
                session.add(UserPermission(user_id=user.id, permission_id=permission.id))
        session.commit()

# Set default user permisions for all existing users
def set_all_default_user_permissions() -> None:
    with Session(engine) as session:
        db_users = session.exec(select(User)).all()
        for user in db_users:
            set_default_user_permissions(user)
