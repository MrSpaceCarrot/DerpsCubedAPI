# Module Imports
from datetime import datetime
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

    can_act_as_user: bool = Field(default=False)


class RefreshToken(SQLModel, table=True):
    __tablename__ = "refresh_tokens"
    id: Optional[int] = Field(primary_key=True, index=True)
    subject: str = Field(index=True, max_length=100)
    issued_at: datetime = Field(index=True)
    expires_at: datetime = Field(index=True)


class Tokens(SQLModel):
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: str
