from __future__ import annotations
import aiohttp

_user_cache: dict[str, int] = {}

async def username_to_user_id(username: str) -> int | None:
    username = (username or "").strip()
    if not username:
        return None
    if username in _user_cache:
        return _user_cache[username]

    url = "https://users.roblox.com/v1/usernames/users"
    payload = {"usernames": [username], "excludeBannedUsers": True}

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, timeout=10) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()

    arr = data.get("data") or []
    if not arr:
        return None

    user_id = arr[0].get("id")
    if isinstance(user_id, int):
        _user_cache[username] = user_id
        return user_id
    return None


async def roblox_headshot_url(user_id: int, size: str = "150x150") -> str | None:
    url = (
        "https://thumbnails.roblox.com/v1/users/avatar-headshot"
        f"?userIds={user_id}&size={size}&format=Png&isCircular=false"
    )
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=10) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()

    arr = data.get("data") or []
    if not arr:
        return None
    return arr[0].get("imageUrl")