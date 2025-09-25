# Module Imports
from fastapi import APIRouter, HTTPException
from database.models import engine, Server, ServerCategory
from sqlmodel import Session, select

router = APIRouter()

# Get all servers
@router.get("/servers")
def get_servers() -> list[Server]:
    with Session(engine) as session:
        servers = session.exec(select(Server)).all()
        return [server.order() for server in servers]

# Get specific server
@router.get("/servers/{id}")
def get_server(id: int) -> Server:
    with Session(engine) as session:
        server = session.get(Server, id)
        if not server:
            raise HTTPException(status_code=404, detail="Server not found")
        return server
    
# Get all server categories
@router.get("/servercategories")
def get_server_categories() -> list[ServerCategory]:
    with Session(engine) as session:
        categories = session.exec(select(ServerCategory)).all()
        return [category.order() for category in categories]
    
# Get specific server category
@router.get("/servercategories/{id}")
def get_server_category(id: int) -> ServerCategory:
    with Session(engine) as session:
        category = session.get(ServerCategory, id)
        if not category:
            raise HTTPException(status_code=404, detail="Server category not found")
        return category