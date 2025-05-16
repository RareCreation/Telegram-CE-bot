import asyncio

from PIL import Image, ImageEnhance
from playwright.async_api import async_playwright
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
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


async def take_screenshot_second(url: str, filename: str):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options
    )

    try:
        driver.get(url)
        await asyncio.sleep(4)

        try:
            driver.execute_script("""
                const banners = document.querySelectorAll("[id*='cookie'], [class*='cookie'], [role*='dialog']");
                banners.forEach(el => el.remove());
            """)
            driver.execute_script("""const container = document.createElement('div');
                                        container.className = 'profile_header_actions';
                                        container.style.display = 'flex';
                                        container.style.gap = '10px';
                                        container.style.position = 'absolute';
                                        container.style.top = '272px';
                                        container.style.left = '1150px';
                                        container.style.zIndex = '9999';
                                        
                                        const btnAddFriend = document.createElement('div');
                                        btnAddFriend.className = 'btn_profile_action btn_medium';
                                        btnAddFriend.style.padding = '3px 15px';
                                        btnAddFriend.style.borderRadius = '2px';
                                        btnAddFriend.style.backgroundColor = 'rgba(0, 0, 0, 0.36)';
                                        btnAddFriend.style.color = 'lightgray';
                                        btnAddFriend.style.display = 'inline-flex';
                                        btnAddFriend.style.alignItems = 'center';
                                        btnAddFriend.style.justifyContent = 'flex-start';
                                        btnAddFriend.style.paddingLeft = '8px';
                                        btnAddFriend.style.height = '23px';
                                        btnAddFriend.style.width = '65px';
                                        btnAddFriend.style.pointerEvents = 'none';
                                        btnAddFriend.style.boxShadow = '0 2px 6px rgba(0, 0, 0, 0.3)';
                                        btnAddFriend.innerText = 'Add Friend';
                                        
                                        const btnMore = document.createElement('div');
                                        btnMore.className = 'btn_profile_action btn_medium';
                                        btnMore.style.padding = '3px 15px';
                                        btnMore.style.borderRadius = '2px';
                                        btnMore.style.backgroundColor = 'rgba(0, 0, 0, 0.36)';
                                        btnMore.style.color = 'lightgray';
                                        btnMore.style.display = 'inline-flex';
                                        btnMore.style.alignItems = 'center';
                                        btnMore.style.gap = '5px';
                                        btnMore.style.height = '23px';
                                        btnMore.style.width = '50px';
                                        btnMore.style.pointerEvents = 'none';
                                        btnMore.style.boxShadow = '0 2px 6px rgba(0, 0, 0, 0.3)';
                                        
                                        const textSpan = document.createElement('span');
                                        textSpan.innerText = 'More...';
                                        textSpan.style.background = 'transparent';
                                        textSpan.style.border = 'none';
                                        textSpan.style.position = 'relative';
                                        textSpan.style.left = '-15px';
                                        
                                        const img = document.createElement('img');
                                        img.src = 'https://community.cloudflare.steamstatic.com/public/images/profile/profile_action_dropdown.png';
                                        img.style.width = '12px';
                                        img.style.height = '12px';
                                        img.style.marginTop = '1px';
                                        img.style.background = 'transparent';
                                        img.style.border = 'none';
                                        img.style.boxShadow = 'none';
                                        img.style.position = 'relative';
                                        img.style.left = '-23px';
                                        
                                        btnMore.appendChild(textSpan);
                                        btnMore.appendChild(img);
                                        
                                        container.appendChild(btnAddFriend);
                                        container.appendChild(btnMore);
                                        document.body.appendChild(container);
        """)

        except Exception as e:
            logger(f"JavaScript cookie removal error: {e}")

        await asyncio.sleep(3)
        driver.save_screenshot(filename)

        img = Image.open(filename)
        width, height = img.size

        cropped_img = img.crop((15, 0, width - 15, height))

        enhancer = ImageEnhance.Brightness(cropped_img)
        darkened_img = enhancer.enhance(0.6)
        darkened_img_rgba = darkened_img.convert("RGBA")


        try:
            friend_img = Image.open("images/friend.png").convert("RGBA")
            position = (
                (darkened_img.width - friend_img.width) // 2,
                (darkened_img.height - friend_img.height) // 2
            )
            darkened_img_rgba.alpha_composite(friend_img, dest=position)
        except Exception as e:
            logger(f"Error overlaying friend.png: {str(e)}")

        try:
            friendq_img = Image.open("images/img.png").convert("RGBA")

            friendq_img = friendq_img.crop((0, 0, friendq_img.width, friendq_img.height - 5))

            position_top_center = (
                (darkened_img.width - friendq_img.width) // 2,
                -18
            )

            darkened_img_rgba.alpha_composite(friendq_img, dest=position_top_center)

        except Exception as e:
            logger(f"Error overlaying img.png: {str(e)}")

        darkened_img_rgba.convert("RGB").save(filename)
    finally:
        driver.quit()



async def take_screenshot(url: str, filename: str):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options
    )

    try:
        driver.get(url)
        await asyncio.sleep(4)

        try:
            driver.execute_script("""
                const banners = document.querySelectorAll("[id*='cookie'], [class*='cookie'], [role*='dialog']");
                banners.forEach(el => el.remove());
            """)
            driver.execute_script("""const container = document.createElement('div');
                                            container.className = 'profile_header_actions';
                                            container.style.display = 'flex';
                                            container.style.gap = '10px';
                                            container.style.position = 'absolute';
                                            container.style.top = '272px';
                                            container.style.left = '1150px';
                                            container.style.zIndex = '9999';
                                            
                                            const btnAddFriend = document.createElement('div');
                                            btnAddFriend.className = 'btn_profile_action btn_medium';
                                            btnAddFriend.style.padding = '3px 15px';
                                            btnAddFriend.style.borderRadius = '2px';
                                            btnAddFriend.style.backgroundColor = 'rgba(0, 0, 0, 0.36)';
                                            btnAddFriend.style.color = 'lightgray';
                                            btnAddFriend.style.display = 'inline-flex';
                                            btnAddFriend.style.alignItems = 'center';
                                            btnAddFriend.style.justifyContent = 'flex-start';
                                            btnAddFriend.style.paddingLeft = '8px';
                                            btnAddFriend.style.height = '23px';
                                            btnAddFriend.style.width = '65px';
                                            btnAddFriend.style.pointerEvents = 'none';
                                            btnAddFriend.style.boxShadow = '0 2px 6px rgba(0, 0, 0, 0.3)';
                                            btnAddFriend.innerText = 'Add Friend';
                                            
                                            const btnMore = document.createElement('div');
                                            btnMore.className = 'btn_profile_action btn_medium';
                                            btnMore.style.padding = '3px 15px';
                                            btnMore.style.borderRadius = '2px';
                                            btnMore.style.backgroundColor = 'rgba(0, 0, 0, 0.36)';
                                            btnMore.style.color = 'lightgray';
                                            btnMore.style.display = 'inline-flex';
                                            btnMore.style.alignItems = 'center';
                                            btnMore.style.gap = '5px';
                                            btnMore.style.height = '23px';
                                            btnMore.style.width = '50px';
                                            btnMore.style.pointerEvents = 'none';
                                            btnMore.style.boxShadow = '0 2px 6px rgba(0, 0, 0, 0.3)';
                                            
                                            const textSpan = document.createElement('span');
                                            textSpan.innerText = 'More...';
                                            textSpan.style.background = 'transparent';
                                            textSpan.style.border = 'none';
                                            textSpan.style.position = 'relative';
                                            textSpan.style.left = '-15px';
                                            
                                            const img = document.createElement('img');
                                            img.src = 'https://community.cloudflare.steamstatic.com/public/images/profile/profile_action_dropdown.png';
                                            img.style.width = '12px';
                                            img.style.height = '12px';
                                            img.style.marginTop = '1px';
                                            img.style.background = 'transparent';
                                            img.style.border = 'none';
                                            img.style.boxShadow = 'none';
                                            img.style.position = 'relative';
                                            img.style.left = '-23px';
                                            
                                            btnMore.appendChild(textSpan);
                                            btnMore.appendChild(img);
                                            
                                            container.appendChild(btnAddFriend);
                                            container.appendChild(btnMore);
                                            document.body.appendChild(container);

        """)

        except Exception as e:
            logger(f"JavaScript cookie removal error: {e}")

        await asyncio.sleep(3)
        driver.save_screenshot(filename)

        img = Image.open(filename)
        width, height = img.size
        cropped_img = img.crop((0, 105, width, height))

        enhancer = ImageEnhance.Brightness(cropped_img)
        darkened_img = enhancer.enhance(0.6)

        try:
            friend_img = Image.open("images/friend.png").convert("RGBA")
            position = (
                (darkened_img.width - friend_img.width) // 2,
                (darkened_img.height - friend_img.height) // 2
            )
            darkened_img_rgba = darkened_img.convert("RGBA")
            darkened_img_rgba.alpha_composite(friend_img, dest=position)
            darkened_img_rgba.convert("RGB").save(filename)
        except Exception as e:
            logger(f"Error overlaying friend.png: {e}")
            darkened_img.save(filename)
    finally:
        driver.quit()
