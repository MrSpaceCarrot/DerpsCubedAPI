# Module Imports
from fastapi import FastAPI, Depends
from contextlib import asynccontextmanager
from database import models
from routers import servers, users
from core.config import settings
from core.auth import get_api_key

# Startup logic
@asynccontextmanager
async def lifespan(app: FastAPI):
    models.setup_database()
    yield

# Tags metadata
tags_metadata = [{"name": "Servers"}, {"name": "Users"}]

# Create app
app = FastAPI(title=settings.APP_TITLE, 
              summary=settings.APP_SUMMARY,
              version=settings.APP_VERSION,
              lifespan=lifespan)

# Setup routers
app.include_router(servers.router, prefix="/api/servers", dependencies=[Depends(get_api_key)])
app.include_router(users.router, prefix="/api/users", dependencies=[Depends(get_api_key)])
