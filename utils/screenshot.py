import asyncio
from playwright.async_api import async_playwright

from utils.logger_util import logger

async def capture_steam_profile(url: str) -> str | None:
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.goto(url)
            await page.set_viewport_size({"width": 1920, "height": 1080})
            await asyncio.sleep(3)
            path = f"steam_screenshot.png"
            await page.screenshot(path=path, full_page=True)
            await browser.close()
            return path
    except Exception as e:
        logger("Error while creating screenshot:", e)
        return None
