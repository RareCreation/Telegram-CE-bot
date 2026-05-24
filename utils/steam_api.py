import aiohttp

from settings.config import STEAM_API_KEY


async def resolve_vanity_url(vanity: str):
    url = "https://api.steampowered.com/ISteamUser/ResolveVanityURL/v1/"
    params = {
        "key": STEAM_API_KEY,
        "vanityurl": vanity
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            data = await resp.json()

    if data["response"]["success"] == 1:
        return data["response"]["steamid"]

    return None