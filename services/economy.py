# Module Imports
import logging
import random
from typing import Tuple
from datetime import datetime, timezone
from sqlmodel import Session, select
from schemas.database import engine
from schemas.economy import Currency, UserCurrency
from schemas.users import User


logger = logging.getLogger("services")

# Services
# User Currencies
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

# Populate currencies for all existing users
def populate_all_user_currencies() -> None:
    with Session(engine) as session:
        db_users = session.exec(select(User)).all()
        for user in db_users:
            populate_user_currencies(user)

# Blackjack
# Generate a playing card
def generate_card() -> str:
    suit = random.choice(["♠", "♥", "♦", "♣"])
    value = random.choice([2, 3, 4, 5, 6, 7, 8, 9, 10, "J", "Q", "K", "A"])
    return f"{suit}{value}"

# Add cards to a hand for blackjack
def add_cards_to_hand(hand: list, number: int) -> list:
    for i in range(1, number + 1, 1):
        new_card = generate_card()
        duplicate = True
        while duplicate == True:
            if new_card in hand:
                new_card = generate_card()
                continue
            hand.append(new_card)
            duplicate = False
    return hand

# Calculate the value of a hand, and how many aces are in the hand
def calculate_hand_value(hand: list) -> Tuple[int, int]:
    # Calculate hand values
    card_values = []
    aces = 0
    for card in hand:
        if card[1:] in ["J", "Q", "K", "A"]:
            if card[1:] == "A":
                aces +=1 
            card_values.append(11)
        else:
            card_values.append(int(card[1:]))
    return sum(card_values), aces

# Calculate the value of a hand for blackjack (aces can be either 11 or 1)
def calculate_blackjack_hand_value(hand: list) -> int:
    hand_value, aces = calculate_hand_value(hand)
    while True:
        if hand_value > 21:
            if aces > 0:
                aces -= 1
                hand_value -= 10
            else:
                break
        else:
            break
    return hand_value
            
# Misc
# Ensure a datetime object has utc information
def ensure_aware(time: datetime) -> datetime:
    return time.replace(tzinfo=timezone.utc)