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

    user_id: Optional[int] = Field(default=None, foreign_key="users.id")
    user: Optional["User"] = Relationship(back_populates="api_keys")
