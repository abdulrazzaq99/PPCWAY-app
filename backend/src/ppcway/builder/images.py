"""What an uploaded image is, read from its own first bytes.

Google checks an image's shape when it is linked, not when it is uploaded:
a landscape image linked as a square one is refused at launch, with the whole
campaign (`ASPECT_RATIO_NOT_ALLOWED`). So the size is read here, the moment
the merchant adds it, and the screen can say "this is 1200 by 628, a landscape
image" before anything goes wrong. PNG, JPEG and GIF only, which is what
Google takes; reading the header needs no imaging library.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Final

#: Google's ceiling for one image asset: 5,120 KB.
MOST_BYTES: Final = 5_120 * 1024

#: The shapes Google asks for, with each one's smallest size (Help 17091269,
#: 9566341). Ratios are compared with a little room, as Google's own are.
SHAPES: Final[dict[str, tuple[float, int, int]]] = {
    "landscape": (1.91, 600, 314),
    "square": (1.0, 300, 300),
    "portrait": (0.8, 480, 600),
    "logo": (1.0, 128, 128),
    "landscape_logo": (4.0, 512, 128),
}


@dataclass(frozen=True, slots=True)
class Picture:
    mime: str
    width: int
    height: int


class NotAnImage(ValueError):
    """The bytes are not a PNG, JPEG or GIF this module can read."""


def read(data: bytes) -> Picture:
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
        width, height = struct.unpack(">II", data[16:24])
        return Picture("image/png", width, height)
    if data[:6] in (b"GIF87a", b"GIF89a") and len(data) >= 10:
        width, height = struct.unpack("<HH", data[6:10])
        return Picture("image/gif", width, height)
    if data.startswith(b"\xff\xd8"):
        return _jpeg(data)
    raise NotAnImage("Google takes PNG, JPEG or GIF images.")


def _jpeg(data: bytes) -> Picture:
    at = 2
    while at + 9 < len(data):
        if data[at] != 0xFF:
            at += 1
            continue
        marker = data[at + 1]
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
            at += 2
            continue
        (length,) = struct.unpack(">H", data[at + 2 : at + 4])
        # Start-of-frame markers carry the size; C4, C8 and CC are not frames.
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            height, width = struct.unpack(">HH", data[at + 5 : at + 9])
            return Picture("image/jpeg", width, height)
        at += 2 + length
    raise NotAnImage("That JPEG has no size in it.")


def fits(picture: Picture, shape: str) -> str:
    """Why the image does not fit the shape, or "" when it does."""
    ratio, least_w, least_h = SHAPES[shape]
    if picture.height == 0:
        return "That image has no height."
    actual = picture.width / picture.height
    if abs(actual - ratio) / ratio > 0.02:
        return f"Google needs a {_ratio(shape)} image here; this one is {picture.width} by {picture.height}."
    if picture.width < least_w or picture.height < least_h:
        return f"Google needs at least {least_w} by {least_h} here; this one is {picture.width} by {picture.height}."
    return ""


def _ratio(shape: str) -> str:
    return {
        "landscape": "1.91:1 landscape",
        "square": "1:1 square",
        "portrait": "4:5 portrait",
        "logo": "1:1 square",
        "landscape_logo": "4:1 landscape",
    }[shape]
