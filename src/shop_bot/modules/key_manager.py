import logging
from datetime import datetime, timedelta
from shop_bot.data_manager.database import add_new_key, get_setting, get_keys_for_host, get_user_keys, get_host
from shop_bot.modules.xui_api import create_or_update_key_on_host  # ✅ существует
import urllib.parse

from shop_bot.data_manager.database import get_all_hosts  # ← убедитесь, что она есть или создайте

from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


async def get_existing_vless_links_for_user(user_id: int) -> list[str]:
    """
    Возвращает список VLESS-ссылок ТОЛЬКО для тех хостов,
    на которых у пользователя уже есть запись в vpn_keys.
    Новые ключи НЕ создаются.
    """
    user_keys = get_user_keys(user_id=user_id)
    if not user_keys:
        return []

    links = []
    for key in user_keys:
        host_name = key["host_name"]
        xui_client_uuid = key["xui_client_uuid"]

        host_data = get_host(host_name)
        if not host_
            logger.warning(f"Host '{host_name}' not found for user {user_id}")
            continue

        try:
            from shop_bot.modules.xui_api import login_to_host, get_connection_string
            api, inbound = login_to_host(
                host_url=host_data['host_url'],
                username=host_data['host_username'],
                password=host_data['host_pass'],
                inbound_id=host_data['host_inbound_id']
            )
            if not inbound:
                logger.error(f"Failed to fetch inbound for {host_name}")
                continue

            connection_string = get_connection_string(
                inbound=inbound,
                user_uuid=xui_client_uuid,
                host_url=host_data['host_url'],
                remark=host_name
            )
            if connection_string:
                links.append(connection_string)
            else:
                logger.warning(f"Empty connection string for {host_name} / user {user_id}")

        except Exception as e:
            logger.error(f"Error generating link for {host_name}: {e}")

    return links
