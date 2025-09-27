# Module Imports
from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from schemas.database import get_session
from schemas.users import User

router = APIRouter()

# Get all users
@router.get("/", tags=["users"])
def get_users(session: Session = Depends(get_session)) -> list[User]:
    users = session.exec(select(User)).all()
    return [user.order() for user in users]
    
# Get specific user
@router.get("/{id}", tags=["users"])
def get_user(id: int, session: Session = Depends(get_session)) -> User:
    user = session.get(User, id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user.order()
