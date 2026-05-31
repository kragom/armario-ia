"""
Rotación automática de API keys cuando una alcanza su cuota
"""
import asyncio
from storage.config_store import load_config

_current_index = 0
_lock = asyncio.Lock()


async def _get_keys() -> list[str]:
    config = load_config()
    keys = []
    if config.api_key:
        keys.append(config.api_key)
    if config.api_keys:
        for k in config.api_keys:
            k = k.strip()
            if k and k not in keys:
                keys.append(k)
    return keys


async def get_current_key() -> str:
    global _current_index
    async with _lock:
        keys = await _get_keys()
        if not keys:
            return ""
        return keys[_current_index % len(keys)]


async def rotate_key() -> str:
    global _current_index
    async with _lock:
        _current_index += 1
        keys = await _get_keys()
        if not keys:
            return ""
        return keys[_current_index % len(keys)]


async def get_all_keys() -> list[str]:
    return await _get_keys()
