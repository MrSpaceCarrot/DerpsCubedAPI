# Module Imports
import random
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends
from sqlmodel import Session, select
from sqlalchemy import func
from auth.security import Authenticator, get_current_user
from schemas.database import get_session
from schemas.economy import Currency, CurrencyPublic, UserCurrency, UserCurrencyPublic, Job, JobPublic, UserJob, UserJobPublic, Cooldown
from schemas.users import User
from services.economy import ensure_aware

router = APIRouter()

# Get all currencies
@router.get("/currencies", tags=["economy"], response_model=list[CurrencyPublic], dependencies=[Depends(Authenticator(True, True))])
def get_all_currencies(session: Session = Depends(get_session)):
    return session.exec(select(Currency).order_by(Currency.id.asc())).all()

# Get all balances
@router.get("/balances", tags=["economy"], response_model=list[UserCurrencyPublic], dependencies=[Depends(Authenticator(True, True))])
def get_all_balances(session: Session = Depends(get_session)):
    return session.exec(select(UserCurrency).order_by(UserCurrency.id.asc())).all()

# Get current user's balance
@router.get("/balances/me", tags=["economy"], response_model=list[UserCurrencyPublic])
def get_current_user_balances(current_user: User =  Depends(get_current_user), session: Session = Depends(get_session)):
    return session.exec(select(UserCurrency).where(UserCurrency.user_id == current_user.id).order_by(UserCurrency.id.asc())).all()

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
        raise HTTPException(status_code=status.HTTP_200_OK, detail=f"You already have a job")
    
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
    return f"You quit your previous job of being a {old_job_name}. You can apply for another job in 300s"

# Work Job
@router.post("/jobs/work", tags=["economy"])
def work_job(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    current_user = session.merge(current_user)
    # Check job
    if not current_user.job:
        raise HTTPException(status_code=status.HTTP_200_OK, detail=f"You cannot work without a job")
    
    # Check cooldown
    for cooldown in current_user.cooldowns:
        if cooldown.cooldown_type == "work" and ensure_aware(cooldown.expires) > datetime.now(timezone.utc):
            expires_in = ensure_aware(cooldown.expires) - datetime.now(timezone.utc)
            raise HTTPException(status_code=status.HTTP_200_OK, detail=f"You can work again in {expires_in.seconds}s")
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
    response_string = f"You went to work and were paid {currency_prefix}{round(pay_amount, currency_paid.decimal_places)} {currency_paid.display_name}. You may work again in {job.cooldown:.0f}s."

    # Send response
    return response_string

# Get job for a specific user
@router.get("/jobs/{user_id}", tags=["economy"], response_model=UserJobPublic | None, dependencies=[Depends(Authenticator(True, True))])
def get_user_job(user_id: int, session: Session = Depends(get_session)):
    db_user = session.exec(select(User).where(User.id == user_id)).first()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return session.exec(select(UserJob).where(UserJob.user_id == user_id)).first()


# Exchange currency (confirmation should take place on frontend)

# Gift Currency

# Currency Leaderboard

# Get Currency Exchange Rates

# Blackjack
