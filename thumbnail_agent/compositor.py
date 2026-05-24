from pathlib import Path

from PIL import Image

ASSETS_DIR = Path(__file__).parent.parent / "assets" / "logos"

# logo height as fraction of thumbnail height
_LOGO_H_RATIO = 0.18
_PADDING_RATIO = 0.04


def composite_logos(image_path: str, brand_elements: list[str]) -> None:
    """Overlay brand logo PNGs onto a generated thumbnail in-place.

    Logos are placed bottom-right, stacked left. Missing assets are skipped silently.
    """
    if not brand_elements:
        return

    resolved = [p for asset in brand_elements if (p := _resolve(asset)) is not None]
    if not resolved:
        return

    base = Image.open(image_path).convert("RGBA")
    w, h = base.size
    logo_h = int(h * _LOGO_H_RATIO)
    padding = int(h * _PADDING_RATIO)

    x_cursor = w - padding
    for logo_path in reversed(resolved):
        logo = Image.open(logo_path).convert("RGBA")
        scale = logo_h / logo.height
        new_w = max(1, int(logo.width * scale))
        logo = logo.resize((new_w, logo_h), Image.LANCZOS)
        x = x_cursor - logo.width
        y = h - logo_h - padding
        base.paste(logo, (x, y), logo)
        x_cursor = x - padding

    base.convert("RGB").save(image_path, "PNG")


def _resolve(asset: str) -> Path | None:
    """Return path to logo file, or None if not found."""
    direct = Path(asset)
    if direct.exists():
        return direct
    via_assets = ASSETS_DIR / Path(asset).name
    if via_assets.exists():
        return via_assets
    return None
