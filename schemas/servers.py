# Module Imports
from typing import Optional
from sqlmodel import SQLModel, Field


class Server(SQLModel, table=True):
    __tablename__ = "servers"
    id: int = Field(primary_key=True, index=True)
    name: Optional[str] = Field(index=True, default=None, max_length=25)
    description: Optional[str] = Field(index=True, default=None, max_length=150)
    category: Optional[str] = Field(index=True, default=None, max_length=25)
    version: Optional[str] = Field(index=True, default=None, max_length=25)
    modloader: Optional[str] = Field(index=True, default=None, max_length=20)
    modlist: Optional[str] = Field(index=True, default=None, max_length=300)
    moddownload: Optional[str] = Field(index=True, default=None, max_length=150)
    is_active: Optional[bool] = Field(index=True, default=None)
    is_compatible: Optional[bool] = Field(index=True, default=None)
    modconditions: Optional[str] = Field(index=True, default=None, max_length=150)
    icon: Optional[str] = Field(index=True, default=None, max_length=45)
    color: Optional[str] = Field(index=True, default=None, max_length=25)
    port: Optional[int] = Field(index=True, default=None)
    emoji: Optional[str] = Field(index=True, default=None, max_length=45)
    uuid: Optional[str] = Field(index=True, default=None, max_length=30)
    domain: Optional[str] = Field(index=True, default=None, max_length=60)

    def order(self):
        return {
            "id": self.id, 
            "name": self.name, 
            "description": self.description, 
            "category": self.category, 
            "version": self.version, 
            "modloader": self.modloader, 
            "moddownload": self.moddownload, 
            "active": self.is_active, 
            "compatible": self.is_compatible,
            "modconditions": self.modconditions, 
            "icon": self.icon, 
            "color": self.color, 
            "port": self.port, 
            "emoji": self.emoji,
            "uuid": self.uuid, 
            "domain": self.domain
        }


class ServerCategory(SQLModel, table=True):
    __tablename__ = "server_categories"
    id: int = Field(primary_key=True, index=True)
    name: Optional[str] = Field(index=True, default=None, max_length=25)
    icon: Optional[str] = Field(index=True, default=None, max_length=45)
    color: Optional[str] = Field(index=True, default=None, max_length=25)
    is_minecraft: Optional[bool] = Field(index=True, default=None)

    def order(self):
        return {
            "id": self.id, 
            "name": self.name, 
            "icon": self.icon, 
            "color": self.color, 
            "is_minecraft": self.is_minecraft
        }
