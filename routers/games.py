# Module Imports
import logging
from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from schemas.database import get_session
from schemas.games import *
from sqlalchemy import func


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
    tags = session.exec(select(GameTag).order_by(GameTag.id.asc())).all()
    return [tag.order() for tag in tags]

# Add game
@router.post("/add/", tags=["games"], response_model=GamePublic)
def add_game(game: GameBase, session: Session = Depends(get_session)):
    logger.info(game)
    db_game = Game.model_validate(game)
    session.add(db_game)
    session.commit()
    return db_game

# Get game
@router.get("/{id}/", tags=["games"], response_model=GamePublic)
def get_game(id: int, session: Session = Depends(get_session)) -> Game:
    game = session.get(Game, id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return game.order()

# Edit game
@router.patch("/{id}/", tags=["games"])
def edit_game(id: int, session: Session = Depends(get_session)) -> Game:
    game = session.get(Game, id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Edit game
    # TO DO

    return game.order()

# Delete game
@router.delete("/{id}/", tags=["games"])
def delete_game(id: int, session: Session = Depends(get_session)) -> Game:
    game = session.get(Game, id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Delete game
    # TO DO

    return game.order()
