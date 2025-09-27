# Module Imports
from typing import TYPE_CHECKING, Optional, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
import sqlalchemy as sa

if TYPE_CHECKING:
    from schemas.users import User


# Schemas
class Game(SQLModel, table=True):
    __tablename__ = "games"
    id: int = Field(primary_key=True, index=True)
    name: str = Field(index=True, default=None, max_length=100)
    platform: str = Field(index=True, default=None, max_length=10)
    install_size: Optional[int] = Field(index=True, default=None)
    link: str = Field(index=True, default=None, max_length=300)
    banner_link: str = Field(index=True, default=None, max_length=300)
    min_party_size: int = Field(index=True, default=None)
    max_party_size: int = Field(index=True, default=None)
    tags: Dict[str, Any] = Field(default=None,  sa_column=sa.Column(sa.JSON))
    last_updated: Optional[datetime] = Field(index=True, default=None)
    date_added: datetime = Field(index=True, default=None)
    
    added_by_id: Optional[int] = Field(default=None, sa_column=sa.Column(sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True))
    added_by: Optional["User"] = Relationship(back_populates="games_added")

    update_banner_link: bool = Field(index=True, default=True)
    average_rating: Optional[float] = Field(index=True, default=None)
    popularity_score: Optional[float] = Field(index=True, default=None)
