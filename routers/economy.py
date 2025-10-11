# Module Imports
import random
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends
from sqlmodel import Session, select
from sqlalchemy import func
from auth.security import Authenticator, get_current_user
from schemas.database import get_session
from schemas.economy import *
from schemas.users import User
from services.economy import ensure_aware
from services.users import get_or_create_user

router = APIRouter()

# Get all currencies
@router.get("/currencies", tags=["economy"], response_model=list[CurrencyPublic], dependencies=[Depends(Authenticator(True, True))])
def get_all_currencies(session: Session = Depends(get_session)):
    return session.exec(select(Currency).order_by(Currency.id.asc())).all()

# Exchange currency
@router.post("/currencies/exchange", tags=["economy"])
def exchange_currency(currency_exchange: CurrencyExchange, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    current_user = session.merge(current_user)
    # Validate currency from
    currency_from = session.get(Currency, currency_exchange.currency_from_id)
    if not currency_from:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Currency from not found")
    if not currency_from.can_exchange:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"You cannot exchange {currency_from.display_name}")

    # Validate currency to
    currency_to = session.get(Currency, currency_exchange.currency_to_id)
    if not currency_to:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Currency to not found")
    if not currency_to.can_exchange:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"You cannot exchange to {currency_to.display_name}")
    
    # Ensure both currencies are not the same
    if currency_from == currency_to:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"You cannot convert {currency_from.display_name} into {currency_to.display_name}")
    
    # Get user balances
    user_currency_from = session.exec(select(UserCurrency).where(UserCurrency.user_id == current_user.id, UserCurrency.currency_id == currency_from.id)).first()
    user_currency_to = session.exec(select(UserCurrency).where(UserCurrency.user_id == current_user.id, UserCurrency.currency_id == currency_to.id)).first()

    # Check that user has enough balance of given currency
    if user_currency_from.balance < currency_exchange.amount:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Insufficent {currency_from.display_name} balance (have {currency_from.prefix}{user_currency_from.balance:.{currency_from.decimal_places}f}, need {currency_from.prefix}{currency_exchange.amount:.{currency_from.decimal_places}f})")

    # Calculate exchange rate between currencies
    relative_rate = currency_from.exchange_rate / currency_to.exchange_rate
    currency_to_amount_gained = currency_exchange.amount * relative_rate

    # Update user balances
    user_currency_from.balance -= currency_exchange.amount
    user_currency_to.balance += currency_to_amount_gained
    session.add(user_currency_from, user_currency_to)
    session.commit()
    session.refresh(user_currency_from, user_currency_to)

    # Return
    return f"Converted {currency_from.prefix}{currency_exchange.amount:.{currency_from.decimal_places}f} into {currency_to.prefix}{currency_to_amount_gained:.{currency_to.decimal_places}f}. Your {currency_from.display_name} balance is now {currency_from.prefix}{user_currency_from.balance:.{currency_from.decimal_places}f}. Your {currency_to.display_name} balance is now {currency_to.prefix}{user_currency_to.balance:.{currency_to.decimal_places}f}"
    
# Get all balances
@router.get("/balances", tags=["economy"], response_model=list[UserCurrencyPublic], dependencies=[Depends(Authenticator(True, True))])
def get_all_balances(session: Session = Depends(get_session)):
    return session.exec(select(UserCurrency).order_by(UserCurrency.id.asc())).all()

# Get current user's balance
@router.get("/balances/me", tags=["economy"], response_model=list[UserCurrencyPublic])
def get_current_user_balances(current_user: User =  Depends(get_current_user), session: Session = Depends(get_session)):
    return session.exec(select(UserCurrency).where(UserCurrency.user_id == current_user.id).order_by(UserCurrency.id.asc())).all()

# Get leaderboard for a given currency
@router.get("/balances/leaderboard/{id}", tags=["economy"], response_model=UserCurrencyLeaderboard, dependencies=[Depends(Authenticator(True, True))])
def get_balances_leaderboard(currency_id: int, session: Session = Depends(get_session)):
    db_currency = session.exec(select(Currency).where(Currency.id == currency_id)).first()
    if not db_currency:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Currency not found")
    db_user_currencies = session.exec(select(UserCurrency).where(UserCurrency.currency_id == currency_id).order_by(UserCurrency.balance.desc())).all()
    return UserCurrencyLeaderboard(currency=db_currency, user_currencies=db_user_currencies)

# Gift Currency
@router.post("/balances/gift", tags=["economy"])
def gift(gift: Gift, current_user: User =  Depends(get_current_user), session: Session = Depends(get_session)):
    current_user: User = session.merge(current_user)

    # Get target user using either discord_id or id
    if gift.discord_id:
        db_recieving_user: User = get_or_create_user(gift.discord_id)
    elif gift.user_id:
        db_recieving_user: User = session.get(User, gift.user_id)
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Either a id or discord_id of a user must be provided")
    
    # Validate gift currency
    db_currency: Currency = session.get(Currency, gift.currency_id)
    if not db_currency:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Currency not found")
    
    # Check that currency can be gifted
    if not db_currency.can_exchange:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This currency cannot be gifted")
    
    # Get user balances for currency being gifted
    db_sending_user_currency: UserCurrency = session.exec(select(UserCurrency).where(UserCurrency.user_id == current_user.id, UserCurrency.currency_id == gift.currency_id)).first()
    db_recieving_user_currency: UserCurrency = session.exec(select(UserCurrency).where(UserCurrency.user_id == db_recieving_user.id, UserCurrency.currency_id == gift.currency_id)).first()

    # Check if enough currency
    if db_sending_user_currency.balance < gift.amount:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Insufficent {db_currency.display_name} balance (have {db_currency.prefix}{db_sending_user_currency.balance:.{db_currency.decimal_places}f}, need {db_currency.prefix}{gift.amount:.{db_currency.decimal_places}f})")

    # Change balances
    db_sending_user_currency.balance -= gift.amount
    db_recieving_user_currency.balance += gift.amount
    session.add(db_sending_user_currency, db_recieving_user_currency)
    session.commit()
    session.refresh(db_sending_user_currency, db_recieving_user_currency)

    # Return
    return f"You have gifted {db_currency.prefix}{gift.amount:.{db_currency.decimal_places}f} {db_currency.display_name} to {db_recieving_user.discord_id}. Your {db_currency.display_name} balance is now {db_currency.prefix}{db_sending_user_currency.balance:.{db_currency.decimal_places}f}"

# Get balances for a specific user
@router.get("/balances/{user_id}", tags=["economy"], response_model=list[UserCurrencyPublic], dependencies=[Depends(Authenticator(True, True))])
def get_user_balances(user_id: int, session: Session = Depends(get_session)):
    db_user = session.exec(select(User).where(User.id == user_id)).first()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return session.exec(select(UserCurrency).where(UserCurrency.user_id == user_id).order_by(UserCurrency.id.asc())).all()

# Get all jobs
@router.get("/jobs", tags=["economy"], response_model=list[JobPublic], dependencies=[Depends(Authenticator(True, True))])
def get_all_jobs(session: Session = Depends(get_session)):
    return session.exec(select(Job).order_by(Job.id.asc())).all()

# Get current user's job
@router.get("/jobs/me", tags=["economy"], response_model=Optional[UserJobPublic])
def get_current_user_job(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    return session.exec(select(UserJob).where(UserJob.user_id == current_user.id)).first()

# Apply for job
@router.post("/jobs/apply", tags=["economy"], response_model=Optional[UserJobPublic])
def apply_for_job(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    current_user = session.merge(current_user)
    # Check existing job
    if current_user.job:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"You already have a job")
    
    # Check cooldown
    for cooldown in current_user.cooldowns:
        if cooldown.cooldown_type == "job_change" and ensure_aware(cooldown.expires) > datetime.now(timezone.utc):
            expires_in = ensure_aware(cooldown.expires) - datetime.now(timezone.utc)
            raise HTTPException(status_code=status.HTTP_200_OK, detail=f"You can apply for another job in {expires_in.seconds}s")
        session.delete(cooldown)

    # Generate random job
    db_random_job = session.exec(select(Job).order_by(func.random())).first()
    if db_random_job.overridden_currency:
        currency_id = db_random_job.overridden_currency_id
    else:
        currency_id = session.exec(select(Currency).where(Currency.can_work_for == True).order_by(func.random())).first().id
    db_user_job = UserJob(user_id=current_user.id, currency_id=currency_id, job_id=db_random_job.id)

    # Return job
    session.add(db_user_job)
    session.commit()
    session.refresh(db_user_job)
    return db_user_job

# Quit job
@router.post("/jobs/quit", tags=["economy"])
def quit_job(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    current_user = session.merge(current_user)

    # Ensure job exists
    if not current_user.job:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You do not have a job you can quit")
    
    # Create cooldown
    db_change_job_cooldown = Cooldown(user_id=current_user.id, expires=datetime.now(timezone.utc) + timedelta(seconds=300), cooldown_type="job_change")
    session.add(db_change_job_cooldown)

    # Remove old work cooldown
    for cooldown in current_user.cooldowns:
        if cooldown.cooldown_type == "work":
            session.delete(cooldown)
    
    # Delete job
    old_job_name = current_user.job.job.display_name
    session.delete(current_user.job)
    session.commit()
    return f"You quit your previous job of {old_job_name}. You can apply for another job in 300s"

# Work Job
@router.post("/jobs/work", tags=["economy"])
def work_job(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    current_user = session.merge(current_user)
    # Check job
    if not current_user.job:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"You cannot work without a job")
    
    # Check cooldown
    for cooldown in current_user.cooldowns:
        if cooldown.cooldown_type == "work" and ensure_aware(cooldown.expires) > datetime.now(timezone.utc):
            expires_in = ensure_aware(cooldown.expires) - datetime.now(timezone.utc)
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"You can work again in {expires_in.seconds}s")
        session.delete(cooldown)

    # Pay user
    job = current_user.job.job
    pay_amount = (random.randint(job.min_pay, job.max_pay)) / current_user.job.currency.value_multiplier
    balance = session.exec(select(UserCurrency).where(UserCurrency.user_id == current_user.id, UserCurrency.currency_id == current_user.job.currency_id)).first()
    balance.balance = pay_amount
    session.add(balance)

    # Create cooldown
    work_cooldown = Cooldown(user_id=current_user.id, expires=datetime.now(timezone.utc) + timedelta(seconds=current_user.job.job.cooldown), cooldown_type="work")
    session.add(work_cooldown)
    session.commit()

    # Generate response string
    currency_paid = current_user.job.currency
    currency_prefix = '' if currency_paid.prefix == None else currency_paid.prefix
    response_string = f"You went to work and were paid {currency_prefix}{pay_amount:.{currency_paid.decimal_places}f} {currency_paid.display_name}. You may work again in {job.cooldown:.0f}s."

    # Send response
    return response_string

# Get job for a specific user
@router.get("/jobs/{user_id}", tags=["economy"], response_model=UserJobPublic | None, dependencies=[Depends(Authenticator(True, True))])
def get_user_job(user_id: int, session: Session = Depends(get_session)):
    db_user = session.exec(select(User).where(User.id == user_id)).first()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return session.exec(select(UserJob).where(UserJob.user_id == user_id)).first()


# Get Currency Exchange Rates

# Blackjack
