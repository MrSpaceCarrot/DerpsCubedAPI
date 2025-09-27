# Module Imports
import code
from sqlmodel import Session
from schemas.database import engine
from schemas.auth import *
from schemas.games import *
from schemas.servers import *
from schemas.users import *

session = Session(engine)

namespace = {
    "session": session,
    "ApiKey": ApiKey,
    "Game": Game,
    "GameTag": GameTag,
    "GameRating": GameRating,
    "Server": Server,
    "ServerCategory": ServerCategory,
    "User": User
}

code.interact(local=namespace)
