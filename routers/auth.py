# Module Imports
import logging
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, status, Request, Response, Cookie, Depends, Header
from fastapi.responses import RedirectResponse
from sqlmodel import Session, select
from config import settings
from auth.utilities import *
from schemas.database import get_session
from schemas.auth import Tokens, RefreshToken
from schemas.users import User
from services.users import get_or_create_user


router = APIRouter()
logger = logging.getLogger("services")

# Redirect to discord login screen
@router.get("/discord/login", tags=["auth"])
def discord_login() -> RedirectResponse:
    return RedirectResponse(url=settings.DISCORD_AUTHORIZE_URL)

# Authenticate user once they login with discord
@router.get("/discord/callback", tags=["auth"])
def discord_callback(response: Response, code: str | None = None, redirect_url: str = settings.DISCORD_REDIRECT_URL, session: Session = Depends(get_session)):
    # Ensure access code is present
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Access code is missing"
        )
    
    # Ensure redirect url
    if not redirect_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Redirect url is missing"
        )
    
    # Get discord access token
    access_token = get_discord_access_token(code, redirect_url)

    # Get discord user information
    user_info = get_discord_user_info(access_token)

    # Get user
    user: User = get_or_create_user(user_info["id"])

    # Setup user if they exist but are doing first login
    if user.first_site_login == None:
        user.first_site_login = datetime.now(timezone.utc)
        user.display_name = user_info["username"]
        user.can_use_site = False
        
        # If the user is a member of certain discord servers, instantly activate their account
        whitelisted_server = False
        for server in get_discord_user_servers(access_token):
            if server["id"] in settings.DISCORD_SERVER_WHITELIST:
                whitelisted_server = True
                break
        if whitelisted_server:
            user.can_use_site = True

    # Update some fields every time a user logs in
    user.username = user_info["username"]
    user.avatar_link = f"https://cdn.discordapp.com/avatars/{user_info['id']}/{user_info['avatar']}?size=1024"
    user.last_site_login = datetime.now(timezone.utc)
    session.add(user)

    # Issue access and refresh token, save refresh token to database
    issued_at = datetime.now(timezone.utc)
    access_token = create_jwt_token(user_id=user.id, issued_at=issued_at, expires_delta=timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRY_MINS))
    refresh_token = create_jwt_token(user_id=user.id, issued_at=issued_at, expires_delta=timedelta(minutes=settings.JWT_REFRESH_TOKEN_EXPIRY_MINS))
    db_refresh_token = RefreshToken(subject=user.id, issued_at=issued_at, expires_at=issued_at + timedelta(minutes=settings.JWT_REFRESH_TOKEN_EXPIRY_MINS))
    session.commit()
    session.add(db_refresh_token)

    # Create return model
    tokens = Tokens(access_token=access_token, token_type="bearer", expires_in=settings.JWT_ACCESS_TOKEN_EXPIRY_MINS * 60, refresh_token=refresh_token)

    # Set HTTP only cookies for both tokens
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,
        samesite="Lax",
        max_age=settings.JWT_ACCESS_TOKEN_EXPIRY_MINS * 60,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,
        samesite="Lax",
        max_age=settings.JWT_REFRESH_TOKEN_EXPIRY_MINS * 60,
    )

    # Return tokens
    return tokens

# Issue a new access token using a refresh token
@router.post("/token/refresh", tags=["auth"], response_model=Tokens)
def refresh_access_token(response: Response,
                         authorization: Optional[str] = Header(None, convert_underscores=False),
                         refresh_cookie: Optional[str] = Cookie(default=None, alias="refresh_token"), 
                         session: Session = Depends(get_session)):
    # Ensure request has a refresh token, check either cookie or auth header
    logger.critical(authorization)
    if refresh_cookie:
        refresh_token = refresh_cookie
    elif authorization:
        refresh_token = authorization.split(" ")[1]
    else:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token")

    # Decode token
    payload = decode_jwt_token(refresh_token)
    user_id = payload.get("sub")
    issued_at = datetime.fromtimestamp(payload.get("iat"), tz=timezone.utc)
    expires_at = datetime.fromtimestamp(payload.get("exp"), tz=timezone.utc)

    # Search for token in database
    db_refresh_token = session.exec(select(RefreshToken).where(RefreshToken.subject == user_id, 
                                                               RefreshToken.issued_at == issued_at,
                                                               RefreshToken.expires_at == expires_at)).first()
    
    # Give error if no token was found
    if not db_refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    # Generate new token
    new_access_token = create_jwt_token(user_id=payload.get("sub"), issued_at=datetime.now(timezone.utc), expires_delta=timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRY_MINS))

    # Set cookie and return
    response.set_cookie(
        key="access_token",
        value=new_access_token,
        httponly=True,
        secure=True,
        samesite="None",
        max_age=settings.JWT_ACCESS_TOKEN_EXPIRY_MINS * 60,
    )

    return Tokens(access_token=new_access_token, token_type="bearer", expires_in=settings.JWT_ACCESS_TOKEN_EXPIRY_MINS * 60, refresh_token=refresh_token)
