# Module Imports
import re
import logging
import requests
from datetime import datetime
from fastapi import HTTPException, status
from sqlmodel import Session, select
from schemas.database import engine
from schemas.games import Game

logger = logging.getLogger("services")

# Services
# Get roblox universe id from a roblox game
def get_roblox_universe_id(link: str) -> str | None:
    # Get place id
    try:
        place_id: str = (re.search(r'roblox\.com/games/(\d+)', link)).group(1)
    except AttributeError:
        return None

    # Get universe id
    url: str = f"https://apis.roblox.com/universes/v1/places/{place_id}/universe"
    response = requests.get(url=url)

    if response.status_code != 200:
        return None
    return response.json()["universeId"]

# Get banner link for a roblox or steam game
def get_banner_link(link: str, platform: str) -> str | None:
    match platform:
        case "Roblox":
            # Get universe id
            universe_id: str = get_roblox_universe_id(link)
            if not universe_id:
                return None
            
            # Get banner link
            url: str = f"https://thumbnails.roblox.com/v1/games/multiget/thumbnails?universeIds={universe_id}&count=1&size=768x432&format=Png"
            response = requests.get(url=url)

            if response.status_code != 200:
                return None
            return response.json()["data"][0]["thumbnails"][0]["imageUrl"]
        
        case "Steam":
            # Get banner link
            try:
                app_id = re.search(r'/app/(\d+)', link).group(1)
                return f"https://cdn.akamai.steamstatic.com/steam/apps/{app_id}/capsule_616x353.jpg"
            except AttributeError:
                return None
        
        case _:
            return None
        
# Get when a game was last updated
def get_last_updated(link: str, platform: str) -> str | None:
    match platform:
        case "Roblox":
            # Get universe id
            universe_id: str = get_roblox_universe_id(link)
            if not universe_id:
                return None
            
            # Get last updated
            url: str = f"https://games.roblox.com/v1/games?universeIds={universe_id}"
            response = requests.get(url=url)

            if response.status_code != 200:
                return None
            return datetime.fromisoformat((response.json()["data"][0]["updated"])[:-1] + '+00:00')
        
        case _:
            return None

# Check if a game already exists
def check_game_exists(name: str, platform: str, link: str) -> bool:
    with Session(engine) as session:
        # Ensure no other game has the same name
        if session.exec(select(Game).where(Game.name == name)).first() is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=[{
                    "loc": ["body", "name"],
                    "msg": "This game has already been added",
                    "type": "value_error",
                }]
            )
        
        # Ensure no other game has the same link (except for party games)
        if session.exec(select(Game).where(Game.link == link)).first() is not None and platform != "Party":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=[{
                    "loc": ["body", "link"],
                    "msg": "This game has already been added",
                    "type": "value_error",
                }]
            )
