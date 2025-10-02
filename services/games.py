# Module Imports
import re
import time
import logging
import requests
from io import BytesIO
from PIL import Image
from datetime import datetime
from fastapi import HTTPException, status
from sqlmodel import Session, select
from schemas.database import engine
from schemas.games import Game, GameRating, GameTag
from services.storage import *


logger = logging.getLogger("services")

# Services
# Banner Links
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
        
# Update banner link for a game
def update_banner_link(game_id: int) -> bool:
    with Session(engine) as session:
        db_game = session.get(Game, game_id)
        existing_banner_link = db_game.banner_link
        new_banner_link = get_banner_link(db_game.link, db_game.platform)

        if new_banner_link == existing_banner_link or not db_game.update_banner_link:
            logger.debug(f"Keeping banner image for {db_game.name}")
            return False
        else:
            logger.debug(f"Updating banner image for {db_game.name}")
            db_game.banner_link = new_banner_link
            session.add(db_game)
            session.commit()
            return True

# Update banner links for all games
def update_banner_links() -> None:
    with Session(engine) as session:
        db_games = session.exec(select(Game).order_by(Game.id.asc())).all()
        kept: int = 0
        updated: int = 0
        for db_game in db_games:
            time.sleep(1)
            result = update_banner_link(db_game.id)
            if result:
                updated += 1
            else:
                kept += 1
        logger.info(f"Updated banner links for {updated} games, kept for {kept} games")

# Last Updated
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
            return datetime.fromisoformat((response.json()["data"][0]["updated"])[:-1]).replace(microsecond=0)
        
        case _:
            return None
        
# Update last updated for a game
def update_last_updated(game_id: int) -> bool:
    with Session(engine) as session:
        db_game = session.get(Game, game_id)
        existing_last_updated = db_game.last_updated
        if existing_last_updated:
            existing_last_updated.replace(microsecond=0)
        new_last_updated = get_last_updated(db_game.link, db_game.platform)

        if new_last_updated == existing_last_updated:
            logger.debug(f"Keeping last updated for {db_game.name} at {existing_last_updated}")
            return False
        else:
            logger.debug(f"Updating last updated for {db_game.name} from {existing_last_updated} to {new_last_updated}")
            db_game.last_updated = new_last_updated
            session.add(db_game)
            session.commit()
            return True

# Update last updated for all games
def update_last_updated_all() -> None:
    with Session(engine) as session:
        db_games = session.exec(select(Game).order_by(Game.id.asc())).all()
        kept: int = 0
        updated: int = 0
        for db_game in db_games:
            time.sleep(1)
            result = update_last_updated(db_game.id)
            if result:
                updated += 1
            else:
                kept += 1
        logger.info(f"Updated last updated for {updated} games, kept for {kept} games")

# Banner Images
# Generate a banner image from a banner link
def generate_banner_image(banner_link: str) -> BytesIO | None:
    try:
        # Get image from image link
        response: requests.Response = requests.get(banner_link)
        img: Image = Image.open(BytesIO(response.content))

        # Resize and crop image
        width, height = img.size
        scale_factor = max(768 / width, 432 / height)
        new_width = int(width * scale_factor)
        new_height = int(height * scale_factor)
        img = img.resize((new_width, new_height))

        left = (new_width - 768) // 2
        top = (new_height - 432) // 2
        right = (new_width + 768) // 2
        bottom = (new_height + 432) // 2
        img = img.crop((left, top, right, bottom))

        # Return contentfile
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer
    except Exception:
        return None

# Update banner image for a game
def update_banner_image(game_id: int) -> None:
    with Session(engine) as session:
        db_game = session.get(Game, game_id)

        banner_image = generate_banner_image(db_game.banner_link)
        if banner_image:
            logger.debug(f"Updating banner image for {db_game.name}")
            upload_file_to_bucket(banner_image, db_game.banner_image)
        else:
            logger.error(f"Error updating banner image for {db_game.name}")

# Update banner image for all games
def update_banner_images() -> None:
    with Session(engine) as session:
        db_games = session.exec(select(Game).order_by(Game.id.asc())).all()
        for db_game in db_games:
            time.sleep(1)
            update_banner_image(db_game.id)
        logger.info(f"Updated banner image for {len(db_games)} games")

# Average Rating
# Calculate the average rating for a game
def calculate_average_rating(ratings: list[GameRating]) -> float | None:
    number_ratings: int = 0
    total_rating: int = 0
    for rating in ratings:
        if rating.rating not in [0, -1]:
            number_ratings += 1
            total_rating += rating.rating
    if number_ratings != 0:
        return round((total_rating / number_ratings), 2)
    else:
        return None
        
# Update the average rating for a game
def update_average_rating(game_id: int) -> bool:
    with Session(engine) as session:
        db_game = session.get(Game, game_id)
        existing_average_rating = db_game.average_rating
        new_average_rating = calculate_average_rating(db_game.ratings)
        
        if new_average_rating == existing_average_rating:
            logger.debug(f"Keeping average rating for {db_game.name} at {existing_average_rating}")
            return False
        else:
            logger.debug(f"Updating average rating for {db_game.name} from {existing_average_rating} to {new_average_rating}")
            db_game.average_rating = new_average_rating
            session.add(db_game)
            session.commit()
            return True

# Update the average rating for all games
def update_average_ratings() -> None:
    with Session(engine) as session:
        db_games = session.exec(select(Game).order_by(Game.id.asc())).all()
        kept: int = 0
        updated: int = 0
        for db_game in db_games:
            result = update_average_rating(db_game.id)
            if result:
                updated += 1
            else:
                kept += 1
        logger.info(f"Updated average rating for {updated} games, kept for {kept} games")

# Popularity Score
# Calculate the popularity score for a game
def calculate_popularity_score(ratings: list[GameRating]) -> float | None:
    for rating in ratings:
        if rating in [0, -1]:
            ratings.remove(rating)
    average_rating = calculate_average_rating(ratings)
    if not average_rating:
        return None
    people_constant = settings.MISC_PEOPLE_CONSTANT
    return round(min(1, (average_rating) * 0.12 * (len(ratings) / people_constant)), 4)

# Update the popularity score for a game
def update_popularity_score(game_id: int) -> bool:
    with Session(engine) as session:
        db_game = session.get(Game, game_id)
        existing_popularity_score = db_game.popularity_score
        new_popularity_score = calculate_popularity_score(db_game.ratings)
        
        if new_popularity_score == existing_popularity_score:
            logger.debug(f"Keeping popularity score for {db_game.name} at {existing_popularity_score}")
            return False
        else:
            logger.debug(f"Updating popularity score for {db_game.name} from {existing_popularity_score} to {new_popularity_score}")
            db_game.popularity_score = new_popularity_score
            session.add(db_game)
            session.commit()
            return True

# Update the popularity score for all games
def update_popularity_scores() -> None:
    with Session(engine) as session:
        db_games = session.exec(select(Game).order_by(Game.id.asc())).all()
        kept: int = 0
        updated: int = 0
        for db_game in db_games:
            result = update_popularity_score(db_game.id)
            if result:
                updated += 1
            else:
                kept += 1
        logger.info(f"Updated popularity score for {updated} games, kept for {kept} games")
        
# Misc
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

# Games maintanence tasks that run hourly
def three_hourly_maintanence() -> None:
    update_banner_links()
    update_banner_images()
    update_average_ratings()
    update_popularity_scores()

# Check if a game already exists
def check_game_exists(name: str, platform: str, link: str) -> None:
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

# Check that all game tags are part of the tags whitelist
def validate_tags(tags: list[GameTag]) -> None:
    with Session(engine) as session:
        for tag in tags:
            db_tag = session.exec(select(GameTag).where(GameTag.name == tag)).first()
            if not db_tag:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=[{
                        "loc": ["body", "tags"],
                        "msg": f"Tag '{tag}' is not in the tag whitelist",
                        "type": "value_error",
                    }]
                )
