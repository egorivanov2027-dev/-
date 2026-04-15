# remnawave.py — обёртка для REST API панели Remnawave
# Предоставляет функции: create_user, get_user, extend_user

import logging
from datetime import datetime, timedelta, timezone

import aiohttp
import config

log = logging.getLogger(__name__)


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {config.PANEL_TOKEN}",
        "Content-Type": "application/json",
    }


async def create_user(
    username: str,
    days: int,
    devices: int,
    traffic_gb: int,
) -> dict | None:
    """Создаёт пользователя в Remnawave и возвращает его данные."""
    expire_ms     = int((datetime.now(timezone.utc) + timedelta(days=days)).timestamp() * 1000)
    traffic_bytes = traffic_gb * 1024 ** 3

    body = {
        "username":            username,
        "trafficLimitBytes":   traffic_bytes,
        "expireAt":            expire_ms,
        "activateAllInbounds": True,
        "hwidDeviceLimit":     devices,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{config.PANEL_URL}/api/users",
                json=body,
                headers=_headers(),
                timeout=aiohttp.ClientTimeout(total=20),
            ) as resp:
                data = await resp.json()
                if resp.status in (200, 201):
                    return data.get("response", data)
                log.error("create_user HTTP %s: %s", resp.status, data)
                return None
    except Exception as exc:
        log.error("create_user exception: %s", exc)
        return None


async def get_user(uuid: str) -> dict | None:
    """Возвращает данные пользователя по UUID или None."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{config.PANEL_URL}/api/users/{uuid}",
                headers=_headers(),
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("response", data)
                return None
    except Exception as exc:
        log.error("get_user exception: %s", exc)
        return None


async def extend_user(uuid: str, days: int) -> dict | None:
    """Продлевает подписку пользователя на указанное количество дней."""
    # Берём текущее время истечения из панели
    user = await get_user(uuid)
    if not user:
        return None

    current_expire_ms = user.get("expireAt") or 0
    now_ms            = int(datetime.now(timezone.utc).timestamp() * 1000)
    base_ms           = max(current_expire_ms, now_ms)
    new_expire_ms     = base_ms + int(timedelta(days=days).total_seconds() * 1000)

    body = {"expireAt": new_expire_ms}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.patch(
                f"{config.PANEL_URL}/api/users/{uuid}",
                json=body,
                headers=_headers(),
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("response", data)
                log.error("extend_user HTTP %s", resp.status)
                return None
    except Exception as exc:
        log.error("extend_user exception: %s", exc)
        return None
