# Module Imports
import logging
import requests
from typing import Union
from config import settings
from schemas.servers import Server


logger = logging.getLogger("services")

# Services
# Check if a server is running
def check_server_running(server: Server) -> Union[bool, None]:
    url: str = f"{settings.PTERODACTYL_DOMAIN}/api/client/servers/{server.uuid}/resources"
    headers: dict = {'Authorization': f'Bearer {settings.PTERODACTYL_CLIENT_API_KEY}'}
    response = requests.get(url=url, headers=headers)
    if response.status_code == 200:
        if response.json()["attributes"]["current_state"] == "running":
            return True
        else:
            return False
    else:
        return None
