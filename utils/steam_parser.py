import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from utils.logger_util import logger


def resolve_image_url(img_src: str, profile_url: str) -> str:
    if not img_src:
        return None

    parsed_src = urlparse(img_src)

    if parsed_src.scheme in ("http", "https"):
        return img_src

    parsed_profile = urlparse(profile_url)
    base_url = f"{parsed_profile.scheme}://{parsed_profile.netloc}"

    if not profile_url.endswith("/"):
        profile_url += "/"

    full_url = urljoin(profile_url, img_src)

    if not full_url.startswith("http"):
        full_url = urljoin(base_url + "/", img_src)

    return full_url


def parse_steam_profile_images(profile_url: str) -> tuple:
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(profile_url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        avatar_container = soup.find("div", class_="playerAvatarAutoSizeInner")
        if not avatar_container:
            return None, None, None

        persona_name_el = soup.find("span", class_="actual_persona_name")
        persona_name = persona_name_el.get_text(strip=True) if persona_name_el else "Unknown"

        frame_url = None
        frame_block = avatar_container.find("div", class_="profile_avatar_frame")
        if frame_block:
            img_tag = frame_block.find("img")
            if img_tag and img_tag.get("src"):
                frame_url = resolve_image_url(img_tag["src"], profile_url)
            else:
                source = frame_block.find("source")
                if source and source.get("srcset"):
                    frame_url = resolve_image_url(source["srcset"], profile_url)

        avatar_url = None
        pictures = avatar_container.find_all("picture")
        if len(pictures) > 1:
            avatar_pic = pictures[1]
            img_tag = avatar_pic.find("img")
            if img_tag and img_tag.get("src"):
                avatar_url = resolve_image_url(img_tag["src"], profile_url)
            else:
                source = avatar_pic.find("source")
                if source and source.get("srcset"):
                    avatar_url = resolve_image_url(source["srcset"], profile_url)

        return frame_url, avatar_url, persona_name

    except Exception as e:
        logger(f"Error parsing Steam profile: {e}")
        return None, None, None


def extract_steam_id(url: str) -> str:
    match = re.fullmatch(r"https?://steamcommunity\.com/profiles/(\d{17})/?", url)
    return match.group(1) if match else None