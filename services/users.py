# Module Imports
import logging
import requests
import time
from io import BytesIO
from PIL import Image
from sqlmodel import Session, select
from config import settings
from schemas.database import engine
from schemas.users import User, Permission, UserPermission
from services.economy import populate_user_currencies
from services.games import populate_user_ratings
from services.storage import *


logger = logging.getLogger("services")

# Services
# General
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
            populate_user_ratings(db_user.id)
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

# Format a user's permissions as a list of strings
def format_user_permissions(user: User) -> None:
    with Session(engine) as session:
        return {permission.code for permission in user.permissions}

# Avatar Images
# Generate an avatar image from an avatar link
def generate_avatar_image(avatar_link: str) -> BytesIO | None:
    try:
        # Get image from link
        response: requests.Response = requests.get(avatar_link, timeout=5)
        img: Image = Image.open(BytesIO(response.content))

        # Return contentfile
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer
    except Exception:
        return None
    
# Update a user's avatar image
def update_avatar_image(user_id: int):
    with Session(engine) as session:
        db_user: User = session.get(User, user_id)

        if not db_user.avatar_link:
            logger.debug(f"Skipping updating avatar image for {db_user.username}")
            return

        avatar_image = generate_avatar_image(db_user.avatar_link)
        if avatar_image:
            file_name: str = f"avatar_images/{str(db_user.id).zfill(4)}.png"
            logger.debug(f"Updating avatar image for {db_user.username}")
            upload_file_to_bucket(avatar_image, file_name)

            db_user.avatar_image = file_name
            session.add(db_user)
            session.commit()

        else:
            logger.warning(f"Error updating avatar image for {db_user.username}")

# Update all user avatar images
def update_avatar_images() -> None:
    with Session(engine) as session:
        db_users = session.exec(select(User).order_by(User.id.asc())).all()
        for db_user in db_users:
            time.sleep(1)
            update_avatar_image(db_user.id)
        logger.info(f"Updated banner image for {len(db_users)} games")
