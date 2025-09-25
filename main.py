# Module Imports
from fastapi import FastAPI
from contextlib import asynccontextmanager
from database import models
from routers import servers
from core.config import settings

# Startup logic
@asynccontextmanager
async def lifespan(app: FastAPI):
    models.setup_database()
    yield

# Create app
app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

# Setup routers
app.include_router(servers.router)

# Root
@app.get("/")
def root():
    return {"Hello": "World"}
