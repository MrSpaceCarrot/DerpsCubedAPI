# Module Imports
from fastapi import APIRouter, HTTPException
from database.models import engine, User
from sqlmodel import Session, select

router = APIRouter()

# Get all users
@router.get("/", tags=["users"])
def get_users() -> list[User]:
    with Session(engine) as session:
        users = session.exec(select(User)).all()
        return [user.order() for user in users]
    
# Get specific user
@router.get("/{id}", tags=["users"])
def get_user(id: int) -> User:
    with Session(engine) as session:
        user = session.get(User, id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user.order()
    