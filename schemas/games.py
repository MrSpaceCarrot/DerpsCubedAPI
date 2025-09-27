# Module Imports
from typing import TYPE_CHECKING, Optional, Dict, Any, List, ClassVar
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
import sqlalchemy as sa

if TYPE_CHECKING:
    from schemas.users import User


# Schemas
class GameBase(SQLModel):
    name: str = Field(..., index=True, max_length=100)
    platform: str = Field(..., index=True, max_length=10)
    link: str = Field(..., index=True, max_length=300)
    min_party_size: int = Field(..., index=True)
    max_party_size: int = Field(..., index=True)
    tags: List[str] = Field(..., sa_column=sa.Column(sa.JSON, nullable=False))


class Game(GameBase, table=True):
    __tablename__ = "games"
    id: Optional[int] = Field(primary_key=True, index=True, default=None)
    install_size: Optional[int] = Field(index=True, default=None)
    banner_link: str = Field(index=True, default=None, max_length=300)
    last_updated: Optional[datetime] = Field(index=True, default=None)
    date_added: datetime = Field(index=True, default=None)

    added_by_id: Optional[int] = Field(default=None, sa_column=sa.Column(sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True))
    added_by: Optional["User"] = Relationship(back_populates="games_added")

    update_banner_link: bool = Field(index=True, default=True)
    average_rating: Optional[float] = Field(index=True, default=None)
    popularity_score: Optional[float] = Field(index=True, default=None)

    ratings: Optional[list["GameRating"]] = Relationship(back_populates="game")


class GamePublic(GameBase):
    id: int
    install_size: Optional[int]
    banner_link: str
    last_updated: Optional[datetime]
    date_added: datetime
    added_by_id: Optional[int]
    update_banner_link: bool
    average_rating: Optional[float]
    popularity_score: Optional[float]
        

class GameUpdate(GameBase):
    name: Optional[str]
    platform: Optional[str]
    install_size: Optional[int]
    link: Optional[str]
    banner_link: Optional[str]
    min_party_size: Optional[int]
    max_party_size: Optional[int]
    tags: Optional[List[str]]
    update_banner_link: Optional[bool]


class GameTag(SQLModel, table=True):
    __tablename__ = "game_tags"
    id: int = Field(primary_key=True, index=True)
    name: str = Field(index=True, default=None, max_length=50)

    def order(self):
        return {
            "id": self.id, 
            "name": self.name
        }


class GameRating(SQLModel, table=True):
    __tablename__ = "game_ratings"
    id: int = Field(primary_key=True, index=True)

    game_id: int = Field(default=None, sa_column=sa.Column(sa.Integer, sa.ForeignKey("games.id", ondelete="CASCADE"), nullable=False))
    game: "Game" = Relationship(back_populates="ratings")

    user_id: int = Field(default=None, sa_column=sa.Column(sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False))
    user: "User" = Relationship(back_populates="ratings")

    rating: int = Field(index=True, default=None)
    date_added: datetime = Field(index=True, default=None)

    def order(self):
        return {
            "id": self.id, 
            "game": self.game,
            "user": self.user,
            "rating": self.rating,
            "date_added": self.date_added
        }
