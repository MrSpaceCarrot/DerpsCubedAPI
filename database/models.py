# Module Imports
from typing import Annotated
from urllib.parse import quote_plus
from fastapi import Depends
from sqlmodel import Field, Session, SQLModel, create_engine
from core.config import settings

# Database connection
DATABASE_URL = f"mysql+mysqlconnector://{settings.DB_USERNAME}:{quote_plus(settings.DB_PASSWORD)}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_DATABASE}"
engine = create_engine(DATABASE_URL)

def setup_database():
    SQLModel.metadata.create_all(engine)

# Get session
#def get_session():
#    with Session(engine) as session:
#        yield session

#SessionDep = Annotated[Session, Depends(get_session)]

# Models
class Server(SQLModel, table=True):
    __tablename__ = "servers"
    id: int = Field(primary_key=True, index=True)
    name: str | None = Field(index=True, default=None, max_length=25)
    description: str | None = Field(index=True, default=None, max_length=150)
    category: str | None = Field(index=True, default=None, max_length=25)
    version: str | None = Field(index=True, default=None, max_length=25)
    modloader: str | None = Field(index=True, default=None, max_length=20)
    modlist: str | None = Field(index=True, default=None, max_length=300)
    moddownload: str | None = Field(index=True, default=None, max_length=150)
    is_active: bool | None = Field(index=True, default=None)
    is_compatible: bool | None = Field(index=True, default=None)
    modconditions: str | None = Field(index=True, default=None, max_length=150)
    icon: str | None = Field(index=True, default=None, max_length=45)
    color: str | None = Field(index=True, default=None, max_length=25)
    port: int | None = Field(index=True, default=None)
    emoji: str | None = Field(index=True, default=None, max_length=45)
    uuid: str | None = Field(index=True, default=None, max_length=30)
    domain: str | None = Field(index=True, default=None, max_length=60)

    def order(self):
        return {
            "id": self.id, "name": self.name, "description": self.description, "category": self.category, "version": self.version, 
            "modloader": self.modloader, "moddownload": self.moddownload, "active": self.is_active, "compatible": self.is_compatible,
            "modconditions": self.modconditions, "icon": self.icon, "color": self.color, "port": self.port, "emoji": self.emoji,
            "uuid": self.uuid, "domain": self.domain
        }

class ServerCategory(SQLModel, table=True):
    __tablename__ = "servercategories"
    id: int = Field(primary_key=True, index=True)
    name: str | None = Field(index=True, default=None, max_length=25)
    icon: str | None = Field(index=True, default=None, max_length=45)
    color: str | None = Field(index=True, default=None, max_length=25)
    is_minecraft: bool | None = Field(index=True, default=None)

    def order(self):
        return {"id": self.id, "name": self.name, "icon": self.icon, "color": self.color, "is_minecraft": self.is_minecraft}