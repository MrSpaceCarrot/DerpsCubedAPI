# Module Imports
import requests
import jwt
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status
from config import settings
from auth.security import SECRET_KEY, ALGORITHM


# Get Discord access token from access code
def get_discord_access_token(access_code: str):
    token_url = settings.DISCORD_ACCESS_TOKEN_URL
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
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Error getting access token"
        )
    return response.json().get('access_token')

# Get discord user information
def get_discord_user_info(access_token: str):
    headers = {'Authorization': f"Bearer {access_token}"}
    response = requests.get(settings.DISCORD_USERINFO_URL, headers=headers)

    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Error getting user information"
        )
    return response.json()

# Create JWT access token
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
