# Module Imports
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, status, Depends
from sqlmodel import Session, select
from sqlalchemy import func
from auth.security import require_permission
from schemas.database import get_session, apply_filters
from schemas.games import *
from schemas.users import User
from services.games import *
from services.storage import *


router = APIRouter()
logger = logging.getLogger("services")

# Get games
@router.get("", tags=["games"], response_model=list[GamePublic], dependencies=[Depends(require_permission("can_view_games"))])
def get_games(filters: FilterGame = Depends(), session: Session = Depends(get_session)):
    query = select(Game)
    query = apply_filters(query, Game, filters)
    return session.exec(query)
    
# Get game tags
@router.get("/tags", tags=["games"], response_model=list[GameTag], dependencies=[Depends(require_permission("can_view_games"))])
def get_game_tags(filters: FilterGameTag = Depends(), session: Session = Depends(get_session)):
    query = select(GameTag)
    query = apply_filters(query, GameTag, filters)
    return session.exec(query)

# Get game ratings
@router.get("/ratings", tags=["games"], response_model=list[GameRatingPublic], dependencies=[Depends(require_permission("can_view_games"))])
def get_game_ratings(filters: FilterGameRating = Depends(), session: Session = Depends(get_session)):
    query = select(GameRating)
    query = apply_filters(query, GameRating, filters)
    return session.exec(query)

# Get current user's ratings
@router.get("/ratings/me", tags=["games"], response_model=list[GameRatingPublic])
def get_current_user_game_ratings(filters: FilterGameRating = Depends(), current_user: User =  Depends(require_permission("can_view_games")), session: Session = Depends(get_session)):
    query = select(GameRating).where(GameRating.user_id == current_user.id)
    query = apply_filters(query, GameRating, filters)
    return session.exec(query)

# Update game rating
@router.post("/ratings/update", tags=["games"], response_model=GameRatingPublic)
def update_game_rating(rating: GameRatingUpdate, current_user: User =  Depends(require_permission("can_add_ratings")), session: Session = Depends(get_session)):
    # Check that the game being rated exists
    db_game = session.exec(select(Game).where(Game.id == rating.game_id)).first()
    if not db_game:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found")

    # Check if rating already exists:
    db_rating = session.exec(select(GameRating).where(GameRating.game_id == rating.game_id, GameRating.user_id == current_user.id)).first()
    if db_rating:
        # If rating already exists, update it
        db_rating.rating = rating.rating
    else:
        # Otherwise create new rating
        db_rating = GameRating(**rating.model_dump())
        db_rating.user_id = current_user.id

    # Update last_updated
    db_rating.last_updated = datetime.now(timezone.utc)

    # Commit rating
    session.add(db_rating)
    session.commit()
    session.refresh(db_rating)

    # Update game's average rating and popularity score
    update_average_rating(db_game.id)
    update_popularity_score(db_game.id)
    return db_rating

# Add game
@router.post("/add", tags=["games"], response_model=GamePublic, status_code=201)
def add_game(game: GameCreate, current_user: User =  Depends(require_permission("can_add_games")), session: Session = Depends(get_session)):
    # Create game instance using validated user data
    db_game = Game(**game.model_dump())

    # Set user who added the game
    db_game.added_by_id = current_user.id

    # Ensure that the game doesn't already exist
    check_game_exists(db_game.name, db_game.platform, db_game.link)

    # Check that all submitted tags are valid
    validate_tags(db_game.tags)

    # Set banner link and last updated
    if not game.banner_link:
        db_game.banner_link = get_banner_link(db_game.link, db_game.platform)
        if not db_game.banner_link:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=[{"type": "value_error", "loc": ["body", "link"], "msg": "Value error, Failed to get banner link, the game link is probably invalid", "input": game.link}])
    db_game.last_updated = get_last_updated(db_game.link, db_game.platform)

    # Set date added
    db_game.date_added = datetime.now(timezone.utc)

    # Add game to session to get id
    session.add(db_game)
    session.flush()

    # Set banner image
    banner_image_file_name = f"banner_images/{db_game.id}.png"
    db_game.banner_image = banner_image_file_name
    banner_image = generate_banner_image(db_game.banner_link)
    upload_file_to_bucket(banner_image, banner_image_file_name)

    # Commit game to db and return
    session.commit()
    session.refresh(db_game)
    return db_game

# Get game
@router.get("/{id}", tags=["games"], response_model=GamePublic, dependencies=[Depends(require_permission("can_view_games"))])
def get_game(id: int, session: Session = Depends(get_session)):
    db_game = session.get(Game, id)
    if not db_game:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found")
    return db_game

# Edit game
@router.patch("/{id}", tags=["games"], response_model=GamePublic, status_code=200)
def edit_game(id: int, game: GameUpdate, current_user: User =  Depends(require_permission("can_add_games")), session: Session = Depends(get_session)):
    # Ensure game exists
    db_game = session.get(Game, id)
    if not db_game:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found")
    
    # Check if the current user was the one that added the game
    if db_game.added_by_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot edit a game you did not add")
    
    # Get updates provided by user
    game_updates = game.model_dump(exclude_unset=True)

    # Write updates to db model
    for key, value in game_updates.items():
        setattr(db_game, key, value)

    # Check that all submitted tags are valid
    validate_tags(db_game.tags)

    # Set banner link, banner image, and last updated
    update_banner_link(db_game.id)
    update_banner_image(db_game.id)
    update_last_updated(db_game.id)

    # Commit game to db and return
    session.add(db_game)
    session.commit()
    session.refresh(db_game)
    return db_game

# Delete game
@router.delete("/{id}", tags=["games"], status_code=204)
def delete_game(id: int, current_user: User =  Depends(require_permission("can_delete_games")), session: Session = Depends(get_session)):
    db_game = session.get(Game, id)
    if not db_game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Check if the current user was the one that added the game
    if db_game.added_by_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot delete a game you did not add")
    
    # Remove game's banner image from storage bucket
    banner_image_file_name = f"banner_images/{db_game.id}.png"
    delete_file_from_bucket(banner_image_file_name)
    
    # Commit deletion
    session.delete(db_game)
    session.commit()
    return
