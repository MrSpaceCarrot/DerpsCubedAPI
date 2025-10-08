# Module Imports
import logging
import jwt
from jwt import PyJWTError
from typing import Optional
from fastapi import HTTPException, status, Depends, Security, Header
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session, select
from config import settings
from auth.utilities import decode_jwt_token
from schemas.database import engine
from schemas.auth import ApiKey
from schemas.users import User
from services.users import get_or_create_user

# Logger
logger = logging.getLogger("services")

# Setup headers
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
act_as_user_header = Header(default=None, alias="X-Act-As-User", description="User to send request as (API Key only)")

# Validate all possible auth methods
# Return the auth method and identity if successful, otherwise raise an error
class Authenticator:
    # Create parameters for if either authentication method is allowed
    def __init__(self, jwt_token_allowed: bool, api_key_allowed: bool):
        self.jwt_token_allowed = jwt_token_allowed
        self.api_key_allowed = api_key_allowed

    def __call__(self,
                 jwt_token: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
                 api_key: Optional[str] = Security(api_key_header),
                 act_as_user: Optional[str] = act_as_user_header
    ) -> dict:
        # Validate JWT Token
        if self.jwt_token_allowed and jwt_token:
            try:
                payload = decode_jwt_token(jwt_token.credentials)
                user_id = payload.get("sub")
                with Session(engine) as session:
                    db_user: User = session.get(User, user_id)
                if not db_user.can_use_site:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your account has not yet been activated")
                return {"method": "jwt", "identity": int(user_id)}
            except PyJWTError:
                pass
                     
        # Validate API Key
        if self.api_key_allowed and api_key:
            with Session(engine) as session:
                # Get API Key in database
                db_api_key: ApiKey = session.exec(select(ApiKey).where(ApiKey.key == api_key)).first()

                if db_api_key:
                    # Check if API Key is acting on behalf of a user
                    if act_as_user:
                        # Check if discord id has been provided
                        if len(act_as_user) > 7:
                            db_user = session.exec(select(User).where(User.discord_id == act_as_user)).first()
                            if not db_user:
                                db_user = get_or_create_user(act_as_user)
                        
                        # Check if user id has been provided
                        else:
                            db_user = session.get(User, act_as_user)
                            if not db_user:
                                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="The provided user does not exist")
                    
                    # Otherwise get user assigned to the API Key
                    else:
                        db_user = db_api_key.user

                    return {"method": "api_key", "identity": db_user.id}
                
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
        return session.get(User, auth_info["identity"])

# Get if current user can add games
def get_current_user_can_add_games(auth_info: dict =  Depends(Authenticator(True, True))) -> User:
    with Session(engine) as session:
        user = session.get(User, auth_info["identity"])
        if not user.can_add_games:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your account has not been approved to add games")
        return user
