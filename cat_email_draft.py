#!/usr/bin/env python3
"""
Fetches a random cat picture, uses Claude vision to identify the cat's color,
then opens a draft email with subject "[Color] Cat".

Requirements:
    pip install requests Pillow anthropic

Usage:
    python cat_email_draft.py
"""

import base64
import subprocess
import sys
import urllib.parse
from io import BytesIO

import anthropic
import requests
from PIL import Image


CAT_API_URL = "https://api.thecatapi.com/v1/images/search"


def get_random_cat() -> tuple[str, str]:
    """Return (image_url, image_id) for a random cat from The Cat API."""
    resp = requests.get(CAT_API_URL, timeout=10)
    resp.raise_for_status()
    item = resp.json()[0]
    return item["url"], item["id"]


def download_as_jpeg_b64(image_url: str, max_size: int = 512) -> str:
    """
    Download image, resize to fit within max_size, convert to JPEG,
    and return as a base64 string. Keeps the payload small for the API.
    """
    resp = requests.get(image_url, timeout=15)
    resp.raise_for_status()

    img = Image.open(BytesIO(resp.content)).convert("RGB")
    img.thumbnail((max_size, max_size), Image.LANCZOS)

    buf = BytesIO()
    img.save(buf, format="JPEG", quality=80)
    return base64.standard_b64encode(buf.getvalue()).decode()


def identify_cat_color(image_b64: str) -> str:
    """Ask Claude to identify the dominant color of the cat in the image."""
    client = anthropic.Anthropic()
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=64,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": image_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            "What is the dominant color of the cat in this image? "
                            "Reply with a single color word only (e.g. Orange, Black, White, "
                            "Gray, Brown, Tabby, Calico, Ginger, Cream, Blue). "
                            "No punctuation, no explanation."
                        ),
                    },
                ],
            }
        ],
    )
    return message.content[0].text.strip().title()


def open_email_draft(subject: str, body: str) -> None:
    """Open the system default mail client with a pre-filled draft."""
    mailto = "mailto:?subject={}&body={}".format(
        urllib.parse.quote(subject),
        urllib.parse.quote(body),
    )
    # xdg-open (Linux), open (macOS), start (Windows)
    for cmd in (["xdg-open", mailto], ["open", mailto], ["cmd", "/c", "start", "", mailto]):
        try:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
        except FileNotFoundError:
            continue
    print("\nNo email client opener found. Copy this mailto link manually:")
    print(mailto)


def main() -> int:
    print("Fetching a random cat image...")
    image_url, image_id = get_random_cat()
    print(f"  URL : {image_url}")
    print(f"  ID  : {image_id}")

    print("Downloading and preparing image...")
    image_b64 = download_as_jpeg_b64(image_url)

    print("Asking Claude to identify the cat's color...")
    color = identify_cat_color(image_b64)
    print(f"  Color: {color}")

    subject = f"{color} Cat"
    body = (
        f"Check out this {color.lower()} cat!\n\n"
        f"{image_url}"
    )

    print(f'\nOpening email draft — Subject: "{subject}"')
    open_email_draft(subject, body)
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
