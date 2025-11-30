# Module Imports
from datetime import datetime
import sqlalchemy as sa
from typing import Optional, Literal
from sqlmodel import SQLModel, Field, Relationship
from fastapi_filter.contrib.sqlalchemy import Filter


# Schemas
# Server
class ServerBase(SQLModel):
    name: str = Field(..., index=True, max_length=25, unique=True)
    display_name: str = Field(..., index=True, max_length=25)
    description: str = Field(..., index=True, max_length=150)
    category_id: int
    version: str = Field(..., index=True, max_length=25)
    modloader: str = Field(..., index=True, max_length=20)
    modlist: Optional[str] = Field(index=True, default=None, max_length=300)
    moddownload: Optional[str] = Field(index=True, default=None, max_length=150)
    modconditions: Optional[str] = Field(index=True, default=None, max_length=150)
    is_active: bool = Field(..., index=True)
    is_compatible: bool = Field(..., index=True)
    icon: Optional[str] = Field(index=True, default=None, max_length=45)
    color: Optional[str] = Field(index=True, default=None, max_length=25)
    emoji: str = Field(index=True, max_length=45)
    uuid: str = Field(index=True, max_length=8)
    domain: str = Field(index=True, max_length=60)


class Server(ServerBase, table=True):
    __tablename__ = "servers"
    id: Optional[int] = Field(primary_key=True, index=True, default=None)

    category_id: Optional[int] = Field(..., sa_column=sa.Column(sa.Integer, sa.ForeignKey("server_categories.id", ondelete="SET NULL")))
    category: Optional["ServerCategory"] = Relationship(back_populates="servers")

    port: int = Field(index=True)

    is_running: bool = Field(index=True, default=False)
    time_started: Optional[datetime] = Field(index=True, default=None)


class ServerPublic(SQLModel):
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
    icon: Optional[str]
    color: Optional[str]
    emoji: str
    domain: str
    is_running: bool
    time_started: Optional[datetime]


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
    icon: Optional[str]
    color: Optional[str]
    emoji: str
    uuid: str
    domain: str
    is_running: bool
    time_started: Optional[datetime]


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
    icon: Optional[str]
    color: Optional[str]
    port: int
    emoji: str
    uuid: str
    domain: str


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
    icon: Optional[str] = None
    color: Optional[str] = None
    port: Optional[int] = None
    emoji: Optional[str] = None
    uuid: Optional[str] = None
    domain: Optional[str] = None


class ServerFilter(Filter):
    name: Optional[str] = None
    display_name: Optional[str] = None
    category_id: Optional[int] = None
    version: Optional[str] = None
    modloader: Optional[str] = None
    is_active: Optional[bool] = None
    is_compatible: Optional[bool] = None
    order_by: Optional[list[str]] = ["id"]
    is_running: Optional[bool] = None

    class Constants(Filter.Constants):
        model = Server


# ServerCategory
class ServerCategoryBase(SQLModel):
    name: str = Field(index=True, max_length=25)
    icon: Optional[str] = Field(index=True, default=None, max_length=45)
    color: Optional[str] = Field(index=True, default=None, max_length=25)
    is_minecraft: bool = Field(index=True)


class ServerCategory(ServerCategoryBase, table=True):
    __tablename__ = "server_categories"
    id: Optional[int] = Field(primary_key=True, index=True, default=None)

    servers: Optional[list["Server"]] = Relationship(back_populates="category")


class ServerCategoryPublic(SQLModel):
    id: int
    name: str
    icon: Optional[str]
    color: Optional[str]
    is_minecraft: bool


class ServerCategoryCreate(ServerCategoryBase):
    pass


class ServerCategoryUpdate(ServerCategoryBase):
    name: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    is_minecraft: Optional[bool] = None


class ServerCategoryFilter(Filter):
    is_minecraft: Optional[bool] = None
    order_by: Optional[list[str]] = ["id"]

    class Constants(Filter.Constants):
        model = ServerCategory
