# Module Imports
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends
from sqlmodel import Session, select
from auth.security import Authenticator, get_current_user
from schemas.database import get_session
from schemas.economy import Currency, CurrencyPublic, UserCurrency, UserCurrencyPublic, Job, JobPublic, UserJob
from schemas.users import User

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
@router.get("/jobs/me", tags=["economy"], response_model=Optional[list[JobPublic]])
def get_current_user_job(current_user: User =  Depends(get_current_user), session: Session = Depends(get_session)):
    return session.exec(select(UserJob).where(UserJob.user_id == current_user.id)).first()

# Get job for a specific user
@router.get("/jobs/{user_id}", tags=["economy"], response_model=JobPublic | None, dependencies=[Depends(Authenticator(True, True))])
def get_user_job(user_id: int, session: Session = Depends(get_session)):
    db_user = session.exec(select(User).where(User.id == user_id)).first()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return session.exec(select(UserJob).where(UserJob.user_id == user_id)).first()

# Get Job

# Work

# Quit Job

# Exchange currency (confirmation should take place on frontend)

# Gift Currency

# Currency Leaderboard

# Get Currency Exchange Rates

# Blackjack
