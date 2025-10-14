# Module Imports
import requests
import jwt
import logging
from jwt.exceptions import ExpiredSignatureError
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlmodel import Session, select
from config import settings
from schemas.database import engine
from schemas.auth import RefreshToken


logger = logging.getLogger("services")

# Get Discord access token from access code
def get_discord_access_token(access_code: str):
    token_url = "https://discord.com/api/oauth2/token"
    data = {
        "client_id": settings.DISCORD_CLIENT_ID,
        "client_secret": settings.DISCORD_CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": access_code,
        "redirect_uri": settings.DISCORD_REDIRECT_URL,
        "scope": "identify"
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    response = requests.post(token_url, data=data, headers=headers)
    
    if response.status_code != 200:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Error getting access token")
    return response.json().get('access_token')

# Get discord user information
def get_discord_user_info(access_token: str):
    headers = {'Authorization': f"Bearer {access_token}"}
    response = requests.get("https://discord.com/api/v10/users/@me", headers=headers)

    if response.status_code != 200:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Error getting user information")
    return response.json()

# Get discord user servers
def get_discord_user_servers(access_token: str):
    headers = {'Authorization': f"Bearer {access_token}"}
    response = requests.get("https://discord.com/api/v10/users/@me/guilds", headers=headers)

    if response.status_code != 200:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Error getting user servers")
    return response.json()

# Create JWT token
def create_jwt_token(user_id: str, issued_at: datetime, expires_delta: timedelta):
    to_encode = {"sub": str(user_id),
                 "iat": issued_at,
                 "exp": issued_at + expires_delta}
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

# Get payload from JWT token
def decode_jwt_token(jwt_token: HTTPAuthorizationCredentials):
    try:
        decoded_jwt = jwt.decode(jwt=jwt_token, key=settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return decoded_jwt
    except ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Expired token")

# Clear expired refresh tokens
def clear_expired_refresh_tokens() -> None:
    with Session(engine) as session:
        db_tokens = session.exec(select(RefreshToken)).all()
        now = datetime.now(timezone.utc)
        kept: int = 0
        deleted: int = 0
        for token in db_tokens:
            if now > token.expires_at.replace(tzinfo=timezone.utc):
                session.delete(token)
                deleted += 1
            else:
                kept += 1
        session.commit()
        logger.info(f"Deleted {deleted} expired refresh tokens, kept {kept}")
