import logging
from datetime import datetime, timedelta
from shop_bot.data_manager.database import add_new_key, get_setting, get_keys_for_host, get_user_keys, get_host
from shop_bot.modules.xui_api import create_or_update_key_on_host  # ✅ существует
import urllib.parse

from shop_bot.data_manager.database import get_all_hosts  # ← убедитесь, что она есть или создайте

from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

async def create_keys_on_all_hosts_and_get_links(user_id: int) -> list[str]:
    hosts = get_all_hosts()
    if not hosts:
        logger.warning("No hosts available for subscription.")
        return []

    links = []
    duration_days = int(get_setting("trial_duration_days") or 1)

    for host in hosts:
        host_name = host["host_name"]
        email = f"user{user_id}@{host_name}"

        # === 🔍 Проверяем, есть ли уже ключ в БД для этого user_id + host_name ===
        existing_keys = get_user_keys(user_id=user_id)
        existing_key_for_host = None
        for key in existing_keys:
            if key["host_name"] == host_name:
                existing_key_for_host = key
                break

        try:
            if existing_key_for_host:
                # === Ключ уже есть — НЕ обновляем, просто генерируем ссылку ===
                host_data = get_host(host_name)
                if not host_data:
                    logger.error(f"Host '{host_name}' not found in DB.")
                    continue

                from shop_bot.modules.xui_api import login_to_host, get_connection_string
                api, inbound = login_to_host(
                    host_url=host_data['host_url'],
                    username=host_data['host_username'],
                    password=host_data['host_pass'],
                    inbound_id=host_data['host_inbound_id']
                )
                if not inbound:
                    logger.error(f"Failed to get inbound for {host_name}")
                    continue

                connection_string = get_connection_string(
                    inbound=inbound,
                    client_uuid=existing_key_for_host["xui_client_uuid"],
                    host_url=host_data['host_url'],
                    remark=host_name
                )
                if connection_string:
                    links.append(connection_string)
                else:
                    logger.warning(f"Empty connection string for existing key {email}")

            else:
                # === Ключа нет — создаём новый и добавляем в БД ===
                result = await create_or_update_key_on_host(
                    host_name=host_name,
                    email=email,
                    days_to_add=duration_days
                )
                if not result or not result.get("connection_string"):
                    logger.error(f"Failed to create key on {host_name}")
                    continue

                # Сохраняем в БД
                add_new_key(
                    user_id=user_id,
                    host_name=host_name,
                    xui_client_uuid=result["client_uuid"],
                    key_email=email,
                    expiry_timestamp_ms=result["expiry_timestamp_ms"]
                )
                links.append(result["connection_string"])

        except Exception as e:
            logger.error(f"Exception processing key on {host_name}: {e}")

    return links

