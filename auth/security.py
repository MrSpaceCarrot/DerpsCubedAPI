# Module Imports
import logging
import jwt
from jwt import PyJWTError
from typing import Annotated, Optional
from jwt import InvalidTokenError
from fastapi import HTTPException, status, Depends, Security
from fastapi.security import APIKeyHeader, HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session, select
from config import settings
from schemas.database import engine
from schemas.auth import ApiKey, TokenPublic
from schemas.users import User

# JWT Settings
SECRET_KEY = settings.JWT_SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.JWT_ACCESS_TOKEN_EXPIRY_MINS

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
logger = logging.getLogger("services")

# Validate API Key
def get_api_key(api_key_header: str = Security(api_key_header), required: bool = True) -> Optional[dict]:
    logger.info("Getting API Key...")
    with Session(engine) as session:
        # Check if Api key exists in database
        api_key = session.exec(select(ApiKey).where(ApiKey.key == api_key_header)).all()
        if api_key:
            return {"method": "api_key", "identity": api_key}
        # Only raise an error if api key only is being checked
        if required:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated - Invalid API Key",
            )
        return None

# Validate JWT Token
def get_jwt_token(token: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False)), required: bool = True) -> Optional[dict]:
    logger.info("Getting JWT Token...")
    # Decode token to get username
    try:
        payload = jwt.decode(jwt=token.credentials, key=SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        return {"method": "jwt", "identity": username}
    except PyJWTError:
        # Only raise an error if jwt token only is being checked
        if required:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated - Invalid Token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return None
        
# Get API Key without throwing error
def get_optional_api_key() -> Optional[dict]:
    return get_api_key(required=False)

# Get jwt token without throwing error
def get_optional_jwt_token() -> Optional[dict]:
    return get_jwt_token(required=False)
    
# Validate either jwt token or api key
def get_auth_info(jwt_token: Annotated[Optional[dict], Depends(get_optional_jwt_token)], 
                  api_key: Annotated[Optional[dict], Depends(get_optional_api_key)]) -> dict:
    logger.info("Getting Auto Info...")
    logger.info(jwt_token)
    logger.info(api_key)
    if jwt_token:
        return jwt_token
    if api_key:
        return api_key
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
    )

# Get current user
def get_current_user(auth_info: dict =  Depends(get_auth_info)) -> User:
    logger.info("Getting Current User...")
    with Session(engine) as session:
        if auth_info["method"] == "jwt":
            user = session.exec(select(User).where(User.username == auth_info["identity"])).all()
        if auth_info["method"] == "api_key":
            api_key = session.exec(select(ApiKey).where(ApiKey.key == auth_info["identity"])).first()
            user = api_key.user
        return user
