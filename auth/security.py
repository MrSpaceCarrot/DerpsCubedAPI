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
from schemas.database import engine, get_session
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
    def __call__(self,
                 jwt_token: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
                 api_key: Optional[str] = Security(api_key_header),
                 act_as_user: Optional[str] = act_as_user_header
    ) -> dict:
        # Validate JWT Token
        if jwt_token:
            try:
                payload = decode_jwt_token(jwt_token.credentials)
                user_id = payload.get("sub")
                with Session(engine) as session:
                    db_user: User = session.get(User, user_id)
                if not db_user.can_use_site:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Your account has not yet been activated")
                return db_user
            except PyJWTError:
                pass
                     
        # Validate API Key
        if api_key:
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
                                if not db_user:
                                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="An invalid discord id was provided")
                        
                        # Check if user id has been provided
                        else:
                            db_user = session.get(User, act_as_user)
                            if not db_user:
                                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="The provided user does not exist")
                    
                    # Otherwise get user assigned to the API Key
                    else:
                        db_user = db_api_key.user

                    return db_user
                
        # If all methods have been tried, return an error
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

# Require a certain permission for an endpoint
def require_permission(permission_code: str):
    def wrapper(current_user: User = Depends(Authenticator()), session: Session = Depends(get_session)):
        current_user: User = session.merge(current_user)
        user_permissions = {permission.code for permission in current_user.permissions}
        if permission_code not in user_permissions:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Missing permission: {permission_code}")
        return current_user
    return wrapper
