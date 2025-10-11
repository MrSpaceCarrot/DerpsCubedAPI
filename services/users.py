# Module Imports
import logging
from sqlmodel import Session, select
from schemas.database import engine
from schemas.users import User, UserPermission
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
            set_default_user_permissions(db_user)
        return db_user

# Set default permissions for a user
def set_default_user_permissions(user: User) -> None:
    with Session(engine) as session:
        # can_use_economy
        session.add(UserPermission(user_id=user.id, permission_id=1))

        # can_view_games
        session.add(UserPermission(user_id=user.id, permission_id=2))

        # can_add_games
        session.add(UserPermission(user_id=user.id, permission_id=3))

        # can_add_ratings
        session.add(UserPermission(user_id=user.id, permission_id=4))

        # can_view_servers
        session.add(UserPermission(user_id=user.id, permission_id=5))

        # can_view_users
        session.add(UserPermission(user_id=user.id, permission_id=6))
        session.commit()

# Set default user permisions for all existing users
def set_all_default_user_permissions() -> None:
    with Session(engine) as session:
        db_users = session.exec(select(User)).all()
        for user in db_users:
            set_default_user_permissions(user)
