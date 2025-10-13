# Module Imports
import logging
import validators
from typing import TYPE_CHECKING, Optional, List, Literal
from typing_extensions import Self
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
import sqlalchemy as sa
from pydantic import field_validator, model_validator
from config import settings


if TYPE_CHECKING:
    from schemas.users import User

logger = logging.getLogger("services")

# Schemas
# Game
class GameBase(SQLModel):
    name: str = Field(..., index=True, max_length=100)
    platform: str = Field(..., index=True, max_length=6)
    link: str = Field(..., index=True, max_length=300)
    banner_link: Optional[str] = None
    min_party_size: int = Field(..., index=True)
    max_party_size: int = Field(..., index=True)
    tags: List[str] = Field(..., sa_column=sa.Column(sa.JSON, nullable=False))

    @field_validator("platform")
    def validate_platform(cls, value: str) -> str:
        if value and value not in ["Roblox", "Steam", "Party", "Other"]:
            raise ValueError("Must be either 'Roblox', 'Steam', 'Party', or 'Other'")
        return value
    
    @field_validator("link")
    def validate_link(cls, value: str) -> str:
        if value and not validators.url(value):
            raise ValueError("Invalid game link")
        return value
    
    @field_validator("banner_link")
    def validate_banner_link(cls, value: str) -> str:
        if value and not validators.url(value):
            raise ValueError("Invalid banner link")
        return value
    
    @field_validator("min_party_size")
    def validate_min_party_size(cls, value: str) -> str:
        if value and (value < 1 or value > 16):
            raise ValueError("Must be between 1 and 16")
        return value
    
    @field_validator("max_party_size")
    def validate_max_party_size(cls, value: str) -> str:
        if value and (value < 1 or value > 16):
            raise ValueError("Must be between 1 and 16")
        return value
    
    @field_validator("tags")
    def validate_tags(cls, value: str) -> str:
        if value and (len(value) < 2 or len(value) > 5):
            raise ValueError("Number of tags must be between 2 and 5")
        return sorted(value)
        
    @model_validator(mode="after")
    def validate(self) -> Self:
        if (self.min_party_size and self.max_party_size) and (self.min_party_size > self.max_party_size or self.max_party_size < self.min_party_size):
            raise ValueError("min_party_size must be smaller than max_party_size")
        
        if self.platform in ["Party", "Other"] and not self.banner_link:
            raise ValueError("A banner link must be provided for 'Party' and 'Other' games")
        return self


class Game(GameBase, table=True):
    __tablename__ = "games"
    id: Optional[int] = Field(primary_key=True, index=True, default=None)
    install_size: Optional[int] = Field(index=True, default=None)
    banner_link: Optional[str] = Field(index=True, default=None, max_length=300)
    banner_image: Optional[str] = Field(index=True, default=None, max_length=100)
    last_updated: Optional[datetime] = Field(index=True, default=None)
    date_added: datetime = Field(index=True, default=None)

    added_by_id: Optional[int] = Field(default=None, sa_column=sa.Column(sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True))
    added_by: Optional["User"] = Relationship(back_populates="games_added")

    update_banner_link: bool = Field(index=True, default=True)
    average_rating: Optional[float] = Field(index=True, default=None)
    popularity_score: Optional[float] = Field(index=True, default=None)

    ratings: Optional[list["GameRating"]] = Relationship(back_populates="game")


class GamePublic(SQLModel):
    id: int
    name: str
    platform: str
    install_size: Optional[int]
    link: str
    banner_link: Optional[str]
    banner_image: Optional[str]
    min_party_size: int
    max_party_size: int
    tags: List[str]
    last_updated: Optional[datetime]
    date_added: datetime
    added_by_id: Optional[int]
    update_banner_link: bool
    average_rating: Optional[float]
    popularity_score: Optional[float]

    @field_validator("banner_image")
    def validate_banner_image(cls, value: str) -> str:
        if value and not value.startswith("http"):
            return f"{settings.STORAGE_BUCKET_MEDIA_URL}/{settings.STORAGE_BUCKET_NAME}/{value}"
        return value


class GameCreate(GameBase):
    pass


class GameUpdate(GameBase):
    name: Optional[str] = None
    platform: Optional[str] = None
    install_size: Optional[int] = None
    link: Optional[str] = None
    banner_link: Optional[str] = None
    min_party_size: Optional[int] = None
    max_party_size: Optional[int] = None
    tags: Optional[List[str]] = None
    update_banner_link: Optional[bool] = None


class FilterGame(SQLModel):
    page: Optional[int] = 1
    per_page: Optional[int] = 50
    name: Optional[str] = None
    platform: Optional[str] = None
    added_by_id: Optional[int] = None
    order_by: Optional[Literal["id", "name", "platform", "min_party_size", "max_party_size", "last_updated", "date_added", "average_rating", "popularity_score", "random"]] = "id"
    order_dir: Optional[Literal["asc", "desc"]] = "asc"


# GameTag
class GameTag(SQLModel, table=True):
    __tablename__ = "game_tags"
    id: int = Field(primary_key=True, index=True)
    name: str = Field(index=True, default=None, max_length=50)


class FilterGameTag(SQLModel):
    page: Optional[int] = 1
    per_page: Optional[int] = 100
    order_by: Optional[Literal["id", "name"]] = "id"
    order_dir: Optional[Literal["asc", "desc"]] = "asc"


# GameRating
class GameRating(SQLModel, table=True):
    __tablename__ = "game_ratings"
    id: Optional[int] = Field(primary_key=True, index=True, default=None)

    game_id: int = Field(..., sa_column=sa.Column(sa.Integer, sa.ForeignKey("games.id", ondelete="CASCADE"), nullable=False))
    game: "Game" = Relationship(back_populates="ratings")

    user_id: int = Field(..., sa_column=sa.Column(sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False))
    user: "User" = Relationship(back_populates="ratings")

    rating: int = Field(..., index=True)
    last_updated: datetime = Field(index=True, default=None)


class GameRatingPublic(SQLModel):
    id: int
    game_id: int
    user_id: int
    rating: int
    last_updated: datetime


class GameRatingUpdate(SQLModel):
    game_id: int
    rating: int

    @field_validator("rating")
    def validate_rating(cls, value: int) -> int:
        if value and (value < -1 or value > 10):
            raise ValueError("Rating must be between 1 and 10, 0 for unrated, -1 for ignored")
        return value


class FilterGameRating(SQLModel):
    page: Optional[int] = 1
    per_page: Optional[int] = 50
    game_id: Optional[int] = None
    user_id: Optional[int] = None
    rating: Optional[int] = None
    order_by: Optional[Literal["id", "game_id", "user_id", "rating"]] = "id"
    order_dir: Optional[Literal["asc", "desc"]] = "asc"
