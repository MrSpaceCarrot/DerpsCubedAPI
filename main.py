#!/usr/bin/env python3

# Module Imports
import logging
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi_pagination import add_pagination
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from routers import auth, economy, games, servers, users
from config import settings, log_config
from schemas.database import setup_database
from services.economy import randomize_exchange_rates
from services.storage import *
from services.games import *
from services.servers import *

# Tags metadata
tags_metadata = [{"name": "Auth"}, {"name": "Economy"}, {"name": "Games"}, {"name": "Servers"}, {"name": "Users"}]

# Task Scheduler
scheduler = AsyncIOScheduler()

# Startup logic
@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_database()
    create_bucket()
    if settings.APP_RUN_SCHEDULED_TASKS == True:
        scheduler.start()
        scheduler.add_job(randomize_exchange_rates, trigger=CronTrigger(minute='0,15,30,45'), id='randomize_exchange_rates')
        scheduler.add_job(update_last_updated_all, trigger=CronTrigger(minute='0,15,30,45'), id='update_last_updated_all')
        scheduler.add_job(three_hourly_maintanence, trigger=CronTrigger(hour='0,3,6,9,12,15,18,21'), id='three_hourly_maintanence')
        scheduler.add_job(update_server_statuses, trigger=CronTrigger(second='0'), id='update_server_statuses')
    yield
    if settings.APP_RUN_SCHEDULED_TASKS == True:
        scheduler.shutdown

# Create app
app = FastAPI(title=settings.APP_TITLE, 
              summary=settings.APP_SUMMARY,
              version=settings.APP_VERSION,
              lifespan=lifespan,
              redirect_slashes=False)
add_pagination(app)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.APP_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup static
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup routers
app.include_router(auth.router, prefix="/api/auth")
app.include_router(economy.router, prefix="/api/economy")
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
