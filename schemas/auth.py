# Module Imports
from typing import TYPE_CHECKING, Optional
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from schemas.users import User


# Schemas
class ApiKey(SQLModel, table=True):
    __tablename__ = "api_keys"
    id: int = Field(primary_key=True, index=True)
    key: str = Field(index=True, default=None, max_length=255, unique=True)

    user_id: int = Field(foreign_key="users.id")
    user: "User" = Relationship(back_populates="api_keys")


class Token(SQLModel):
    access_token: str
    token_type: str

class TokenPublic(SQLModel):
    username: Optional[str] = None
