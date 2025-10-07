# Module Imports
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlmodel import SQLModel, Float, Field, Relationship
import sqlalchemy as sa


if TYPE_CHECKING:
    from schemas.users import User

logger = logging.getLogger("services")

# Schemas
# Currency
class Currency(SQLModel, table=True):
    __tablename__ = "currencies"
    id: Optional[int] = Field(primary_key=True, index=True)
    name: str = Field(index=True, max_length=30)
    display_name: str = Field(index=True, max_length=30)
    prefix: Optional[str] = Field(index=True, max_length=1)
    can_gamble: bool = Field(index=True)
    can_exchange: bool = Field(index=True)
    can_work_for: bool = Field(index=True)
    exchange_rate: Optional[float] = Field(index=True)
    decimal_places: int = Field(index=True)
    value_multiplier: float = Field(index=True)
    starting_value: float = Field(index=True)
    color: str = Field(index=True, max_length=7)

    balances: Optional[list["UserCurrency"]] = Relationship(back_populates="currency")
    jobs: Optional[list["Job"]] = Relationship(back_populates="overridden_currency")
    user_jobs: Optional[list["UserJob"]] = Relationship(back_populates="currency")


class CurrencyPublic(SQLModel):
    id: int
    name: str
    display_name: str
    prefix: Optional[str]
    can_gamble: bool
    can_exchange: bool
    can_work_for: bool
    exchange_rate: Optional[float]
    decimal_places: int
    value_multiplier: float
    starting_value: float
    color: str


# UserCurrency
class UserCurrency(SQLModel, table=True):
    __tablename__ = "user_currencies"
    id: Optional[int] = Field(primary_key=True, index=True)

    user_id: int = Field(sa_column=sa.Column(sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE")))
    user: "User" = Relationship(back_populates="balances")

    currency_id: int = Field(sa_column=sa.Column(sa.Integer, sa.ForeignKey("currencies.id", ondelete="CASCADE")))
    currency: "Currency" = Relationship(back_populates="balances")

    balance: float = Field(sa_column=sa.Column(Float(precision=53)))


class UserCurrencyPublic(SQLModel):
    id: int
    user_id: int
    currency_id: int
    balance: int


# Job
class Job(SQLModel, table=True):
    __tablename__ = "jobs"
    id: Optional[int] = Field(primary_key=True, index=True)
    name: str = Field(index=True, max_length=30)
    display_name: str = Field(index=True, max_length=30)
    min_pay: float = Field(index=True)
    max_pay: float = Field(index=True)
    cooldown: float = Field(index=True)

    overridden_currency_id: Optional[int] = Field(sa_column=sa.Column(sa.Integer, sa.ForeignKey("currencies.id", ondelete="SET NULL"), nullable=True))
    overridden_currency: Optional["Currency"] = Relationship(back_populates="jobs")


class JobPublic(SQLModel):
    id: int
    name: str
    display_name: str
    min_pay: float
    max_pay: float
    cooldown: float
    overridden_currency_id: Optional[int]


# UserJob
class UserJob(SQLModel, table=True):
    __tablename__ = "user_jobs"
    id: Optional[int] = Field(primary_key=True, index=True)

    user_id: int = Field(sa_column=sa.Column(sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE")))
    user: "User" = Relationship(back_populates="job")

    currency_id: int = Field(sa_column=sa.Column(sa.Integer, sa.ForeignKey("currencies.id", ondelete="CASCADE")))
    currency: "Currency" = Relationship(back_populates="user_jobs")


class UserJobPublic(SQLModel):
    id: int
    user_id: int
    currency_id: int


# Cooldown
class Cooldown(SQLModel, table=True):
    __tablename__ = "cooldowns"
    id: Optional[int] = Field(primary_key=True, index=True)

    user_id: int = Field(sa_column=sa.Column(sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE")))
    user: "User" = Relationship(back_populates="cooldown")

    expires: datetime = Field(index=True)
    cooldown_type: str = Field(index=True, max_length=30)
