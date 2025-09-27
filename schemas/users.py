# Module Imports
from typing import TYPE_CHECKING, Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from schemas.auth import ApiKey
    from schemas.games import Game


# Schemas
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
    can_add_games: Optional[bool] = Field(index=True, default=None)

    api_keys: Optional[list["ApiKey"]] = Relationship(back_populates="user")
    games_added: List["Game"] = Relationship(back_populates="added_by")

    def order(self):
        return {
            "id": self.id, "discord_id": self.discord_id, "username": self.username, "avatar_link": self.avatar_link,
            "first_site_login": self.first_site_login, "last_site_login": self.last_site_login, "display_name": self.display_name,
            "display_name_last_changed": self.display_name_last_changed, "can_use_site": self.can_use_site, "can_add_games": self.can_add_games
        }
