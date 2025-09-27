# Module Imports
import code
from sqlmodel import Session
from schemas.database import engine
from schemas.auth import ApiKey
from schemas.games import Game
from schemas.servers import Server, ServerCategory
from schemas.users import User

session = Session(engine)

namespace = {
    "session": session,
    "ApiKey": ApiKey,
    "Game": Game,
    "Server": Server,
    "ServerCategory": ServerCategory,
    "User": User
}

code.interact(local=namespace)
