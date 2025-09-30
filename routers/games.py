# Module Imports
import logging
from fastapi import APIRouter, HTTPException, status, Depends
from sqlmodel import Session, select
from sqlalchemy import func
from auth.security import Authenticator, get_current_user, get_current_user_can_add_games
from schemas.database import get_session
from schemas.games import *
from schemas.users import User
from services.games import get_banner_link, get_last_updated, check_game_exists


router = APIRouter()
logger = logging.getLogger("services")

# Get all games
@router.get("/", tags=["games"], response_model=list[GamePublic], dependencies=[Depends(Authenticator(True, True))])
def get_games(session: Session = Depends(get_session)):
    return session.exec(select(Game).order_by(Game.id.asc())).all()

# Get 12 most recently added games
@router.get("/recentadd/", tags=["games"], response_model=list[GamePublic], dependencies=[Depends(Authenticator(True, True))])
def recently_added_games(session: Session = Depends(get_session)):
    return session.exec(select(Game).order_by(Game.date_added.desc()).limit(12))

# Get 12 most recently update games
@router.get("/recentupdate/", tags=["games"], response_model=list[GamePublic], dependencies=[Depends(Authenticator(True, True))])
def recently_updated_games(session: Session = Depends(get_session)):
    return session.exec(select(Game).order_by(Game.last_updated.desc()).limit(12), dependencies=[Depends(Authenticator(True, True))])

# Get 12 games which have not recieved updates the longest
@router.get("/dead/", tags=["games"], response_model=list[GamePublic], dependencies=[Depends(Authenticator(True, True))])
def dead_games(session: Session = Depends(get_session)):
    return session.exec(select(Game).where(Game.last_updated != None).order_by(Game.last_updated.asc()).limit(12))

# Get 12 random games
@router.get("/random/", tags=["games"], response_model=list[GamePublic], dependencies=[Depends(Authenticator(True, True))])
def random_games(session: Session = Depends(get_session)):
    return session.exec(select(Game).order_by(func.random()).limit(12))

# Get 12 highest rated games
@router.get("/top/", tags=["games"], response_model=list[GamePublic], dependencies=[Depends(Authenticator(True, True))])
def top_games(session: Session = Depends(get_session)):
    return session.exec(select(Game).where(Game.popularity_score != None).order_by(Game.popularity_score.desc()).limit(12))
    
# Get all game tags
@router.get("/tags/", tags=["games"], response_model=list[GameTag], dependencies=[Depends(Authenticator(True, True))])
def get_game_tags(session: Session = Depends(get_session)):
    return session.exec(select(GameTag).order_by(GameTag.id.asc())).all()

# Update game rating
@router.post("/ratings/update", tags=["games"], response_model=GameRatingPublic)
def update_game_rating(rating: GameRatingUpdate, current_user: User =  Depends(get_current_user), session: Session = Depends(get_session)):
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
    db_rating.last_updated = datetime.now()

    # Commit rating and return
    session.add(db_rating)
    session.commit()
    session.refresh(db_rating)
    return db_rating

# Get current user's ratings
@router.get("/ratings/me", tags=["games"], response_model=list[GameRatingPublic])
def get_current_user_ratings(current_user: User =  Depends(get_current_user), session: Session = Depends(get_session)):
    return session.exec(select(GameRating).where(GameRating.user_id == current_user.id).order_by(GameRating.id.asc())).all() 

# Add game
@router.post("/add/", tags=["games"], response_model=GamePublic, status_code=201)
def add_game(game: GameCreate, current_user: User =  Depends(get_current_user_can_add_games), session: Session = Depends(get_session)):
    # Create game instance using validated user data
    db_game = Game(**game.model_dump())

    # Set user who added the game
    db_game.added_by_id = current_user.id

    # Ensure that the game doesn't already exist
    check_game_exists(db_game.name, db_game.platform, db_game.link)

    # Ensure that banner link and last updated is set
    db_game.banner_link = get_banner_link(db_game.link, db_game.platform)
    db_game.last_updated = get_last_updated(db_game.link, db_game.platform)

    # Set date added
    db_game.date_added = datetime.now()

    # Commit game to db and return
    session.add(db_game)
    session.commit()
    session.refresh(db_game)
    return db_game

# Get game
@router.get("/{id}/", tags=["games"], response_model=GamePublic, dependencies=[Depends(Authenticator(True, True))])
def get_game(id: int, session: Session = Depends(get_session)):
    game = session.get(Game, id)
    if not game:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found")
    return game

# Edit game
@router.patch("/{id}/", tags=["games"], response_model=GamePublic, status_code=200)
def edit_game(id: int, game: GameUpdate, current_user: User =  Depends(get_current_user), session: Session = Depends(get_session)):
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

    # Ensure that banner link and last updated is set
    db_game.banner_link = get_banner_link(db_game.link, db_game.platform)
    db_game.last_updated = get_last_updated(db_game.link, db_game.platform)

    # Commit game to db and return
    session.add(db_game)
    session.commit()
    session.refresh(db_game)
    return db_game

# Delete game
@router.delete("/{id}/", tags=["games"], status_code=204)
def delete_game(id: int, current_user: User =  Depends(get_current_user), session: Session = Depends(get_session)):
    db_game = session.get(Game, id)
    if not db_game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Check if the current user was the one that added the game
    if db_game.added_by_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot delete a game you did not add")
    
    session.delete(db_game)
    session.commit()
    return
