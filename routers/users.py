# Module Imports
from typing import Annotated
from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from auth.security import get_current_user
from schemas.database import get_session
from schemas.users import User

router = APIRouter()

# Get all users
@router.get("/", tags=["users"], dependencies=[Depends(get_current_user)])
def get_users(session: Session = Depends(get_session)) -> list[User]:
    users = session.exec(select(User).order_by(User.id.asc())).all()
    return [user.order() for user in users]

# Get current user
@router.get("/me", tags=["users"])
def get_current_user_info(current_user: User =  Depends(get_current_user)):
    return current_user
    
# Get specific user
@router.get("/{id}", tags=["users"], dependencies=[Depends(get_current_user)])
def get_user(id: int, session: Session = Depends(get_session)) -> User:
    user = session.get(User, id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user.order()
