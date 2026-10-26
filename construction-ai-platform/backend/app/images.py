"""Image intake: validates, repairs/limits and encodes uploaded construction photos."""
import base64
import io
from dataclasses import dataclass, field
from typing import List

from fastapi import UploadFile
from PIL import Image, ImageStat

from .config import settings
from .errors import AppError

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP", "GIF"}
MAX_SIDE = 1568  # larger images are downscaled (keeps request size and cost down)
MIN_SIDE = 64


@dataclass
class ProcessedImage:
    b64: str
    media_type: str
    width: int
    height: int
    warnings: List[str] = field(default_factory=list)


async def read_image(upload: UploadFile) -> ProcessedImage:
    raw = await upload.read()
    if not raw:
        raise AppError(422, "empty_image", "The uploaded image file is empty.")
    if len(raw) > settings.max_image_mb * 1024 * 1024:
        raise AppError(413, "image_too_large", f"Image is larger than {settings.max_image_mb} MB.")

    try:
        img = Image.open(io.BytesIO(raw))
        fmt = img.format
        img.load()  # forces full decode -> raises on truncated / incomplete files
    except (OSError, ValueError, SyntaxError) as exc:
        msg = str(exc).lower()
        if "truncated" in msg or "broken" in msg or "incomplete" in msg:
            raise AppError(422, "incomplete_image", "The image looks incomplete (truncated upload). Please upload it again.")
        raise AppError(400, "invalid_image", "This file is not a readable image. Use JPG, PNG, WEBP or GIF.")
    except Exception:  # PIL.UnidentifiedImageError and others
        raise AppError(400, "invalid_image", "This file is not a readable image. Use JPG, PNG, WEBP or GIF.")

    if fmt not in ALLOWED_FORMATS:
        raise AppError(415, "unsupported_image_type", f"Image type {fmt} is not supported. Use JPG, PNG, WEBP or GIF.")

    w, h = img.size
    if min(w, h) < MIN_SIDE:
        raise AppError(422, "image_too_small", f"Image is too small ({w}x{h}px). Minimum is {MIN_SIDE}px per side.")

    warnings: List[str] = []
    if max(w, h) < 400:
        warnings.append("Low resolution image - small details (thin cracks, PPE) may be missed.")

    img = img.convert("RGB")
    brightness = ImageStat.Stat(img.convert("L")).mean[0]
    if brightness < 35:
        warnings.append("Image is very dark - results may be unreliable.")
    elif brightness > 225:
        warnings.append("Image is overexposed - results may be unreliable.")

    if max(w, h) > MAX_SIDE:
        img.thumbnail((MAX_SIDE, MAX_SIDE))
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=88)
    nw, nh = img.size
    return ProcessedImage(base64.b64encode(out.getvalue()).decode(), "image/jpeg", nw, nh, warnings)
