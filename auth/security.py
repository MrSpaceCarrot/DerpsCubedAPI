# Module Imports
import logging
import jwt
from jwt import PyJWTError
from typing import Optional
from fastapi import HTTPException, status, Depends, Security
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session, select
from config import settings
from schemas.database import engine
from schemas.auth import ApiKey
from schemas.users import User

# JWT Settings
SECRET_KEY = settings.JWT_SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.JWT_ACCESS_TOKEN_EXPIRY_MINS

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
logger = logging.getLogger("services")

# Validate all possible auth methods
# Return the auth method and identity if successful, otherwise raise an error
class Authenticator:
    # Create parameters for if either authentication method is allowed
    def __init__(self, jwt_token_allowed: bool, api_key_allowed: bool):
        self.jwt_token_allowed = jwt_token_allowed
        self.api_key_allowed = api_key_allowed

    def __call__(self,
                 jwt_token: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
                 api_key: Optional[str] = Security(api_key_header)
    ) -> dict:
        # Validate JWT Token
        if self.jwt_token_allowed and jwt_token:
            try:
                payload = jwt.decode(jwt=jwt_token.credentials, key=SECRET_KEY, algorithms=[ALGORITHM])
                username = payload.get("sub")
                with Session(engine) as session:
                    db_user: User = session.exec(select(User).where(User.username == username)).first()
                if not db_user.can_use_site:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your account has not yet been activated")
                return {"method": "jwt", "identity": username}
            except PyJWTError:
                pass
                     
        # Validate API Key
        if self.api_key_allowed and api_key:
            with Session(engine) as session:
                db_api_key: ApiKey = session.exec(select(ApiKey).where(ApiKey.key == api_key)).first()
                if db_api_key:
                    db_user = db_api_key.user
                    if not db_user.can_use_site:
                        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your account has not yet been activated")
                    return {"method": "api_key", "identity": db_api_key.key}
                
        # If all methods have been tried, return an error
        if self.jwt_token_allowed == False and jwt_token != None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated - An valid API key is required for this endpoint")
        elif self.api_key_allowed == False and api_key != None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated - A valid JWT token is required for this endpoint")
        else: 
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

# Get current user
def get_current_user(auth_info: dict =  Depends(Authenticator(True, True))) -> User:
    with Session(engine) as session:
        # Get user from their auth method
        if auth_info["method"] == "jwt":
            user = session.exec(select(User).where(User.username == auth_info["identity"])).first()
        if auth_info["method"] == "api_key":
            api_key = session.exec(select(ApiKey).where(ApiKey.key == auth_info["identity"])).first()
            user = api_key.user
        return user

# Get if current user can add games
def get_current_user_can_add_games(auth_info: dict =  Depends(Authenticator(True, True))) -> User:
    with Session(engine) as session:
        # Get user from their auth method
        if auth_info["method"] == "jwt":
            user = session.exec(select(User).where(User.username == auth_info["identity"])).first()
        if auth_info["method"] == "api_key":
            api_key = session.exec(select(ApiKey).where(ApiKey.key == auth_info["identity"])).first()
            user = api_key.user

        # Check if the user has permission to add games
        if not user.can_add_games:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your account has not been approved to add games")
        return user
