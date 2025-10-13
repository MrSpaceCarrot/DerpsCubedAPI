# Module Imports
import logging
import requests
from typing import Union
from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from auth.security import require_permission
from config import settings
from schemas.database import get_session, apply_filters
from schemas.servers import *
from schemas.users import User
from services.servers import check_server_running


router = APIRouter()
logger = logging.getLogger("services")

# Get servers
@router.get("/", tags=["servers"], response_model=list[ServerPublic], dependencies=[Depends(require_permission("can_view_servers"))])
def get_servers(filters: FilterServer = Depends(), session: Session = Depends(get_session)) -> list[Server]:
    query = select(Server)
    query = apply_filters(query, Server, filters)
    return session.exec(query).all()
    
# Get server categories
@router.get("/categories", tags=["servers"], response_model=list[ServerCategoryPublic], dependencies=[Depends(require_permission("can_view_servers"))])
def get_server_categories(filters: FilterServerCategory = Depends(), session: Session = Depends(get_session)) -> list[ServerCategory]:
    query = select(ServerCategory)
    query = apply_filters(query, ServerCategory, filters)
    return session.exec(query).all()

# Add server category
@router.post("/categories/add/", tags=["servers"], response_model=ServerCategoryPublic, dependencies=[Depends(require_permission("can_manage_servers"))], status_code=201)
def add_server_category(category: ServerCategoryCreate, session: Session = Depends(get_session)):
    # Create category instance using validated user data
    db_category = ServerCategory(**category.model_dump())

    # Ensure that icon and color are set if minecraft
    if db_category.is_minecraft and (not db_category.icon or not db_category.color):
        raise HTTPException(status_code=400, detail="An icon and color must be provided for minecraft categories")
    else:
        db_category.icon = None
        db_category.color = None

    # Commit category
    session.add(db_category)
    session.commit()
    session.refresh(db_category)
    return db_category
    
# Get server category
@router.get("/categories/{id}", tags=["servers"], response_model=ServerCategoryPublic, dependencies=[Depends(require_permission("can_view_servers"))])
def get_server_category(id: int, session: Session = Depends(get_session)) -> ServerCategory:
    db_category = session.get(ServerCategory, id)
    if not db_category:
        raise HTTPException(status_code=404, detail="Server category not found")
    return db_category

# Edit server category
@router.patch("/categories/{id}/", tags=["servers"], response_model=ServerCategoryPublic, dependencies=[Depends(require_permission("can_manage_servers"))], status_code=200)
def edit_server_category(id: int, category: ServerCategoryUpdate, session: Session = Depends(get_session)):
    # Check that the category exists
    db_category = session.get(ServerCategory, id)
    if not db_category:
        raise HTTPException(status_code=404, detail="Server category not found")
        
    # Write updates to db model
    category_updates = category.model_dump(exclude_unset=True)
    for key, value in category_updates.items():
        setattr(db_category, key, value)

    # Ensure that icon and color are set if minecraft
    if db_category.is_minecraft and (not db_category.icon or not db_category.color):
        raise HTTPException(status_code=400, detail="An icon and color must be provided for minecraft categories")
    else:
        db_category.icon = None
        db_category.color = None

    # Commit category to db and return
    session.add(db_category)
    session.commit()
    session.refresh(db_category)
    return db_category

# Start server
@router.post("/start/{id}", tags=["servers"], dependencies=[Depends(require_permission("can_start_servers"))])
def start_server(id: Union[int, str], session: Session = Depends(get_session)):
    # Check that the server exists
    db_server = session.get(Server, id)
    if not db_server:
        db_server = session.exec(select(Server).where(Server.name == id)).first()
        if not db_server:
            raise HTTPException(status_code=404, detail="Server not found")

    # Check if the server is already running
    if check_server_running(db_server) == True:
        raise HTTPException(status_code=400, detail=f"Server '{db_server.display_name}' is already online")

    # Start server
    url: str = f"{settings.PTERODACTYL_DOMAIN}/api/client/servers/{db_server.uuid}/power"
    headers: dict = {'Authorization': f'Bearer {settings.PTERODACTYL_CLIENT_API_KEY}'}
    body: dict = {'signal': 'start'}
    response = requests.post(url=url, headers=headers, json=body)

    # Send response
    if response.status_code == 204:
        return f"Successfully starting server '{db_server.display_name}'"
    else:
        raise HTTPException(status_code=500, detail=f"An error occured starting server '{db_server.display_name}'")

# Add server
@router.post("/add/", tags=["servers"], response_model=ServerPublic, dependencies=[Depends(require_permission("can_manage_servers"))], status_code=201)
def add_server(server: ServerCreate, session: Session = Depends(get_session)):
    # Create server instance using validated user data
    db_server = Server(**server.model_dump())

    # Check that the given category id is valid
    db_category = session.get(ServerCategory, server.category_id)
    if not db_category:
        raise HTTPException(status_code=400, detail="The given server category was not found")

    # Commit server
    session.add(db_server)
    session.commit()
    session.refresh(db_server)
    return db_server

# Get server
@router.get("/{id}/", tags=["servers"], response_model=ServerPublicSingle, dependencies=[Depends(require_permission("can_view_servers"))])
def get_server(id: Union[int, str], session: Session = Depends(get_session)) -> Server:
    # Check that the server exists
    db_server = session.get(Server, id)
    if not db_server:
        db_server = session.exec(select(Server).where(Server.name == id)).first()
        if not db_server:
            raise HTTPException(status_code=404, detail="Server not found")
        
    # Add is_running information to response
    server_response: ServerPublicSingle = ServerPublicSingle(**db_server.model_dump(), is_running = check_server_running(db_server))

    # Return
    return server_response

# Edit server
@router.patch("/{id}/", tags=["servers"], response_model=ServerPublic, dependencies=[Depends(require_permission("can_manage_servers"))], status_code=200)
def edit_server(id: Union[int, str], server: ServerUpdate, session: Session = Depends(get_session)):
    # Check that the server exists
    db_server = session.get(Server, id)
    if not db_server:
        db_server = session.exec(select(Server).where(Server.name == id)).first()
        if not db_server:
            raise HTTPException(status_code=404, detail="Server not found")
        
    # Check that the given category id is valid
    if server.category_id:
        db_category = session.get(ServerCategory, server.category_id)
        if not db_category:
            raise HTTPException(status_code=400, detail="The given server category was not found")
        
    # Write updates to db model
    server_updates = server.model_dump(exclude_unset=True)
    for key, value in server_updates.items():
        setattr(db_server, key, value)

    # Commit server to db and return
    session.add(db_server)
    session.commit()
    session.refresh(db_server)
    return db_server

# Delete server
@router.delete("/{id}/", tags=["servers"], dependencies=[Depends(require_permission("can_manage_servers"))], status_code=204)
def delete_server(id: Union[int, str], session: Session = Depends(get_session)):
    # Check that the server exists
    db_server = session.get(Server, id)
    if not db_server:
        db_server = session.exec(select(Server).where(Server.name == id)).first()
        if not db_server:
            raise HTTPException(status_code=404, detail="Server not found")
        
    # Commit deletion
    session.delete(db_server)
    session.commit()
    return
