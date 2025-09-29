# Module Imports
import logging
from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from sqlalchemy import func
from schemas.database import get_session
from schemas.games import *
from services.games import get_banner_link, get_last_updated, check_game_exists


router = APIRouter()
logger = logging.getLogger("services")

# Get all games
@router.get("/", tags=["games"], response_model=list[GamePublic])
def get_games(session: Session = Depends(get_session)):
    return session.exec(select(Game).order_by(Game.id.asc())).all()

# Get 12 most recently added games
@router.get("/recentadd/", tags=["games"], response_model=list[GamePublic])
def recently_added_games(session: Session = Depends(get_session)):
    return session.exec(select(Game).order_by(Game.date_added.desc()).limit(12))

# Get 12 most recently update games
@router.get("/recentupdate/", tags=["games"], response_model=list[GamePublic])
def recently_updated_games(session: Session = Depends(get_session)):
    return session.exec(select(Game).order_by(Game.last_updated.desc()).limit(12))

# Get 12 games which have not recieved updates the longest
@router.get("/dead/", tags=["games"], response_model=list[GamePublic])
def dead_games(session: Session = Depends(get_session)):
    return session.exec(select(Game).where(Game.last_updated != None).order_by(Game.last_updated.asc()).limit(12))

# Get 12 random games
@router.get("/random/", tags=["games"], response_model=list[GamePublic])
def random_games(session: Session = Depends(get_session)):
    return session.exec(select(Game).order_by(func.random()).limit(12))

# Get 12 highest rated games
@router.get("/top/", tags=["games"], response_model=list[GamePublic])
def top_games(session: Session = Depends(get_session)):
    return session.exec(select(Game).where(Game.popularity_score != None).order_by(Game.popularity_score.desc()).limit(12))
    
# Get all game tags
@router.get("/tags/", tags=["games"])
def get_game_tags(session: Session = Depends(get_session)) -> list[GameTag]:
    return session.exec(select(GameTag).order_by(GameTag.id.asc())).all()

# Add game
@router.post("/add/", tags=["games"], response_model=GamePublic, status_code=201)
def add_game(game: GameCreate, session: Session = Depends(get_session)):
    # Create game instance using validated user data
    db_game = Game(**game.model_dump())

    # Set user who added the game
    # Check if the user has permission to add games
    # TO DO

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
@router.get("/{id}/", tags=["games"], response_model=GamePublic)
def get_game(id: int, session: Session = Depends(get_session)) -> Game:
    game = session.get(Game, id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return game

# Edit game
@router.patch("/{id}/", tags=["games"], response_model=GamePublic, status_code=200)
def edit_game(id: int, game: GameUpdate, session: Session = Depends(get_session)) -> Game:
    # Ensure game exists
    db_game = session.get(Game, id)
    if not db_game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Check if the user has permission to add games
    # TO DO
    
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
def delete_game(id: int, session: Session = Depends(get_session)) -> None:
    game = session.get(Game, id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Check if the user has permission to add games
    # TO DO
    
    session.delete(game)
    session.commit()
    return
