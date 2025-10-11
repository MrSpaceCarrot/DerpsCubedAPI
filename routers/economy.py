# Module Imports
import uuid
import random
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends
from sqlmodel import Session, select
from sqlalchemy import func
from auth.security import require_permission
from schemas.database import get_session
from schemas.economy import *
from schemas.users import User
from services.economy import ensure_aware, add_cards_to_hand, calculate_blackjack_hand_value
from services.users import get_or_create_user

router = APIRouter()

# Get all currencies
@router.get("/currencies", tags=["economy"], response_model=list[CurrencyPublic], dependencies=[Depends(require_permission("can_use_economy"))])
def get_all_currencies(session: Session = Depends(get_session)):
    return session.exec(select(Currency).order_by(Currency.id.asc())).all()

# Exchange currency
@router.post("/currencies/exchange", tags=["economy"])
def exchange_currency(currency_exchange: CurrencyExchange, current_user: User = Depends(require_permission("can_use_economy")), session: Session = Depends(get_session)):
    current_user: User = session.merge(current_user)
    # Validate currency from
    currency_from: Currency = session.get(Currency, currency_exchange.currency_from_id)
    if not currency_from:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Currency from not found")
    if not currency_from.can_exchange:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"You cannot exchange {currency_from.display_name}")

    # Validate currency to
    currency_to: Currency = session.get(Currency, currency_exchange.currency_to_id)
    if not currency_to:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Currency to not found")
    if not currency_to.can_exchange:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"You cannot exchange to {currency_to.display_name}")
    
    # Ensure both currencies are not the same
    if currency_from == currency_to:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"You cannot convert {currency_from.display_name} into {currency_to.display_name}")
    
    # Get user balances
    user_currency_from: UserCurrency = session.exec(select(UserCurrency).where(UserCurrency.user_id == current_user.id, UserCurrency.currency_id == currency_from.id)).first()
    user_currency_to: UserCurrency = session.exec(select(UserCurrency).where(UserCurrency.user_id == current_user.id, UserCurrency.currency_id == currency_to.id)).first()

    # Check that user has enough balance of given currency
    if user_currency_from.balance < currency_exchange.amount:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Insufficent {currency_from.display_name} balance (have {currency_from.prefix}{user_currency_from.balance:.{currency_from.decimal_places}f}, need {currency_from.prefix}{currency_exchange.amount:.{currency_from.decimal_places}f})")

    # Calculate exchange rate between currencies
    relative_rate: float = currency_from.exchange_rate / currency_to.exchange_rate
    currency_to_amount_gained: float = currency_exchange.amount * relative_rate

    # Update user balances
    user_currency_from.balance -= currency_exchange.amount
    user_currency_to.balance += currency_to_amount_gained
    session.add(user_currency_from, user_currency_to)
    session.commit()
    session.refresh(user_currency_from, user_currency_to)

    # Return
    return f"Converted {currency_from.prefix}{currency_exchange.amount:.{currency_from.decimal_places}f} into {currency_to.prefix}{currency_to_amount_gained:.{currency_to.decimal_places}f}. Your {currency_from.display_name} balance is now {currency_from.prefix}{user_currency_from.balance:.{currency_from.decimal_places}f}. Your {currency_to.display_name} balance is now {currency_to.prefix}{user_currency_to.balance:.{currency_to.decimal_places}f}"
    
# Get all balances
@router.get("/balances", tags=["economy"], response_model=list[UserCurrencyPublic], dependencies=[Depends(require_permission("can_use_economy"))])
def get_all_balances(session: Session = Depends(get_session)):
    return session.exec(select(UserCurrency).order_by(UserCurrency.id.asc())).all()

# Get current user's balance
@router.get("/balances/me", tags=["economy"], response_model=list[UserCurrencyPublic])
def get_current_user_balances(current_user: User = Depends(require_permission("can_use_economy")), session: Session = Depends(get_session)):
    return session.exec(select(UserCurrency).where(UserCurrency.user_id == current_user.id).order_by(UserCurrency.id.asc())).all()

# Get leaderboard for a given currency
@router.get("/balances/leaderboard/{id}", tags=["economy"], response_model=UserCurrencyLeaderboard, dependencies=[Depends(require_permission("can_use_economy"))])
def get_balances_leaderboard(currency_id: int, session: Session = Depends(get_session)):
    db_currency = session.exec(select(Currency).where(Currency.id == currency_id)).first()
    if not db_currency:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Currency not found")
    db_user_currencies = session.exec(select(UserCurrency).where(UserCurrency.currency_id == currency_id).order_by(UserCurrency.balance.desc())).all()
    return UserCurrencyLeaderboard(currency=db_currency, user_currencies=db_user_currencies)

# Gift Currency
@router.post("/balances/gift", tags=["economy"])
def gift(gift: Gift, current_user: User = Depends(require_permission("can_use_economy")), session: Session = Depends(get_session)):
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
@router.get("/balances/{user_id}", tags=["economy"], response_model=list[UserCurrencyPublic], dependencies=[Depends(require_permission("can_use_economy"))])
def get_user_balances(user_id: int, session: Session = Depends(get_session)):
    db_user: User = session.exec(select(User).where(User.id == user_id)).first()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return session.exec(select(UserCurrency).where(UserCurrency.user_id == user_id).order_by(UserCurrency.id.asc())).all()

# Get all jobs
@router.get("/jobs", tags=["economy"], response_model=list[JobPublic], dependencies=[Depends(require_permission("can_use_economy"))])
def get_all_jobs(session: Session = Depends(get_session)):
    return session.exec(select(Job).order_by(Job.id.asc())).all()

# Get current user's job
@router.get("/jobs/me", tags=["economy"], response_model=Optional[UserJobPublic])
def get_current_user_job(current_user: User = Depends(require_permission("can_use_economy")), session: Session = Depends(get_session)):
    return session.exec(select(UserJob).where(UserJob.user_id == current_user.id)).first()

# Apply for job
@router.post("/jobs/apply", tags=["economy"], response_model=Optional[UserJobPublic])
def apply_for_job(current_user: User = Depends(require_permission("can_use_economy")), session: Session = Depends(get_session)):
    current_user: User = session.merge(current_user)
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
    db_random_job: Job = session.exec(select(Job).order_by(func.random())).first()
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
def quit_job(current_user: User = Depends(require_permission("can_use_economy")), session: Session = Depends(get_session)):
    current_user: User = session.merge(current_user)

    # Ensure job exists
    if not current_user.job:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You do not have a job you can quit")
    
    # Create cooldown
    db_change_job_cooldown: Cooldown = Cooldown(user_id=current_user.id, expires=datetime.now(timezone.utc) + timedelta(seconds=300), cooldown_type="job_change")
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
def work_job(current_user: User = Depends(require_permission("can_use_economy")), session: Session = Depends(get_session)):
    current_user: User = session.merge(current_user)
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
    job: Job = current_user.job.job
    pay_amount: float = (random.randint(job.min_pay, job.max_pay)) / current_user.job.currency.value_multiplier
    balance = session.exec(select(UserCurrency).where(UserCurrency.user_id == current_user.id, UserCurrency.currency_id == current_user.job.currency_id)).first()
    balance.balance = pay_amount
    session.add(balance)

    # Create cooldown
    work_cooldown: Cooldown = Cooldown(user_id=current_user.id, expires=datetime.now(timezone.utc) + timedelta(seconds=current_user.job.job.cooldown), cooldown_type="work")
    session.add(work_cooldown)
    session.commit()

    # Generate response string
    currency_paid = current_user.job.currency
    currency_prefix = '' if currency_paid.prefix == None else currency_paid.prefix
    response_string = f"You went to work and were paid {currency_prefix}{pay_amount:.{currency_paid.decimal_places}f} {currency_paid.display_name}. You may work again in {job.cooldown:.0f}s."

    # Send response
    return response_string

# Get job for a specific user
@router.get("/jobs/{user_id}", tags=["economy"], response_model=UserJobPublic | None, dependencies=[Depends(require_permission("can_use_economy"))])
def get_user_job(user_id: int, session: Session = Depends(get_session)):
    db_user: User = session.exec(select(User).where(User.id == user_id)).first()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return session.exec(select(UserJob).where(UserJob.user_id == user_id)).first()

# Blackjack
@router.post("/gambling/blackjack", tags=["economy"], response_model=BlackjackGamePublic)
def blackjack(blackjack_game_update: BlackjackGameUpdate, current_user: User = Depends(require_permission("can_use_economy")), session: Session = Depends(get_session)):
    current_user: User = session.merge(current_user)

    # Get details from request
    blackjack_game_update: BlackjackGameUpdate = BlackjackGameUpdate(**blackjack_game_update.model_dump())

    # If game code was not given (game is just starting)
    if not blackjack_game_update.code:
        # Check that the currency is valid
        db_currency: Currency = session.get(Currency, blackjack_game_update.currency_id)
        if not db_currency:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Currency not found")
        
        # Check that the currency can be gambled
        if not db_currency.can_gamble:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This currency cannot be gambled")
        
        # Check that the user has enough to bet
        db_user_currency: UserCurrency = session.exec(select(UserCurrency).where(UserCurrency.id == db_currency.id)).first()
        if db_user_currency.balance < blackjack_game_update.bet:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Insufficent {db_currency.display_name} balance (have {db_currency.prefix}{db_user_currency.balance:.{db_currency.decimal_places}f}, need {db_currency.prefix}{blackjack_game_update.bet:.{db_currency.decimal_places}f})")

        # Create BlackjackGame
        db_blackjack_game = BlackjackGame(code=str(uuid.uuid4()), user_id=current_user.id, currency_id=db_currency.id, bet=blackjack_game_update.bet)

        # Draw cards
        db_blackjack_game.user_hand = add_cards_to_hand([], 2)
        db_blackjack_game.dealer_hand = add_cards_to_hand([], 2)

    # If game code was given (game is already going)
    else:
        # Verify BlackjackGame
        db_blackjack_game = session.exec(select(BlackjackGame).where(BlackjackGame.code == blackjack_game_update.code)).first()
        if not db_blackjack_game:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blackjack game code is invalid")
        
        # Verify that the game has not already finished
        if db_blackjack_game.result:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This blackjack game has already finished")

        # Verify that an action was given
        if not blackjack_game_update.action:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Action must either be 'Hit' or 'Stand'")
        
        # If user has hit, draw a card. Dealer hits only if their hand is worth less than 17
        if blackjack_game_update.action == "Hit":
            db_blackjack_game.user_hand = add_cards_to_hand(db_blackjack_game.user_hand, 1)

            if calculate_blackjack_hand_value(db_blackjack_game.dealer_hand) < 17:
                db_blackjack_game.dealer_hand = add_cards_to_hand(db_blackjack_game.dealer_hand, 1)

        # If user has stood, dealer hits until their hand value is more than or equal to 17
        if blackjack_game_update.action == "Stand":
            while calculate_blackjack_hand_value(db_blackjack_game.dealer_hand) < 17:
                db_blackjack_game.dealer_hand = add_cards_to_hand(db_blackjack_game.dealer_hand, 1)
        
    # Determine if the game has finished
    user_hand_value = calculate_blackjack_hand_value(db_blackjack_game.user_hand)
    dealer_hand_value = calculate_blackjack_hand_value(db_blackjack_game.dealer_hand)

    db_blackjack_game.user_hand_value = user_hand_value
    db_blackjack_game.dealer_hand_value = dealer_hand_value

    game_outcome = None

    if user_hand_value > 21:
            game_outcome = "Lose"
    elif user_hand_value == 21:
        if dealer_hand_value == 21:
            game_outcome = "Tie"
        else:
            game_outcome = "Win"
    else:
        if dealer_hand_value > 21:
            game_outcome = "Win"
        elif dealer_hand_value == 21:
            game_outcome = "Lose"
        elif dealer_hand_value > user_hand_value and blackjack_game_update.action == "Stand":
            game_outcome = "Lose"
        elif user_hand_value > dealer_hand_value and blackjack_game_update.action == "Stand" and dealer_hand_value >= 17:
            game_outcome = "Win"
        elif user_hand_value == dealer_hand_value and blackjack_game_update.action == "Stand":
            game_outcome = "Tie"

    # If the game ended, set result and update balances
    if game_outcome != None:
        currency = db_blackjack_game.currency
        db_user_currency = session.exec(select(UserCurrency).where(UserCurrency.user_id == current_user.id, UserCurrency.currency_id == db_blackjack_game.currency_id)).first()
        db_blackjack_game.result = game_outcome
        
        if game_outcome == "Win":
            db_blackjack_game.result_text = f"You won {currency.prefix}{db_blackjack_game.bet:.{currency.decimal_places}f} {currency.display_name}. Your {currency.display_name} balance is now {currency.prefix}{(db_user_currency.balance + db_blackjack_game.bet):.{currency.decimal_places}f}"
        elif game_outcome == "Lose":
            db_blackjack_game.result_text = f"You lost {currency.prefix}{db_blackjack_game.bet:.{currency.decimal_places}f} {currency.display_name}. Your {currency.display_name} balance is now {currency.prefix}{(db_user_currency.balance - db_blackjack_game.bet):.{currency.decimal_places}f}"
        else:
            db_blackjack_game.result_text = f"You were refunded {currency.prefix}{db_blackjack_game.bet:.{currency.decimal_places}f} {currency.display_name}. Your {currency.display_name} balance is {currency.prefix}{db_user_currency.balance:.{currency.decimal_places}f}"

        # Update balances
        for user_currency in current_user.balances:
            if user_currency.id == 1:
                user_currency.balance += 10
                session.add(user_currency)
            if user_currency.id == currency.id:
                if game_outcome == "Win":
                    user_currency.balance += db_blackjack_game.bet
                elif game_outcome == "Lose":
                    user_currency.balance -= db_blackjack_game.bet
                session.add(user_currency)

    # Commit game to database
    session.add(db_blackjack_game)
    session.commit()
    session.refresh(db_blackjack_game)

    # Censor dealer cards if the game has not finished, return
    if not game_outcome:
        db_blackjack_game.dealer_hand_value = 0
        censored_dealer_hand = [db_blackjack_game.dealer_hand[0]]
        for i in range(1, len(db_blackjack_game.dealer_hand), 1):
            censored_dealer_hand.append("[?]")
        db_blackjack_game.dealer_hand = censored_dealer_hand
    return db_blackjack_game
