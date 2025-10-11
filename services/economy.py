# Module Imports
import logging
from datetime import datetime, timezone
from sqlmodel import Session, select
from schemas.database import engine
from schemas.economy import Currency, UserCurrency
from schemas.users import User


logger = logging.getLogger("services")

# Services
# Populate user currencies
def populate_user_currencies(user: User) -> None:
    with Session(engine) as session:
        db_currencies = session.exec(select(Currency)).all()
        for currency in db_currencies:
            filtered_user_currency = [user_currency for user_currency in user.balances if user_currency.currency == currency]
            if not filtered_user_currency:
                db_currency = UserCurrency(user_id=user.id, currency_id=currency.id, balance=currency.starting_value)
                session.add(db_currency)
        session.commit()

# Ensure a datetime object has utc information
def ensure_aware(time: datetime):
    return time.replace(tzinfo=timezone.utc)

# Populate currencies for all existing users
def populate_all_user_currencies():
    with Session(engine) as session:
        db_users = session.exec(select(User)).all()
        for user in db_users:
            populate_user_currencies(user)
