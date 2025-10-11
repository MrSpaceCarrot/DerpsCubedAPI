# Module Imports
from typing import TYPE_CHECKING, Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from schemas.auth import ApiKey
    from schemas.economy import UserCurrency, UserJob, Cooldown, BlackjackGame
    from schemas.games import Game, GameRating


# Schemas
# Permission
class UserPermission(SQLModel, table=True):
    __tablename__ = "user_permissions"
    user_id: int = Field(foreign_key="users.id", primary_key=True)
    permission_id: int = Field(foreign_key="permissions.id", primary_key=True)


class Permission(SQLModel, table=True):
    __tablename__ = "permissions"
    id: Optional[int] = Field(primary_key=True, index=True)
    code: str = Field(index=True, max_length=30)
    description: str = Field(index=True, max_length=100)

    users: Optional[list["User"]] = Relationship(back_populates="permissions", link_model=UserPermission)


# User
class User(SQLModel, table=True):
    __tablename__ = "users"
    id: int = Field(primary_key=True, index=True)
    discord_id: str = Field(index=True, default=None, max_length=100)
    username: Optional[str] = Field(index=True, default=None, max_length=100)
    avatar_link: Optional[str] = Field(index=True, default=None, max_length=100)
    first_site_login: Optional[datetime] = Field(index=True, default=None)
    last_site_login: Optional[datetime] = Field(index=True, default=None)
    display_name: Optional[str] = Field(index=True, default=None, max_length=100)
    display_name_last_changed: Optional[datetime] = Field(index=True, default=None)
    can_use_site: Optional[bool] = Field(index=True, default=None)

    api_keys: Optional[list["ApiKey"]] = Relationship(back_populates="user")
    games_added: Optional[List["Game"]] = Relationship(back_populates="added_by")
    ratings: Optional[list["GameRating"]] = Relationship(back_populates="user")
    balances: Optional[list["UserCurrency"]] = Relationship(back_populates="user")
    job: Optional["UserJob"] = Relationship(back_populates="user")
    cooldowns: Optional[list["Cooldown"]] = Relationship(back_populates="user")
    blackjack_games: Optional[list["BlackjackGame"]] = Relationship(back_populates="user")
    permissions: Optional[List["Permission"]] = Relationship(back_populates="users", link_model=UserPermission)


class UserPublic(SQLModel):
    id: int
    discord_id: str
    username: Optional[str]
    avatar_link: Optional[str]
    first_site_login: Optional[datetime]
    last_site_login: Optional[datetime]
    display_name: Optional[str]
    display_name_last_changed: Optional[datetime]
    can_use_site: Optional[bool]
    can_add_games: Optional[bool]
    permissions: Optional[list["Permission"]]


class UserPublicShort(SQLModel):
    id: int
    discord_id: str


class UserCreate(SQLModel):
    discord_id: str


class UserUpdate(SQLModel):
    display_name: Optional[str]
