# Module Imports
from urllib.parse import quote_plus
from sqlmodel import SQLModel, Field, create_engine, Relationship
from datetime import datetime
from config import settings

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
# Authentication
class User(SQLModel, table=True):
    __tablename__ = "users"
    id: int = Field(primary_key=True, index=True)
    discord_id: str = Field(index=True, default=None, max_length=100)
    username: str | None = Field(index=True, default=None, max_length=100)
    avatar_link: str | None = Field(index=True, default=None, max_length=100)
    first_site_login: datetime | None = Field(index=True, default=None)
    last_site_login: datetime | None = Field(index=True, default=None)
    display_name: str | None = Field(index=True, default=None, max_length=100)
    display_name_last_changed: datetime | None = Field(index=True, default=None)
    can_use_site: bool | None = Field(index=True, default=None)
    can_add_games: bool | None = Field(index=True, default=None)

    api_keys: list["ApiKey"] | None = Relationship(back_populates="user")

    def order(self):
        return {
            "id": self.id, "discord_id": self.discord_id, "username": self.username, "avatar_link": self.avatar_link,
            "first_site_login": self.first_site_login, "last_site_login": self.last_site_login, "display_name": self.display_name,
            "display_name_last_changed": self.display_name_last_changed, "can_use_site": self.can_use_site, "can_add_games": self.can_add_games
        }


class ApiKey(SQLModel, table=True):
    __tablename__ = "api_keys"
    id: int = Field(primary_key=True, index=True)
    key: str = Field(index=True, default=None, max_length=255, unique=True)

    user_id: int | None = Field(default=None, foreign_key="users.id")
    user: User | None = Relationship(back_populates="api_keys")
    

# Servers
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
    __tablename__ = "server_categories"
    id: int = Field(primary_key=True, index=True)
    name: str | None = Field(index=True, default=None, max_length=25)
    icon: str | None = Field(index=True, default=None, max_length=45)
    color: str | None = Field(index=True, default=None, max_length=25)
    is_minecraft: bool | None = Field(index=True, default=None)

    def order(self):
        return {"id": self.id, "name": self.name, "icon": self.icon, "color": self.color, "is_minecraft": self.is_minecraft}