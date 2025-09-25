# Module Imports
from typing import Annotated
from fastapi import APIRouter, Query
from database.models import SessionDep, Server
from sqlmodel import select

router = APIRouter()

@router.get("/about")
def root():
    return {"John": "Baller"}

@router.get("/servers")
def servers(session: SessionDep, offset: int = 0, limit: Annotated[int, Query(le=100)] = 100) -> list[Server]:
    servers = session.exec(select(Server).offset(offset).limit(limit)).all()
    return servers