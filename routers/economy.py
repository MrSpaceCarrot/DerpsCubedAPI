# Module Imports
import uuid
import random
from datetime import datetime, timezone, timedelta
from typing import Optional, Union
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi_filter import FilterDepends
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlmodel import Session, select
from sqlalchemy import func
from auth.security import require_permission
from schemas.database import get_session
from schemas.economy import *
from schemas.users import User
from services.economy import ensure_aware, add_cards_to_hand, calculate_blackjack_hand_value
from services.users import get_or_create_user

router = APIRouter()

# Get currencies
@router.get("/currencies", tags=["economy"], dependencies=[Depends(require_permission("can_use_economy"))])
def get_currencies(filter: CurrencyFilter = FilterDepends(CurrencyFilter), session: Session = Depends(get_session)) -> Page[CurrencyPublic]:
    query = select(Currency)
    query = filter.filter(query)
    query = filter.sort(query)
    return paginate(session, query)

# Start currency exchange
@router.post("/currencies/exchange/start", tags=["economy"])
def start_currency_exchange(currency_exchange: CurrencyExchangeStart, current_user: User = Depends(require_permission("can_use_economy")), session: Session = Depends(get_session)):
    current_user: User = session.merge(current_user)

    # Get details from request
    currency_exchange: CurrencyExchangeStart = CurrencyExchangeStart(**currency_exchange.model_dump())

    # Check that the user does not have any unfinished exchanges
    db_unexpired_exchange = session.exec(select(CurrencyExchange).where(CurrencyExchange.user_id == current_user.id).where(CurrencyExchange.result == None)).first()
    if db_unexpired_exchange and datetime.now(timezone.utc) < ensure_aware(db_unexpired_exchange.expires):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You already have an active currency exchange that has not been confirmed, canceled, or expired")

    # Load given currencies
    db_currencies = session.exec(select(Currency)).all()
    
    currency_from: Currency = None
    currency_to: Currency = None
    for currency in db_currencies:
        if currency.id == currency_exchange.currency_from_id:
            currency_from = currency
        if currency.id == currency_exchange.currency_to_id:
            currency_to = currency

    # Validate currency from
    if not currency_from:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Currency from not found")
    if not currency_from.can_exchange:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"You cannot exchange {currency_from.display_name}")
    
    # Validate currency to
    if not currency_to:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Currency to not found")
    if not currency_to.can_exchange:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"You cannot exchange to {currency_to.display_name}")
    
    # Ensure both currencies are not the same
    if currency_from == currency_to:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"You cannot convert {currency_from.display_name} into {currency_to.display_name}")
    
    # Get user balance
    user_currency_from: UserCurrency = session.exec(select(UserCurrency).where(UserCurrency.user_id == current_user.id, UserCurrency.currency_id == currency_from.id)).first()

    # Check that user has enough balance of given currency
    if user_currency_from.balance < currency_exchange.amount:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Insufficent {currency_from.display_name} balance (have {currency_from.prefix}{user_currency_from.balance:.{currency_from.decimal_places}f}, need {currency_from.prefix}{currency_exchange.amount:.{currency_from.decimal_places}f})")

    # Calculate exchange rate between currencies
    relative_rate: float = currency_from.exchange_rate / currency_to.exchange_rate
    currency_to_amount_gained: float = currency_exchange.amount * relative_rate

    # Create CurrencyExchange
    code = str(uuid.uuid4())
    expires = datetime.now(timezone.utc) + timedelta(minutes=5)
    db_currency_exchange = CurrencyExchange(code=code,
                                            user_id=current_user.id,
                                            currency_from_id=currency_from.id,
                                            currency_from_amount=currency_exchange.amount,
                                            currency_to_id=currency_to.id,
                                            currency_to_amount=currency_to_amount_gained,
                                            relative_exchange_rate=relative_rate,
                                            expires=expires)
    session.add(db_currency_exchange)
    session.commit()
    
    # Create Response
    response_text: list = [f"You are about to convert {currency_from.prefix}{currency_exchange.amount:.{currency_from.decimal_places}f} {currency_from.display_name} into {currency_to.prefix}{currency_to_amount_gained:.{currency_to.decimal_places}f} {currency_to.display_name}", f"{currency_from.prefix}1 {currency_from.display_name} is currently worth {currency_to.prefix}{relative_rate:.4f} {currency_to.display_name}", "Are you sure you want to do this?"]
    return CurrencyExchangeStartResponse(response_text=response_text, code=code)

# Continue currency exchange
@router.post("/currencies/exchange/continue", tags=["economy"])
def continue_currency_exchange(currency_exchange: CurrencyExchangeContinue, current_user: User = Depends(require_permission("can_use_economy")), session: Session = Depends(get_session)):
    current_user: User = session.merge(current_user)

    # Get details from request
    currency_exchange: CurrencyExchangeContinue = CurrencyExchangeContinue(**currency_exchange.model_dump())
    
    # Verify CurrencyExchange
    db_currency_exchange = session.exec(select(CurrencyExchange).where(CurrencyExchange.code == currency_exchange.code)).first()
    if not db_currency_exchange:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Currency exchange code is invalid")

    # Verify that the exchange has not already finished
    if db_currency_exchange.result:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This currency exchange has already finished")
    
    # Check that the exchange has not expired
    if datetime.now(timezone.utc) > ensure_aware(db_currency_exchange.expires):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This currency exchange has expired")

    # Update user balances if action was confirmed
    if currency_exchange.action == "Confirm":
        # Get user balances
        user_currency_from: UserCurrency = session.exec(select(UserCurrency).where(UserCurrency.user_id == current_user.id, UserCurrency.currency_id == db_currency_exchange.currency_from_id)).first()
        user_currency_to: UserCurrency = session.exec(select(UserCurrency).where(UserCurrency.user_id == current_user.id, UserCurrency.currency_id == db_currency_exchange.currency_to_id)).first()

        # Update user balances
        user_currency_from.balance -= db_currency_exchange.currency_from_amount
        user_currency_to.balance += db_currency_exchange.currency_to_amount
        session.add(user_currency_from, user_currency_to)
        session.commit()
        session.refresh(user_currency_from, user_currency_to)

        # Update CurrencyExchange
        currency_from = user_currency_from.currency
        currency_from_amount = db_currency_exchange.currency_from_amount
        currency_to = user_currency_to.currency
        currency_to_amount = db_currency_exchange.currency_to_amount

        db_currency_exchange.result = "Confirmation"
        action = "Confirmation"
        response_text: list = [f"Converted {currency_from.prefix}{currency_from_amount:.{currency_from.decimal_places}f} {currency_from.display_name} to {currency_to.prefix}{currency_to_amount:.{currency_to.decimal_places}f} {currency_to.display_name}", f"Your {currency_from.display_name} balance is now {currency_from.prefix}{user_currency_from.balance:.{currency_from.decimal_places}f}", f"Your {currency_to.display_name} balance is now {currency_to.prefix}{user_currency_to.balance:.{currency_to.decimal_places}f}"]
    
        # Create transactions
        db_transaction_from = Transaction(user_id=current_user.id, currency_id=currency_from.id, amount=-db_currency_exchange.currency_from_amount, timestamp=datetime.now(timezone.utc), note="Currency exchange")
        db_transaction_to = Transaction(user_id=current_user.id, currency_id=currency_to.id, amount=db_currency_exchange.currency_to_amount, timestamp=datetime.now(timezone.utc), note="Currency exchange")
        session.add(db_transaction_from)
        session.add(db_transaction_to)
    else:
        db_currency_exchange.result = "Cancellation"
        action = "Cancellation"
        response_text: list = ["Transaction Cancelled"]

    # Return
    session.add(db_currency_exchange)
    session.commit()
    return CurrencyExchangeContinueResponse(response_text=response_text, action=action)
    
# Get balances
@router.get("/balances", tags=["economy"], dependencies=[Depends(require_permission("can_use_economy"))])
def get_balances(filter: UserCurrencyFilter = FilterDepends(UserCurrencyFilter), session: Session = Depends(get_session)) -> Page[UserCurrencyPublic]:
    query = select(UserCurrency)
    query = filter.filter(query)
    query = filter.sort(query)
    return paginate(session, query)

# Get current user's balances
@router.get("/balances/me", tags=["economy"])
def get_current_user_balances(filter: UserCurrencyFilter = FilterDepends(UserCurrencyFilter), current_user: User = Depends(require_permission("can_use_economy")), session: Session = Depends(get_session)) -> Page[UserCurrencyPublic]:
    query = select(UserCurrency)
    query = filter.filter(query)
    query = filter.sort(query)
    query = query.where(UserCurrency.user_id == current_user.id)
    return paginate(session, query)

# Modify a user's balance for a currency
@router.post("/balances/modify", tags=["economy"], response_model=UserCurrency, dependencies=[Depends(require_permission("can_manage_economy"))])
def modify_user_balance(user_currency_update: UserCurrencyUpdate, session: Session = Depends(get_session)):
    # Get target user using either discord_id or id
    if user_currency_update.discord_id:
        db_user: User = get_or_create_user(user_currency_update.discord_id)
        if not db_user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="An invalid discord id was provided for the gift recipient")
    elif user_currency_update.user_id:
        db_user: User = session.get(User, user_currency_update.user_id)
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Either a id or discord_id of a user must be provided")
    
    # Validate currency
    db_currency: Currency = session.get(Currency, user_currency_update.currency_id)
    if not db_currency:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Currency not found")
    
    # Update user currency, create transaction
    db_user_currency = session.exec(select(UserCurrency).where(UserCurrency.user_id == db_user.id, UserCurrency.currency_id == db_currency.id)).first()
    match user_currency_update.mode:
        case "Add":
            db_user_currency.balance += user_currency_update.amount
            db_transaction = Transaction(user_id=db_user.id, currency_id=db_currency.id, amount=user_currency_update.amount, timestamp=datetime.now(timezone.utc), note=user_currency_update.note)
        case "Subtract":
            db_user_currency.balance -= user_currency_update.amount
            db_transaction = Transaction(user_id=db_user.id, currency_id=db_currency.id, amount=-user_currency_update.amount, timestamp=datetime.now(timezone.utc), note=user_currency_update.note)
        case "Set":
            db_user_currency.balance = user_currency_update.amount
            transaction_amount = -(db_user_currency.balance - user_currency_update.amount)
            db_transaction = Transaction(user_id=db_user.id, currency_id=db_currency.id, amount=transaction_amount, timestamp=datetime.now(timezone.utc), note=user_currency_update.note)
    session.add(db_user_currency)
    session.add(db_transaction)
    session.commit()
    session.refresh(db_user_currency)
    return db_user_currency

# Gift Currency
@router.post("/balances/gift", tags=["economy"])
def send_gift(gift: Gift, current_user: User = Depends(require_permission("can_use_economy")), session: Session = Depends(get_session)):
    current_user: User = session.merge(current_user)

    # Get target user using either discord_id or id
    if gift.discord_id:
        db_recieving_user: User = get_or_create_user(gift.discord_id)
        if not db_recieving_user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="An invalid discord id was provided for the gift recipient")
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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Insufficent {db_currency.display_name} balance (have {db_currency.prefix}{db_sending_user_currency.balance:.{db_currency.decimal_places}f}, need {db_currency.prefix}{gift.amount:.{db_currency.decimal_places}f}).")

    # Change balances
    db_sending_user_currency.balance -= gift.amount
    db_recieving_user_currency.balance += gift.amount
    session.add(db_sending_user_currency, db_recieving_user_currency)

    # Create transactions
    db_transaction_sending = Transaction(user_id=current_user.id, currency_id=gift.currency_id, amount=-gift.amount, timestamp=datetime.now(timezone.utc), note=f"Sent gift to {db_recieving_user.display_name}")
    db_transaction_recieving = Transaction(user_id=db_recieving_user.id, currency_id=gift.currency_id, amount=gift.amount, timestamp=datetime.now(timezone.utc), note=f"Received gift from {current_user.display_name}")
    session.add(db_transaction_sending)
    session.add(db_transaction_recieving)

    session.commit()
    session.refresh(db_sending_user_currency, db_recieving_user_currency)

    # Return
    return f"Successfully gifted {db_currency.prefix}{gift.amount:.{db_currency.decimal_places}f} {db_currency.display_name} to {db_recieving_user.display_name}. Your {db_currency.display_name} balance is now {db_currency.prefix}{db_sending_user_currency.balance:.{db_currency.decimal_places}f}. <@{db_recieving_user.discord_id}>'s {db_currency.display_name} balance is now {db_currency.prefix}{db_recieving_user_currency.balance:.{db_currency.decimal_places}f}."

# Get current user's transactions
@router.get("/transactions/me", tags=["economy"])
def get_current_user_transactions(filter: TransactionFilter = FilterDepends(TransactionFilter), current_user: User = Depends(require_permission("can_use_economy")), session: Session = Depends(get_session)) -> Page[TransactionPublic]:
    query = select(Transaction)
    query = filter.filter(query)
    query = filter.sort(query)
    query = query.where(Transaction.user_id == current_user.id)
    return paginate(session, query)

# Get balances for a specific user
@router.get("/balances/{user_id}", tags=["economy"], response_model=list[UserCurrencyPublic], dependencies=[Depends(require_permission("can_use_economy"))])
def get_user_balances(user_id: int, session: Session = Depends(get_session)):
    db_user: User = session.exec(select(User).where(User.id == user_id)).first()
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return session.exec(select(UserCurrency).where(UserCurrency.user_id == user_id).order_by(UserCurrency.id.asc())).all()

# Get jobs
@router.get("/jobs", tags=["economy"], dependencies=[Depends(require_permission("can_use_economy"))])
def get_jobs(filter: JobFilter = FilterDepends(JobFilter), session: Session = Depends(get_session)) -> Page[JobPublic]:
    query = select(Job)
    query = filter.filter(query)
    query = filter.sort(query)
    return paginate(session, query)

# Get user jobs
@router.get("/jobs/users", tags=["economy"], dependencies=[Depends(require_permission("can_use_economy"))])
def get_user_jobs(filter: UserJobFilter = FilterDepends(UserJobFilter), session: Session = Depends(get_session)) -> Page[UserJobPublic]:
    query = select(UserJob)
    query = filter.filter(query)
    query = filter.sort(query)
    return paginate(session, query)

# Get current user's job
@router.get("/jobs/me", tags=["economy"], response_model=UserJobPublic)
def get_current_user_job(current_user: User = Depends(require_permission("can_use_economy")), session: Session = Depends(get_session)):
    current_user: User = session.merge(current_user)

    db_user_job = session.exec(select(UserJob).where(UserJob.user_id == current_user.id)).first()

    # If job exists, return it
    if db_user_job:
        return db_user_job
    
    # If job does not exist, return a cooldown for when the user can apply for another one
    else:
        for cooldown in current_user.cooldowns:
            if cooldown.cooldown_type == "job_change" and ensure_aware(cooldown.expires) > datetime.now(timezone.utc):
                expires_in = ensure_aware(cooldown.expires) - datetime.now(timezone.utc)
                raise HTTPException(status_code=status.HTTP_200_OK, detail=f"You do not currently have a job. You can apply for another job in {expires_in.seconds}s")
        raise HTTPException(status_code=status.HTTP_200_OK, detail="You do not currently have a job")
    
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
    return {"detail": f"You quit your previous job of {old_job_name}. You can apply for another job in 300s"}

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
    balance.balance = balance.balance + pay_amount
    session.add(balance)

    # Create transaction
    db_transaction = Transaction(user_id=current_user.id, currency_id=current_user.job.currency_id, amount=pay_amount, timestamp=datetime.now(timezone.utc), note=f"{current_user.job.job.display_name} paycheck")
    session.add(db_transaction)

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

# Blackjack
@router.post("/gambling/blackjack", tags=["economy"], response_model=BlackjackGameResponse)
def blackjack(request_blackjack_game: Union[BlackjackGameStart, BlackjackGameContinue], current_user: User = Depends(require_permission("can_use_economy")), session: Session = Depends(get_session)):
    current_user: User = session.merge(current_user)

    # If the game is just starting
    if type(request_blackjack_game) == BlackjackGameStart:
        blackjack_game: BlackjackGameStart = BlackjackGameStart(**request_blackjack_game.model_dump())

        # Check that the user does not have any unfinished games
        db_unexpired_game = session.exec(select(BlackjackGame).where(BlackjackGame.user_id == current_user.id).where(BlackjackGame.result == None)).first()
        if db_unexpired_game and datetime.now(timezone.utc) < ensure_aware(db_unexpired_game.expires):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You already have an active blackjack game that has not been finished or expired")

        # Check that the currency is valid
        db_currency: Currency = session.get(Currency, blackjack_game.currency_id)
        if not db_currency:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Currency not found")
        
        # Check that the currency can be gambled
        if not db_currency.can_gamble:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This currency cannot be gambled")
        
        # Check that the user has enough to bet
        db_user_currency: UserCurrency = session.exec(select(UserCurrency).where(UserCurrency.id == db_currency.id)).first()
        if db_user_currency.balance < blackjack_game.bet:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Insufficent {db_currency.display_name} balance (have {db_currency.prefix}{db_user_currency.balance:.{db_currency.decimal_places}f}, need {db_currency.prefix}{blackjack_game.bet:.{db_currency.decimal_places}f})")

        # Create BlackjackGame
        expires = datetime.now(timezone.utc) + timedelta(minutes=5)
        db_blackjack_game = BlackjackGame(code=str(uuid.uuid4()), user_id=current_user.id, currency_id=db_currency.id, bet=blackjack_game.bet, expires=expires)

        # Draw cards
        db_blackjack_game.user_hand = add_cards_to_hand([], 2)
        db_blackjack_game.dealer_hand = add_cards_to_hand([], 2)

    # If game is already ongoing
    else:
        blackjack_game: BlackjackGameContinue = BlackjackGameContinue(**request_blackjack_game.model_dump())

        # Verify BlackjackGame
        db_blackjack_game = session.exec(select(BlackjackGame).where(BlackjackGame.code == blackjack_game.code)).first()
        if not db_blackjack_game:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blackjack game code is invalid")
        
        # Verify that the game has not already finished
        if db_blackjack_game.result:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This blackjack game has already finished")
        
        # Check that the exchange has not expired
        if datetime.now(timezone.utc) > ensure_aware(db_blackjack_game.expires):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This blackjack game has expired")

        # Verify that an action was given
        if not blackjack_game.action:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Action must either be 'Hit' or 'Stand'")
        
        # If user has hit, draw a card. Dealer hits only if their hand is worth less than 17
        if blackjack_game.action == "Hit":
            db_blackjack_game.user_hand = add_cards_to_hand(db_blackjack_game.user_hand, 1)

            if calculate_blackjack_hand_value(db_blackjack_game.dealer_hand) < 17:
                db_blackjack_game.dealer_hand = add_cards_to_hand(db_blackjack_game.dealer_hand, 1)

        # If user has stood, dealer hits until their hand value is more than or equal to 17
        if blackjack_game.action == "Stand":
            while calculate_blackjack_hand_value(db_blackjack_game.dealer_hand) < 17:
                db_blackjack_game.dealer_hand = add_cards_to_hand(db_blackjack_game.dealer_hand, 1)

        # Get bet currency
        db_currency = db_blackjack_game.currency
        
    # Determine if the game has finished
    user_hand_value = calculate_blackjack_hand_value(db_blackjack_game.user_hand)
    dealer_hand_value = calculate_blackjack_hand_value(db_blackjack_game.dealer_hand)

    db_blackjack_game.user_hand_value = user_hand_value
    db_blackjack_game.dealer_hand_value = dealer_hand_value

    logger.info(user_hand_value)
    logger.info(dealer_hand_value)

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
        else:
            if type(request_blackjack_game) == BlackjackGameContinue:
                if dealer_hand_value > user_hand_value and blackjack_game.action == "Stand":
                    game_outcome = "Lose"
                elif user_hand_value > dealer_hand_value and blackjack_game.action == "Stand" and dealer_hand_value >= 17:
                    game_outcome = "Win"
                elif user_hand_value == dealer_hand_value and blackjack_game.action == "Stand":
                    game_outcome = "Tie"

    # If the game ended, set result and update balances
    if game_outcome != None:
        db_user_currency = session.exec(select(UserCurrency).where(UserCurrency.user_id == current_user.id, UserCurrency.currency_id == db_blackjack_game.currency_id)).first()
        db_blackjack_game.result = game_outcome
        
        if game_outcome == "Win":
            response_text = [f"You won {db_currency.prefix}{db_blackjack_game.bet:.{db_currency.decimal_places}f} {db_currency.display_name}", f"Your {db_currency.display_name} balance is now {db_currency.prefix}{(db_user_currency.balance + db_blackjack_game.bet):.{db_currency.decimal_places}f}"]
        elif game_outcome == "Lose":
            response_text = [f"You lost {db_currency.prefix}{db_blackjack_game.bet:.{db_currency.decimal_places}f} {db_currency.display_name}", f"Your {db_currency.display_name} balance is now {db_currency.prefix}{(db_user_currency.balance - db_blackjack_game.bet):.{db_currency.decimal_places}f}"]
        else:
            response_text = [f"You were refunded {db_currency.prefix}{db_blackjack_game.bet:.{db_currency.decimal_places}f} {db_currency.display_name}", f"Your {db_currency.display_name} balance is {db_currency.prefix}{db_user_currency.balance:.{db_currency.decimal_places}f}"]

        # Update balances, create transactions
        for user_currency in current_user.balances:
            if user_currency.id == 1:
                user_currency.balance += 10
                session.add(user_currency)

            if user_currency.id == db_currency.id:
                if game_outcome == "Win":
                    user_currency.balance += db_blackjack_game.bet
                    db_transaction = Transaction(user_id=current_user.id, currency_id=db_blackjack_game.currency_id, amount=db_blackjack_game.bet, timestamp=datetime.now(timezone.utc), note="Blackjack win")
                    session.add(db_transaction)
                
                elif game_outcome == "Lose":
                    user_currency.balance -= db_blackjack_game.bet
                    db_transaction = Transaction(user_id=current_user.id, currency_id=db_blackjack_game.currency_id, amount=-db_blackjack_game.bet, timestamp=datetime.now(timezone.utc), note="Blackjack loss")
                    session.add(db_transaction)
                session.add(user_currency)
    else:
        response_text = None

    # Commit game to database
    session.add(db_blackjack_game)
    session.commit()
    session.refresh(db_blackjack_game)

    # Censor dealer cards if the game has not finished
    if not game_outcome:
        db_blackjack_game.dealer_hand_value = 0
        censored_dealer_hand = [db_blackjack_game.dealer_hand[0]]
        for i in range(1, len(db_blackjack_game.dealer_hand), 1):
            censored_dealer_hand.append("[?]")
        db_blackjack_game.dealer_hand = censored_dealer_hand

    # Return
    return BlackjackGameResponse(game=db_blackjack_game, response_text=response_text)
