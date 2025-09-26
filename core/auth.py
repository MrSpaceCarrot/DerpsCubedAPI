# Module Imports
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
from database.models import engine, ApiKey
from sqlmodel import Session, select

api_key_header = APIKeyHeader(name="X-API-Key")

# Get Api Key from request
def get_api_key(api_key_header: str = Security(api_key_header)):
    with Session(engine) as session:
        # Check if Api key exists in database
        api_key = session.exec(select(ApiKey).where(ApiKey.key == api_key_header)).all()
        if api_key:
            return api_key
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )

