# Module Imports
import logging
from datetime import datetime
from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlmodel import Session, select
from database.models import engine, User
from config import settings
from auth.utilities import *


router = APIRouter()
logger = logging.getLogger("services")

# Redirect to discord login screen
@router.get("/login/discord", tags=["auth"])
def login_discord() -> RedirectResponse:
    return RedirectResponse(url=settings.DISCORD_AUTHORIZE_URL)

# Authenticate user once they login with discord
@router.get("/discord/callback", tags=["auth"])
def discord_callback(code: str | None = None):
    # Ensure access code is present
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Access code is missing"
        )
    
    # Get discord access token
    access_token = get_discord_access_token(code)

    # Get discord user information
    user_info = get_discord_user_info(access_token)

    # Get user from database
    with Session(engine) as session:
        user: User = session.exec(select(User).where(User.discord_id == user_info["id"])).first()

        # Create user if they do not already exist
        if not user:
            user = User(discord_id=user_info["id"])
            user.display_name = user_info["username"]
            user.can_use_site = False
            user.can_add_games = False

        # If user exists but is only logging onto site for first time, set first login
        if user.first_site_login == None:
            user.first_site_login = datetime.now()

            # Check if user is in whitelisted discord servers
            # TO DO

        # Update some fields every time a user logs in
        user.username = user_info["username"]
        user.avatar_link = f"https://cdn.discordapp.com/avatars/{user_info['id']}/{user_info['avatar']}?size=1024"
        user.last_site_login = datetime.now()

        # Save user to database
        session.add(user)
        session.commit()

        # Issue token
        # TO DO

        # Return token
        # TO DO
        