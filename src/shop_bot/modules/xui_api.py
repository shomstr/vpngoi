import uuid
from datetime import datetime, timedelta
import logging
from urllib.parse import urlparse
from typing import List, Dict

from py3xui import Api, Client, Inbound

from shop_bot.data_manager.database import get_host, get_key_by_email
import base64
from shop_bot.data_manager.database import get_user_keys
import json

logger = logging.getLogger(__name__)




def login_to_host(host_url: str, username: str, password: str, inbound_id: int) -> tuple[Api | None, Inbound | None]:
    try:
        api = Api(host=host_url, username=username, password=password)
        api.login()
        inbounds: List[Inbound] = api.inbound.get_list()
        target_inbound = next((inbound for inbound in inbounds if inbound.id == inbound_id), None)
        
        if target_inbound is None:
            logger.error(f"Inbound with ID '{inbound_id}' not found on host '{host_url}'")
            return api, None
        return api, target_inbound
    except Exception as e:
        logger.error(f"Login or inbound retrieval failed for host '{host_url}': {e}", exc_info=True)
        return None, None


def get_connection_string(inbound, user_uuid: str, host_url: str, remark: str) -> str | None:
    """
    Генерирует VLESS URI для клиента.
    `inbound` — объект Inbound из py3xui (Pydantic-модель).
    """
    if not inbound:
        return None

    try:
        # Извлекаем данные из Pydantic-моделей
        port = inbound.port
        settings = inbound.settings  # Settings (Pydantic)
        stream = inbound.stream_settings  # StreamSettings (Pydantic)
        logger.error(inbound)
        if not stream:
            logger.error("StreamSettings is None")
            return None

        # Основные параметры
        network = getattr(stream, "network", "tcp")
        security = getattr(stream, "security", "none")
        server = urlparse(host_url).hostname

        if not server:
            logger.error(f"Cannot parse hostname from host_url: {host_url}")
            return None

        # Ищем flow у клиента
        flow = ""
        if settings and hasattr(settings, "clients"):
            for client in settings.clients:
                if getattr(client, "id", None) == user_uuid:
                    flow = getattr(client, "flow", "")
                    break

        # Собираем параметры вручную (без .get())
        params = [f"type={network}", f"security={security}"]

        if security == "reality":
            reality = getattr(stream, "reality_settings", None)
            if not reality:
                logger.error("REALITY enabled but reality_settings is missing")
                return None

            pbk = getattr(reality, "public_key", None)
            short_ids = getattr(reality, "short_ids", [])
            server_names = getattr(reality, "server_names", [])
            fingerprint = getattr(reality, "fingerprint", "chrome")

            if not (pbk and short_ids and server_names):
                logger.error("Missing REALITY parameters: pbk, short_ids, or server_names")
                return None

            params.extend([
                f"pbk={pbk}",
                f"sid={short_ids[0]}",
                f"sni={server_names[0]}",
                f"fp={fingerprint}",
                "spx=%2F"
            ])

        elif security == "tls":
            tls = getattr(stream, "tls_settings", None)
            sni = getattr(tls, "server_name", server) if tls else server
            params.append(f"sni={sni}")
            params.append("fp=chrome")

        if flow:
            params.append(f"flow={flow}")

        query = "&".join(params)
        return f"vless://{user_uuid}@{server}:{port}?{query}#{remark}"

    except Exception as e:
        logger.error(f"Error generating connection string: {e}", exc_info=True)
        return None

def update_or_create_client_on_panel(api: Api, inbound_id: int, email: str, days_to_add: int) -> tuple[str | None, int | None]:
    try:
        inbound_to_modify = api.inbound.get_by_id(inbound_id)
        if not inbound_to_modify:
            raise ValueError(f"Could not find inbound with ID {inbound_id}")

        if inbound_to_modify.settings.clients is None:
            inbound_to_modify.settings.clients = []
            
        client_index = -1
        for i, client in enumerate(inbound_to_modify.settings.clients):
            if client.email == email:
                client_index = i
                break
        
        if client_index != -1:
            existing_client = inbound_to_modify.settings.clients[client_index]
            if existing_client.expiry_time > int(datetime.now().timestamp() * 1000):
                current_expiry_dt = datetime.fromtimestamp(existing_client.expiry_time / 1000)
                new_expiry_dt = current_expiry_dt + timedelta(days=days_to_add)
            else:
                new_expiry_dt = datetime.now() + timedelta(days=days_to_add)
        else:
            new_expiry_dt = datetime.now() + timedelta(days=days_to_add)

        new_expiry_ms = int(new_expiry_dt.timestamp() * 1000)

        if client_index != -1:
            inbound_to_modify.settings.clients[client_index].reset = days_to_add
            inbound_to_modify.settings.clients[client_index].enable = True
            
            client_uuid = inbound_to_modify.settings.clients[client_index].id
        else:
            client_uuid = str(uuid.uuid4())
            new_client = Client(
                id=client_uuid,
                email=email,
                enable=True,
                flow="xtls-rprx-vision",
                expiry_time=new_expiry_ms
            )
            inbound_to_modify.settings.clients.append(new_client)

        api.inbound.update(inbound_id, inbound_to_modify)

        return client_uuid, new_expiry_ms

    except Exception as e:
        logger.error(f"Error in update_or_create_client_on_panel: {e}", exc_info=True)
        return None, None

async def create_or_update_key_on_host(host_name: str, email: str, days_to_add: int) -> Dict | None:
    host_data = get_host(host_name)
    if not host_data:
        logger.error(f"Workflow failed: Host '{host_name}' not found in the database.")
        return None

    api, inbound = login_to_host(
        host_url=host_data['host_url'],
        username=host_data['host_username'],
        password=host_data['host_pass'],
        inbound_id=host_data['host_inbound_id']
    )
    if not api or not inbound:
        logger.error(f"Workflow failed: Could not log in or find inbound on host '{host_name}'.")
        return None
        
    client_uuid, new_expiry_ms = update_or_create_client_on_panel(api, inbound.id, email, days_to_add)
    if not client_uuid:
        logger.error(f"Workflow failed: Could not create/update client '{email}' on host '{host_name}'.")
        return None
    
    connection_string = get_connection_string(inbound, client_uuid, host_data['host_url'], remark=host_name)
    
    logger.info(f"Successfully processed key for '{email}' on host '{host_name}'.")
    
    return {
        "client_uuid": client_uuid,
        "email": email,
        "expiry_timestamp_ms": new_expiry_ms,
        "connection_string": connection_string,
        "host_name": host_name
    }

async def get_key_details_from_host(key_data: dict) -> dict | None:
    host_name = key_data.get('host_name')
    if not host_name:
        logger.error(f"Could not get key details: host_name is missing for key_id {key_data.get('key_id')}")
        return None

    host_db_data = get_host(host_name)
    if not host_db_data:
        logger.error(f"Could not get key details: Host '{host_name}' not found in the database.")
        return None

    api, inbound = login_to_host(
        host_url=host_db_data['host_url'],
        username=host_db_data['host_username'],
        password=host_db_data['host_pass'],
        inbound_id=host_db_data['host_inbound_id']
    )
    if not api or not inbound: return None

    connection_string = get_connection_string(inbound, key_data['xui_client_uuid'], host_db_data['host_url'], remark=host_name)
    return {"connection_string": connection_string}

async def delete_client_on_host(host_name: str, client_email: str) -> bool:
    host_data = get_host(host_name)
    if not host_data:
        logger.error(f"Cannot delete client: Host '{host_name}' not found.")
        return False

    api, inbound = login_to_host(
        host_url=host_data['host_url'],
        username=host_data['host_username'],
        password=host_data['host_pass'],
        inbound_id=host_data['host_inbound_id']
    )

    if not api or not inbound:
        logger.error(f"Cannot delete client: Login or inbound lookup failed for host '{host_name}'.")
        return False
        
    try:
        client_to_delete = get_key_by_email(client_email)
        if client_to_delete:
            api.client.delete(inbound.id, client_to_delete['xui_client_uuid'])
            logger.info(f"Successfully deleted client '{client_to_delete['xui_client_uuid']}' from host '{host_name}'.")
            return True
        else:
            logger.warning(f"Client '{client_to_delete['xui_client_uuid']}' not found on host '{host_name}' for deletion (already gone).")
            return True
            
    except Exception as e:
        logger.error(f"Failed to delete client '{client_to_delete['xui_client_uuid']}' from host '{host_name}': {e}", exc_info=True)
        return False