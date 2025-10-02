# Module Imports
import code
from sqlmodel import Session
from schemas.database import engine
import schemas.auth
import schemas.games
import schemas.servers
import schemas.users
import services.games
import auth.utilities

session = Session(engine)   

namespace = {}
namespace.update(vars(schemas.auth))
namespace.update(vars(schemas.games))
namespace.update(vars(schemas.servers))
namespace.update(vars(schemas.users))
namespace.update(vars(services.games))
namespace.update(vars(auth.utilities))

code.interact(local=namespace)
