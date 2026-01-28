import logging
from datetime import datetime, timedelta
from shop_bot.data_manager.database import add_new_key, get_setting, get_keys_for_host, get_user_keys, get_host
from shop_bot.modules.xui_api import create_or_update_key_on_host  
import urllib.parse

from shop_bot.data_manager.database import get_all_hosts  
from shop_bot.modules.xui_api import login_to_host, get_connection_string, create_or_update_key_on_host

logger = logging.getLogger(__name__)


async def get_existing_vless_links_for_user(user_id: int, host_name: str | None = None) -> list[str]:
    """
    Возвращает список VLESS-ссылок для пользователя.
    
    - Если host_name is None или не передан → только существующие ключи из vpn_keys.
    - Если host_name == "all_servers" → создаёт ключи на всех хостах (если нет) и возвращает все.
    - Если host_name == "server-us" → создаёт/возвращает только для этого хоста.
    """
    if host_name == "all_servers":
        # Режим: все серверы — создаём недостающие
        all_hosts = get_all_hosts()
        if not all_hosts:
            logger.warning("No hosts configured in the system.")
            return []

        # Получаем текущие ключи пользователя как словарь по host_name
        existing_keys = {key["host_name"]: key for key in get_user_keys(user_id)}
        links = []
        duration_days = int(get_setting("trial_duration_days") or 1)

        for host in all_hosts:
            h_name = host["host_name"]
            email = f"user{user_id}@{h_name}"

            if h_name in existing_keys:
                # Уже есть — генерируем ссылку
                xui_uuid = existing_keys[h_name]["xui_client_uuid"]
                conn_str = await _generate_link_from_host_data(host, xui_uuid)
                if conn_str:
                    links.append(conn_str)
            else:
                # Нет — создаём
                try:
                    result = await create_or_update_key_on_host(
                        host_name=h_name,
                        email=email,
                        days_to_add=duration_days
                    )
                    if result and result.get("connection_string"):
                        # Сохраняем в БД
                        add_new_key(
                            user_id=user_id,
                            host_name=h_name,
                            xui_client_uuid=result["client_uuid"],
                            key_email=email,
                            expiry_timestamp_ms=result["expiry_timestamp_ms"]
                        )
                        links.append(result["connection_string"])
                    else:
                        logger.error(f"Failed to create key on {h_name}")
                except Exception as e:
                    logger.error(f"Exception creating key on {h_name}: {e}")

        return links

    elif host_name:
        # Режим: один конкретный хост
        host_data = get_host(host_name)
        if not host_
            logger.error(f"Requested host '{host_name}' not found.")
            return []

        existing_keys = {key["host_name"]: key for key in get_user_keys(user_id)}
        email = f"user{user_id}@{host_name}"

        if host_name in existing_keys:
            xui_uuid = existing_keys[host_name]["xui_client_uuid"]
            conn_str = await _generate_link_from_host_data(host_data, xui_uuid)
            return [conn_str] if conn_str else []
        else:
            # Создаём ключ на этом хосте
            duration_days = int(get_setting("trial_duration_days") or 1)
            try:
                result = await create_or_update_key_on_host(
                    host_name=host_name,
                    email=email,
                    days_to_add=duration_days
                )
                if result and result.get("connection_string"):
                    add_new_key(
                        user_id=user_id,
                        host_name=host_name,
                        xui_client_uuid=result["client_uuid"],
                        key_email=email,
                        expiry_timestamp_ms=result["expiry_timestamp_ms"]
                    )
                    return [result["connection_string"]]
                else:
                    logger.error(f"Failed to create key on {host_name}")
                    return []
            except Exception as e:
                logger.error(f"Exception creating key on {host_name}: {e}")
                return []

    else:
        # Режим: только существующие (старое поведение)
        user_keys = get_user_keys(user_id=user_id)
        if not user_keys:
            return []

        links = []
        for key in user_keys:
            host_data = get_host(key["host_name"])
            if not host_
                continue
            conn_str = await _generate_link_from_host_data(host_data, key["xui_client_uuid"])
            if conn_str:
                links.append(conn_str)
        return links


async def _generate_link_from_host_data(host_data: dict, user_uuid: str) -> str | None:
    """Вспомогательная функция для генерации ссылки."""
    try:
        api, inbound = login_to_host(
            host_url=host_data['host_url'],
            username=host_data['host_username'],
            password=host_data['host_pass'],
            inbound_id=host_data['host_inbound_id']
        )
        if not inbound:
            logger.error(f"Failed to fetch inbound for {host_data['host_name']}")
            return None

        return get_connection_string(
            inbound=inbound,
            user_uuid=user_uuid,
            host_url=host_data['host_url'],
            remark=host_data['host_name']
        )
    except Exception as e:
        logger.error(f"Error generating link for {host_data['host_name']}: {e}")
        return None
