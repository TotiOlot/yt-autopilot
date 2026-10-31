"""Paso 6 — Miniatura 1280x720: foto de fondo + texto grande con contorno (estilo documental)."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from .common import ASSETS

W, H = 1280, 720
YELLOW = (255, 214, 0)


def _font(size: int):
    for f in list((ASSETS / "fonts").glob("*.ttf")) + [Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")]:
        try:
            return ImageFont.truetype(str(f), size)
        except OSError:
            continue
    return ImageFont.load_default()


def _fit_cover(img: Image.Image) -> Image.Image:
    r = max(W / img.width, H / img.height)
    img = img.resize((int(img.width * r) + 1, int(img.height * r) + 1), Image.LANCZOS)
    x = (img.width - W) // 2; y = (img.height - H) // 2
    return img.crop((x, y, x + W, y + H))


def _wrap(text: str, font, max_w: int, draw) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for wd in words:
        test = f"{cur} {wd}".strip()
        if draw.textlength(test, font=font) <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


def make_thumbnail(bg_path: Path, text: str, out: Path) -> Path:
    bg = _fit_cover(Image.open(bg_path).convert("RGB"))
    bg = ImageEnhance.Contrast(bg).enhance(1.25)
    bg = ImageEnhance.Color(bg).enhance(1.15)
    # degradado oscuro a la izquierda para que el texto se lea
    shade = Image.new("L", (W, H))
    sd = ImageDraw.Draw(shade)
    for x in range(W):
        sd.line([(x, 0), (x, H)], fill=int(215 * max(0, 1 - x / (W * 0.75))))
    bg = Image.composite(Image.new("RGB", (W, H), (0, 0, 0)), bg, shade)

    draw = ImageDraw.Draw(bg)
    text = text.upper()
    max_w = int(W * 0.58)
    size = 170
    while size > 60:
        font = _font(size)
        lines = _wrap(text, font, max_w, draw)
        line_h = int(size * 1.05)
        if len(lines) * line_h <= H * 0.78 and all(draw.textlength(l, font=font) <= max_w for l in lines):
            break
        size -= 6
    y = (H - len(lines) * line_h) // 2
    for i, line in enumerate(lines):
        color = YELLOW if i == len(lines) - 1 else (255, 255, 255)   # última línea en amarillo
        draw.text((60, y), line, font=font, fill=color, stroke_width=max(4, size // 18), stroke_fill=(0, 0, 0))
        y += line_h
    bg = bg.filter(ImageFilter.UnsharpMask(radius=2, percent=60))
    bg.save(out, "JPEG", quality=92)
    return out
