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
            if currency not in user.balances:
                db_currency = UserCurrency(user_id=user.id, currency_id=currency.id, balance=currency.starting_value)
                session.add(db_currency)
        session.commit()

# Ensure a datetime object has utc information
def ensure_aware(time: datetime):
    return time.replace(tzinfo=timezone.utc)
