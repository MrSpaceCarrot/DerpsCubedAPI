# Module Imports
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from pydantic import field_serializer
from sqlmodel import SQLModel, Field, Relationship
from schemas.users import UserPublic

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

    subject: int = Field(foreign_key="users.id", index=True)
    user: "User" = Relationship(back_populates="refresh_tokens")

    issued_at: datetime = Field(index=True)
    expires_at: datetime = Field(index=True)

    @field_serializer("issued_at")
    def validate_issued_at(self, dt: datetime):
        if dt:
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        
    @field_serializer("expires_at")
    def validate_expires_at(self, dt: datetime):
        if dt:
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)


class Tokens(SQLModel):
    access_token: str
    token_type: str
    expires: datetime
    expires_in: int
    refresh_token: str
    user: UserPublic
    user_permissions: list[str]

    @field_serializer("expires")
    def validate_expires(self, dt: datetime):
        if dt:
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
