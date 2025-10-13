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
        """
        By default the user should have the following permissions:
         - can_use_economy: 1
         - can_view_games: 2
         - can_add_games: 3
         - can_add_ratings: 4
         - can_view_servers: 5
         - can_view_users: 6
         - can_start_servers: 10
        """

        for permission_id in [1, 2, 3, 4, 5, 6, 10]:
            session.add(UserPermission(user_id=user.id, permission_id=permission_id))
        session.commit()

# Set default user permisions for all existing users
def set_all_default_user_permissions() -> None:
    with Session(engine) as session:
        db_users = session.exec(select(User)).all()
        for user in db_users:
            set_default_user_permissions(user)
