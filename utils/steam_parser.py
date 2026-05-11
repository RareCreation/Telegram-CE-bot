import re
import requests

from io import BytesIO
from PIL import Image
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

from utils.logger_util import logger


def get_requests_session():
    session = requests.Session()

    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/135.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,"
            "application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Referer": "https://steamcommunity.com/"
    })

    return session


def resolve_image_url(img_src: str, profile_url: str) -> str:
    if not img_src:
        return None

    parsed = urlparse(img_src)

    if parsed.scheme in ("http", "https"):
        return img_src

    return urljoin(profile_url, img_src)


def extract_image_url(tag):
    if not tag:
        return None

    src = tag.get("src")

    if src:
        return src.strip()

    srcset = tag.get("srcset")

    if srcset:
        return srcset.split(",")[0].split()[0].strip()

    return None


def parse_steam_profile_images(profile_url: str):
    try:
        session = get_requests_session()

        response = session.get(
            profile_url,
            timeout=20,
            allow_redirects=True
        )

        logger.debug(
            f"GET {profile_url} -> {response.status_code}"
        )

        if response.status_code != 200:
            logger.error(
                f"HTTP {response.status_code} for {profile_url}"
            )
            return None, None, None

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        avatar_container = soup.find(
            "div",
            class_="playerAvatarAutoSizeInner"
        )

        if not avatar_container:
            logger.error(
                "playerAvatarAutoSizeInner not found"
            )
            return None, None, None

        persona_name = "Unknown"

        persona_name_el = soup.find(
            "span",
            class_="actual_persona_name"
        )

        if persona_name_el:
            persona_name = persona_name_el.get_text(
                strip=True
            )

        frame_url = None

        frame_block = avatar_container.find(
            "div",
            class_="profile_avatar_frame"
        )

        if frame_block:
            picture = frame_block.find("picture")

            if picture:
                img_tag = picture.find("img")

                frame_src = extract_image_url(img_tag)

                if not frame_src:
                    source_tag = picture.find("source")
                    frame_src = extract_image_url(source_tag)

                if frame_src:
                    frame_url = resolve_image_url(
                        frame_src,
                        profile_url
                    )

        avatar_url = None

        pictures = avatar_container.find_all("picture")

        for picture in pictures:
            parent = picture.parent

            if parent and (
                "profile_avatar_frame"
                in parent.get("class", [])
            ):
                continue

            img_tag = picture.find("img")

            avatar_src = extract_image_url(img_tag)

            if not avatar_src:
                source_tag = picture.find("source")
                avatar_src = extract_image_url(source_tag)

            if avatar_src:
                avatar_url = resolve_image_url(
                    avatar_src,
                    profile_url
                )
                break

        logger.debug(
            f"""
            Persona: {persona_name}
            Avatar: {avatar_url}
            Frame: {frame_url}
            """
        )

        return frame_url, avatar_url, persona_name

    except Exception as e:
        logger.error(
            f"Error parsing Steam profile: {e}"
        )
        return None, None, None


def download_image(session, url):
    response = session.get(
        url,
        timeout=15,
        headers={
            "Referer": "https://si.team-uz.com/"
        }
    )

    logger.debug(
        f"Downloading image {url} -> {response.status_code}"
    )

    if response.status_code != 200:
        raise ValueError(
            f"Image request failed: {response.status_code}"
        )

    content_type = response.headers.get(
        "Content-Type",
        ""
    )

    if "image" not in content_type:
        raise ValueError(
            f"Invalid content-type: {content_type}"
        )

    return Image.open(
        BytesIO(response.content)
    ).convert("RGBA")


def extract_steam_id(url: str) -> str:
    match = re.fullmatch(
        r"https?://steamcommunity\.com/profiles/(\d{17})/?",
        url
    )

    return match.group(1) if match else None