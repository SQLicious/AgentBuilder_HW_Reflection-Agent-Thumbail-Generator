from pathlib import Path
from unittest.mock import patch

from PIL import Image


def _make_png(path: Path, size=(1536, 1024)):
    img = Image.new("RGBA", size, (50, 50, 50, 255))
    img.save(str(path), "PNG")


def test_compositor_overlays_logo_when_asset_exists(tmp_path):
    base_path = tmp_path / "iter_1.png"
    _make_png(base_path)

    logo_dir = tmp_path / "logos"
    logo_dir.mkdir()
    logo = Image.new("RGBA", (200, 200), (255, 0, 0, 200))
    logo.save(str(logo_dir / "claude.png"))

    from thumbnail_agent.compositor import composite_logos
    with patch("thumbnail_agent.compositor.ASSETS_DIR", logo_dir):
        composite_logos(str(base_path), ["claude.png"])

    result = Image.open(str(base_path))
    assert result.size == (1536, 1024)


def test_compositor_skips_missing_asset(tmp_path):
    base_path = tmp_path / "iter_1.png"
    _make_png(base_path)

    from thumbnail_agent.compositor import composite_logos
    composite_logos(str(base_path), ["nonexistent_logo.png"])

    assert Image.open(str(base_path)).size == (1536, 1024)


def test_compositor_noop_on_empty_list(tmp_path):
    base_path = tmp_path / "iter_1.png"
    _make_png(base_path)
    original_bytes = base_path.read_bytes()

    from thumbnail_agent.compositor import composite_logos
    composite_logos(str(base_path), [])

    assert base_path.read_bytes() == original_bytes


def test_brand_elements_parsed_from_strategy_json():
    from thumbnail_agent.nodes import _brand_elements
    strategy = '{"brand_elements": ["claude.png", "openai.png"], "thumbnail_text": "AI WAR"}'
    assert _brand_elements(strategy) == ["claude.png", "openai.png"]


def test_brand_elements_returns_empty_on_bad_json():
    from thumbnail_agent.nodes import _brand_elements
    assert _brand_elements("not json") == []
    assert _brand_elements("") == []
    assert _brand_elements('{"no_brand_key": true}') == []
