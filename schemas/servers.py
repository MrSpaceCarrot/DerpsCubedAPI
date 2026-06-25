# Module Imports
from datetime import datetime, timezone
import sqlalchemy as sa
from typing import Optional, Literal
from sqlmodel import SQLModel, Field, Relationship
from pydantic import field_serializer, field_validator
from fastapi_filter import FilterDepends, with_prefix
from fastapi_filter.contrib.sqlalchemy import Filter
from config import settings
from schemas.games import Game, GamePublicForServers, GameFilter


# Schemas
# ServerCategory
class ServerCategoryBase(SQLModel):
    name: str = Field(index=True, max_length=25)
    servers_color: Optional[str] = Field(index=True, default=None, max_length=25)
    servers_icon: Optional[str] = Field(index=True, default=None, max_length=100)
    is_minecraft: bool = Field(index=True)
    minecraft_color: Optional[str] = Field(index=True, default=None, max_length=25)
    minecraft_icon: Optional[str] = Field(index=True, default=None, max_length=45)
    

class ServerCategory(ServerCategoryBase, table=True):
    __tablename__ = "server_categories"
    id: Optional[int] = Field(primary_key=True, index=True, default=None)

    servers: Optional[list["Server"]] = Relationship(back_populates="category")


class ServerCategoryPublic(SQLModel):
    id: int
    name: str
    servers_color: Optional[str]
    servers_icon: Optional[str]
    is_minecraft: bool
    minecraft_color: Optional[str]
    minecraft_icon: Optional[str]

    @field_validator("servers_icon")
    def validate_servers_icon(cls, value: str) -> str:
        if value and not value.startswith("http"):
            return f"{settings.STORAGE_BUCKET_MEDIA_URL}/{settings.STORAGE_BUCKET_NAME}/{value}"
        return value
    

class ServerCategoryCreate(ServerCategoryBase):
    pass


class ServerCategoryUpdate(ServerCategoryBase):
    name: Optional[str] = None
    servers_color: Optional[str] = None
    servers_icon: Optional[str] = None
    is_minecraft: Optional[bool] = None
    minecraft_color: Optional[str] = None
    minecraft_icon: Optional[str] = None
    
    
class ServerCategoryFilter(Filter):
    id: Optional[int] = None
    is_minecraft: Optional[bool] = None
    order_by: Optional[list[str]] = ["id"]

    class Constants(Filter.Constants):
        model = ServerCategory


# Server
class ServerBase(SQLModel):
    name: str = Field(..., index=True, max_length=25, unique=True)
    display_name: str = Field(..., index=True, max_length=25)
    description: str = Field(..., index=True, max_length=500)
    category_id: int
    version: str = Field(..., index=True, max_length=25)
    modloader: str = Field(..., index=True, max_length=20)
    modlist: Optional[str] = Field(index=True, default=None, max_length=300)
    moddownload: Optional[str] = Field(index=True, default=None, max_length=150)
    modconditions: Optional[str] = Field(index=True, default=None, max_length=150)
    is_active: bool = Field(..., index=True)
    is_compatible: bool = Field(..., index=True)
    is_private: bool = Field(False, index=True)
    icon: Optional[str] = Field(index=True, default=None, max_length=45)
    color: Optional[str] = Field(index=True, default=None, max_length=25)
    emoji: str = Field(index=True, max_length=45)
    uuid: str = Field(index=True, max_length=8)
    domain: str = Field(index=True, max_length=60)
    banner_image: Optional[str] = Field(index=True, default=None, max_length=100)
    creation_date: Optional[datetime] = Field(index=True, default=None)


class Server(ServerBase, table=True):
    __tablename__ = "servers"
    id: Optional[int] = Field(primary_key=True, index=True, default=None)

    category_id: Optional[int] = Field(..., sa_column=sa.Column(sa.Integer, sa.ForeignKey("server_categories.id", ondelete="SET NULL")))
    category: Optional["ServerCategory"] = Relationship(back_populates="servers")

    port: int = Field(index=True)

    is_running: bool = Field(index=True, default=False)
    time_started: Optional[datetime] = Field(index=True, default=None)

    game_id: Optional[int] = Field(foreign_key="games.id")
    game: Optional["Game"] = Relationship(back_populates="servers")


class ServerPublic(SQLModel):
    id: int
    name: str
    display_name: str
    description: str
    category: Optional[ServerCategoryPublic]
    version: str
    modloader: str
    modlist: Optional[str]
    moddownload: Optional[str]
    modconditions: Optional[str]
    is_active: bool
    is_compatible: bool
    is_private: bool
    icon: Optional[str]
    color: Optional[str]
    emoji: str
    domain: str
    is_running: bool
    time_started: Optional[datetime]
    banner_image: Optional[str]
    game: Optional[GamePublicForServers]
    creation_date: Optional[datetime]

    @field_serializer("time_started")
    def validate_time_started(self, dt: datetime):
        if dt:
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        
    @field_validator("banner_image")
    def validate_banner_image(cls, value: str) -> str:
        if value and not value.startswith("http"):
            return f"{settings.STORAGE_BUCKET_MEDIA_URL}/{settings.STORAGE_BUCKET_NAME}/{value}"
        return value

"""
Might delete because model isn't very useful
class ServerPublicSingle(SQLModel):
    id: int
    name: str
    display_name: str
    description: str
    category_id: int
    version: str
    modloader: str
    modlist: Optional[str]
    moddownload: Optional[str]
    modconditions: Optional[str]
    is_active: bool
    is_compatible: bool
    is_private: bool
    icon: Optional[str]
    color: Optional[str]
    emoji: str
    uuid: str
    domain: str
    is_running: bool
    time_started: Optional[datetime]
    banner_image: Optional[str]
    game: Optional[GamePublicForServers]

    @field_serializer("time_started")
    def validate_time_started(self, dt: datetime):
        if dt:
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        
    @field_validator("banner_image")
    def validate_banner_image(cls, value: str) -> str:
        if value and not value.startswith("http"):
            return f"{settings.STORAGE_BUCKET_MEDIA_URL}/{settings.STORAGE_BUCKET_NAME}/{value}"
        return value
"""


class ServerCreate(ServerBase):
    name: str
    display_name: str
    description: str
    category_id: int
    version: str
    modloader: str
    modlist: Optional[str]
    moddownload: Optional[str]
    modconditions: Optional[str]
    is_active: bool
    is_compatible: bool
    is_private: bool
    icon: Optional[str]
    color: Optional[str]
    port: int
    emoji: str
    uuid: str
    domain: str
    creation_date: Optional[datetime]


class ServerUpdate(ServerBase):
    name: Optional[str] = None
    display_name: str = None
    description: Optional[str] = None
    category_id: Optional[int] = None
    version: Optional[str] = None
    modloader: Optional[str] = None
    modlist: Optional[str] = None
    moddownload: Optional[str] = None
    modconditions: Optional[str] = None
    is_active: Optional[bool] = None
    is_compatible: Optional[bool] = None
    is_private: Optional[bool] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    port: Optional[int] = None
    emoji: Optional[str] = None
    uuid: Optional[str] = None
    domain: Optional[str] = None
    creation_date: Optional[datetime] = None


class ServerFilter(Filter):
    name: Optional[str] = None
    name__like: Optional[str] = None
    display_name: Optional[str] = None
    display_name__like: Optional[str] = None
    category_: Optional[ServerCategoryFilter] = FilterDepends(
        with_prefix("category", ServerCategoryFilter)
    )
    version: Optional[str] = None
    modloader: Optional[str] = None
    is_active: Optional[bool] = None
    is_compatible: Optional[bool] = None
    is_private: Optional[bool] = None
    order_by: Optional[list[str]] = ["id"]
    is_running: Optional[bool] = None
    game: Optional[GameFilter] = FilterDepends(
        with_prefix("game", GameFilter)
    )

    class Constants(Filter.Constants):
        model = Server


