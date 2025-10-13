# Module Imports
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Optional, List, Literal
from sqlmodel import SQLModel, Float, Field, Relationship
import sqlalchemy as sa
from sqlalchemy import JSON
from sqlalchemy.ext.mutable import MutableList
from pydantic import field_validator
from schemas.users import UserPublicShort


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
    blackjack_games: Optional[list["BlackjackGame"]] = Relationship(back_populates="currency")


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


class CurrencyPublicShort(SQLModel):
    id: int
    name: str
    display_name: str
    prefix: Optional[str]


class FilterCurrency(SQLModel):
    page: Optional[int] = 1
    per_page: Optional[int] = 50
    can_gamble: Optional[bool] = None
    can_exchange: Optional[bool] = None
    can_work_for: Optional[bool] = None
    order_by: Optional[Literal["id", "name", "display_name"]] = "id"
    order_dir: Optional[Literal["asc", "desc"]] = "asc"


# UserCurrency
class UserCurrency(SQLModel, table=True):
    __tablename__ = "user_currencies"
    id: Optional[int] = Field(primary_key=True, index=True)

    user_id: int = Field(sa_column=sa.Column(sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE")))
    user: "User" = Relationship(back_populates="balances")

    currency_id: int = Field(sa_column=sa.Column(sa.Integer, sa.ForeignKey("currencies.id", ondelete="CASCADE")))
    currency: "Currency" = Relationship(back_populates="balances")

    balance: float = Field(sa_column=sa.Column(Float()))


class UserCurrencyPublic(SQLModel):
    id: int
    user: UserPublicShort
    currency: CurrencyPublicShort
    balance: float
    

class UserCurrencyLeaderboard(SQLModel):
    currency: CurrencyPublic
    user_currencies: Optional[list[UserCurrencyPublic]]


class FilterUserCurrency(SQLModel):
    page: Optional[int] = 1
    per_page: Optional[int] = 50
    user_id: Optional[int] = None
    currency_id: Optional[int] = None
    order_by: Optional[Literal["id", "user_id", "currency_id"]] = "id"
    order_dir: Optional[Literal["asc", "desc"]] = "asc"


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

    user_jobs: Optional[list["UserJob"]] = Relationship(back_populates="job")


class JobPublic(SQLModel):
    id: int
    name: str
    display_name: str
    min_pay: float
    max_pay: float
    cooldown: float
    overridden_currency_id: Optional[int]


class FilterJob(SQLModel):
    page: Optional[int] = 1
    per_page: Optional[int] = 50
    order_by: Optional[Literal["id", "name", "display_name", "min_pay", "max_pay", "cooldown"]] = "id"
    order_dir: Optional[Literal["asc", "desc"]] = "asc"


# UserJob
class UserJob(SQLModel, table=True):
    __tablename__ = "user_jobs"
    id: Optional[int] = Field(primary_key=True, index=True)

    user_id: int = Field(sa_column=sa.Column(sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE")))
    user: "User" = Relationship(back_populates="job")

    job_id: int = Field(sa_column=sa.Column(sa.Integer, sa.ForeignKey("jobs.id", ondelete="CASCADE")))
    job: "Job" = Relationship(back_populates="user_jobs")

    currency_id: int = Field(sa_column=sa.Column(sa.Integer, sa.ForeignKey("currencies.id", ondelete="CASCADE")))
    currency: "Currency" = Relationship(back_populates="user_jobs")


class UserJobPublic(SQLModel):
    id: int
    user: UserPublicShort
    job: JobPublic
    currency: CurrencyPublic


class FilterUserJob(SQLModel):
    page: Optional[int] = 1
    per_page: Optional[int] = 50
    user_id: Optional[int] = None
    job_id: Optional[int] = None
    currency: Optional[int] = None
    order_by: Optional[Literal["id", "user_id", "job_id", "currency_id"]] = "id"
    order_dir: Optional[Literal["asc", "desc"]] = "asc"


# Cooldown
class Cooldown(SQLModel, table=True):
    __tablename__ = "cooldowns"
    id: Optional[int] = Field(primary_key=True, index=True)

    user_id: int = Field(sa_column=sa.Column(sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE")))
    user: "User" = Relationship(back_populates="cooldowns")

    expires: datetime= Field(sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False))
    cooldown_type: str = Field(index=True, max_length=30)


# Currency Exchange
class CurrencyExchange(SQLModel):
    currency_from_id: int
    currency_to_id: int
    amount: float

    @field_validator("amount")
    def validate_amount(cls, value: float) -> float:
        if value < 0:
            raise ValueError("Amount must be greater than 0")
        return value


# Gift
class Gift(SQLModel):
    user_id: Optional[int] = None
    discord_id: Optional[str] = None
    currency_id: int
    amount: float

    @field_validator("amount")
    def validate_amount(cls, value: float) -> float:
        if value < 0:
            raise ValueError("Amount must be greater than 0")
        return value
    

# Blackjack
class BlackjackGame(SQLModel, table=True):
    __tablename__ = "blackjack_games"
    id: Optional[int] = Field(primary_key=True, index=True)
    code: str = Field(index=True, max_length=36)

    user_id: int = Field(sa_column=sa.Column(sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE")))
    user: "User" = Relationship(back_populates="blackjack_games")

    user_hand: List[str] = Field(sa_column=sa.Column(MutableList.as_mutable(JSON), nullable=False,))
    user_hand_value: int = Field(index=True)
    dealer_hand: List[str] = Field(sa_column=sa.Column(MutableList.as_mutable(JSON), nullable=False))
    dealer_hand_value: int = Field(index=True)

    currency_id: int = Field(sa_column=sa.Column(sa.Integer, sa.ForeignKey("currencies.id", ondelete="SET NULL")))
    currency: "Currency" = Relationship(back_populates="blackjack_games")

    bet: float = Field(sa_column=sa.Column(Float()))
    result: Optional[str] = Field(index=True, max_length=4)
    result_text: Optional[str] = Field(index=True, max_length=300)


class BlackjackGamePublic(SQLModel):
    id: int
    code: str
    user: UserPublicShort
    user_hand: List[str]
    user_hand_value: int
    dealer_hand: List[str]
    dealer_hand_value: int
    currency: CurrencyPublicShort
    bet: float
    result: Optional[str]
    result_text: Optional[str]


class BlackjackGameUpdate(SQLModel):
    currency_id: Optional[int] = None
    bet: Optional[float] = None
    code: Optional[str] = None
    action: Optional[str] = None

    @field_validator("bet")
    def validate_bet(cls, value: str) -> float:
        if value and value < 0:
            raise ValueError("Bet must be greater that 0'")
        return value

    @field_validator("action")
    def validate_action(cls, value: str) -> float:
        if value and value not in ["Hit", "Stand"]:
            raise ValueError("Action must either be 'Hit' or 'Stand'")
        return value
