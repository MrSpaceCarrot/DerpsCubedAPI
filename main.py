# Module Imports
import logging
import uvicorn
from fastapi import FastAPI, Depends
from contextlib import asynccontextmanager
from routers import auth, games, servers, users
from config import settings, log_config
from schemas.database import setup_database

# Tags metadata
tags_metadata = [{"name": "Auth"}, {"name": "Games"}, {"name": "Servers"}, {"name": "Users"}]

# Startup logic
@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_database()
    yield

# Create app
app = FastAPI(title=settings.APP_TITLE, 
              summary=settings.APP_SUMMARY,
              version=settings.APP_VERSION,
              lifespan=lifespan)

# Setup routers
app.include_router(auth.router, prefix="/api/auth")
app.include_router(games.router, prefix="/api/games")
app.include_router(servers.router, prefix="/api/servers")
app.include_router(users.router, prefix="/api/users")

# Run app
if __name__ == "__main__":
    logging.config.dictConfig(log_config)
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.APP_RELOAD,
        log_config=log_config,
        reload_excludes='*.log'
    )
