import logging
from datetime import datetime, timedelta
from shop_bot.data_manager.database import add_new_key, get_setting
from shop_bot.modules.xui_api import create_or_update_key_on_host  # ✅ существует

logger = logging.getLogger(__name__)

# Замените это на ваш способ получения списка хостов
# Например: from shop_bot.data_manager.database import get_all_hosts
# Или импортируйте из конфига
from shop_bot.data_manager.database import get_all_hosts  # ← убедитесь, что она есть или создайте

from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

async def create_keys_on_all_hosts_and_get_proxies(user_id: int) -> list[dict]:
    hosts = get_all_hosts()
    if not hosts:
        logger.warning("No hosts found for subscription!")
        return []

    proxies = []
    now = datetime.now()
    duration_days = int(get_setting("trial_duration_days") or 1)
    expiry_timestamp = int((now + timedelta(days=duration_days)).timestamp())

    for host in hosts:
        host_name = host.get("host_name")
        if not host_name:
            logger.error("Host missing 'host_name', skipping.")
            continue

        try:
            email = f"{user_id}_{int(now.timestamp())}@{host_name}"

            # Создаём ключ на хосте
            proxy_config = await create_or_update_key_on_host(
                host_name=host_name,
                email=email,
                days_to_add=duration_days
            )

            # Поддерживаем оба варианта: "uuid" и "client_uuid"
            uuid_val = None
            if proxy_config:
                uuid_val = proxy_config.get("uuid") or proxy_config.get("client_uuid")
            if not uuid_val:
                logger.error(f"Key creation succeeded on x-ui, but UUID is missing for {host_name}. Result: {proxy_config}")
                continue

            # Обязательные параметры хоста
            address = host.get("address")
            port = host.get("port")
            if not address or not port:
                logger.error(f"Host '{host_name}' missing 'address' or 'port', skipping.")
                continue

            # Опциональные параметры с безопасными значениями по умолчанию
            network = host.get("network", "tcp")
            tls = host.get("tls", True)
            sni = host.get("sni") or address
            flow = host.get("flow")  # может быть None или строка
            path = host.get("path", "/")
            host_header = host.get("host_header") or (sni if tls else address)
            fingerprint = host.get("fingerprint", "chrome")
            display_name = host.get("display_name") or host_name

            # Формируем прокси для Clash Meta
            proxy = {
                "name": display_name,
                "type": "vless",
                "server": address,
                "port": port,
                "uuid": uuid_val,
                "network": network,
                "tls": bool(tls),
                "udp": True,
                "skip-cert-verify": True,
            }

            # TLS-настройки
            if tls:
                proxy["servername"] = sni
                proxy["fingerprint"] = fingerprint

            # WebSocket
            if network == "ws":
                proxy["ws-opts"] = {
                    "path": path,
                    "headers": {"Host": host_header}
                }

            # Flow (только если задан и поддерживается)
            if flow:
                proxy["flow"] = flow

            # Сохраняем в БД
            add_new_key(
                user_id=user_id,
                host_name=host_name,
                client_id=uuid_val,
                email=email,
                expiry=int(expiry_timestamp * 1000)
            )

            proxies.append(proxy)

        except Exception as e:
            logger.error(f"Unexpected error creating key on {host_name} for {user_id}: {e}", exc_info=True)
            continue

    return proxies