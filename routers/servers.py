# Module Imports
from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from schemas.database import get_session, engine
from schemas.servers import Server, ServerCategory


router = APIRouter()

# Get all servers
@router.get("/", tags=["servers"])
def get_servers(session: Session = Depends(get_session)) -> list[Server]:
    servers = session.exec(select(Server)).all()
    return [server.order() for server in servers]
    
# Get all server categories
@router.get("/categories/", tags=["servers"])
def get_server_categories(session: Session = Depends(get_session)) -> list[ServerCategory]:
    categories = session.exec(select(ServerCategory)).all()
    return [category.order() for category in categories]
    
# Get specific server category
@router.get("/categories/{id}", tags=["servers"])
def get_server_category(id: int, session: Session = Depends(get_session)) -> ServerCategory:
    category = session.get(ServerCategory, id)
    if not category:
        raise HTTPException(status_code=404, detail="Server category not found")
    return category.order()

# Get specific server
@router.get("/{id}/", tags=["servers"])
def get_server(id: int, session: Session = Depends(get_session)) -> Server:
    server = session.get(Server, id)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    return server.order()
