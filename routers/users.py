# Module Imports
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, status, Depends, Query
from fastapi_filter import FilterDepends
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlmodel import Session, select
from auth.security import require_permission, Authenticator
from schemas.database import get_session
from schemas.users import *

router = APIRouter()
logger = logging.getLogger("services")

# Get users
@router.get("", tags=["users"], dependencies=[Depends(require_permission("can_view_users"))])
def get_users(filter: UserFilter = FilterDepends(UserFilter), session: Session = Depends(get_session)) -> Page[UserPublic]:
    query = select(User)
    query = filter.filter(query)
    query = filter.sort(query)
    return paginate(session, query)

# Create user
@router.post("/create", tags=["users"], response_model=UserPublic, dependencies=[Depends(require_permission("can_manage_users"))], status_code=201)
def create_user(user: UserCreate, session: Session = Depends(get_session)):
    # Check if user already exists
    db_user = session.exec(select(User).where(User.discord_id == user.discord_id)).first()
    if not db_user:
        db_user = User(**user.model_dump())
        session.add(db_user)
        session.commit()
        session.refresh(db_user)
    return db_user

# Get current user
@router.get("/me", tags=["users"], response_model=UserPublic)
def get_current_user_info(current_user: User =  Depends(Authenticator())):
    return current_user

# Update current user
@router.patch("/me", tags=["users"], response_model=UserPublic)
def update_current_user_info(user: UserUpdate, current_user: User =  Depends(Authenticator()), session: Session = Depends(get_session)):
    # Get updates provided by user
    user_updates = user.model_dump(exclude_unset=True)

    # Update display name last changed
    if user.display_name != current_user.display_name:
        current_user.display_name_last_changed = datetime.now(timezone.utc)

    # Write updates to db model
    for key, value in user_updates.items():
        setattr(current_user, key, value)

    # Commit user to db and return
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return current_user
    
# Get specific user
@router.get("/{id}", tags=["users"], response_model=UserPublic, dependencies=[Depends(require_permission("can_view_users"))])
def get_user(id: int, session: Session = Depends(get_session)) -> User:
    user = session.get(User, id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user
