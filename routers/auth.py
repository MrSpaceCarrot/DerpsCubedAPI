# Module Imports
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import RedirectResponse
from sqlmodel import Session, select
from config import settings
from auth.security import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from auth.utilities import *
from schemas.database import get_session
from schemas.auth import Token
from schemas.users import User


router = APIRouter()
logger = logging.getLogger("services")

# Redirect to discord login screen
@router.get("/login/discord", tags=["auth"])
def login_discord() -> RedirectResponse:
    return RedirectResponse(url=settings.DISCORD_AUTHORIZE_URL)

# Authenticate user once they login with discord
@router.get("/discord/callback", tags=["auth"])
def discord_callback(code: str | None = None, session: Session = Depends(get_session)):
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
    user: User = session.exec(select(User).where(User.discord_id == user_info["id"])).first()

    # Create user if they do not already exist
    first_site_use = False
    if not user:
        user = User(discord_id=user_info["id"])
        first_site_use = True

    # Check if user exists but is doing first login
    if user.first_site_login == None:
        first_site_use = True

    # Setup user if using site for first time
    if first_site_use:
        user.first_site_login = datetime.now()
        user.display_name = user_info["username"]
        user.can_use_site = False
        user.can_add_games = False

        # Check if user is in whitelisted discord servers
        # TO DO

    # Update some fields every time a user logs in
    user.username = user_info["username"]
    user.avatar_link = f"https://cdn.discordapp.com/avatars/{user_info['id']}/{user_info['avatar']}?size=1024"
    user.last_site_login = datetime.now()

    # Save user to database
    session.add(user)
    session.commit()

    # Issue and return token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)
    return Token(access_token=access_token, token_type="bearer")
