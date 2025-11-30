# Module Imports
import logging
import requests
from typing import Union
from config import settings
from sqlmodel import Session, select
from schemas.servers import Server
from schemas.database import engine
from datetime import datetime, timezone


logger = logging.getLogger("services")

# Services
# Update running and time started for all servers via dockerlink
def update_server_statuses() -> None:
    with Session(engine) as session:
        db_servers = session.exec(select(Server)).all()
        db_server_uuids = {"servers": []}

        for db_server in db_servers:
            db_server_uuids["servers"].append(db_server.uuid)

        # Get statuses
        url: str = f"{settings.DOCKERLINK_URL}/info"
        headers: dict = {"X-API-Key": settings.DOCKERLINK_AUTH_KEY}
        response = requests.post(url=url, json=db_server_uuids, headers=headers)

        if response.ok:
            # Update db entries
            for item in response.json():
                server: Server = next((s for s in db_servers if s.uuid == item["uuid"]), None)
                server.is_running = item["running"]
                if item["running"]:
                    server.time_started = datetime.fromisoformat(item["created"].replace("Z", "+00:00"))
                else:
                    server.time_started = None
                session.add(server)

            session.commit()
            logger.info(f"Updated status for all servers")
        else:
            logger.error(f"Failed to update server statuses")

# Check if a server is running via pterodactyl
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
