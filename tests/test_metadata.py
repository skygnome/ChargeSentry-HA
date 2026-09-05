"""Static checks over the integration's metadata files.

hassfest covers these in CI; keeping them here means a missing translation
fails fast locally too.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from custom_components.chargesentry_rest import binary_sensor, sensor
from custom_components.chargesentry_rest.const import PLATFORMS

COMPONENT = Path("custom_components/chargesentry_rest")


def _load_json(name: str) -> dict:
    return json.loads((COMPONENT / name).read_text())


def test_translations_match_strings() -> None:
    """translations/en.json is a copy of strings.json."""
    assert _load_json("strings.json") == _load_json("translations/en.json")


def test_manifest_is_well_formed() -> None:
    """The manifest carries everything HACS and hassfest need."""
    manifest = _load_json("manifest.json")
    for key in ("domain", "name", "version", "documentation", "codeowners"):
        assert manifest.get(key), f"manifest is missing {key}"
    assert manifest["domain"] == "chargesentry_rest"
    assert manifest["config_flow"] is True


def test_every_platform_module_exists() -> None:
    """Each platform listed in const.py has a module."""
    for platform in PLATFORMS:
        assert (COMPONENT / f"{platform}.py").is_file()


def test_entity_translation_keys_are_defined() -> None:
    """Every translation_key used by an entity description is translated."""
    strings = _load_json("strings.json")["entity"]

    for description in sensor.SENSORS:
        assert description.translation_key in strings["sensor"], (
            f"sensor {description.key} has no translation"
        )
    for description in binary_sensor.BINARY_SENSORS:
        assert description.translation_key in strings["binary_sensor"], (
            f"binary_sensor {description.key} has no translation"
        )
    assert "charging" in strings["switch"]


def test_enum_sensor_options_are_all_translated() -> None:
    """Every status the API can return has a display name."""
    strings = _load_json("strings.json")["entity"]["sensor"]["status"]["state"]
    status = next(d for d in sensor.SENSORS if d.key == "status")
    for option in status.options:
        assert option in strings, f"status {option} has no translation"


def test_services_yaml_matches_strings() -> None:
    """services.yaml and its translations describe the same services and fields."""
    services = yaml.safe_load((COMPONENT / "services.yaml").read_text())
    strings = _load_json("strings.json")["services"]

    assert set(services) == set(strings)
    for name, definition in services.items():
        assert set(definition.get("fields", {})) == set(
            strings[name].get("fields", {})
        ), f"field mismatch for service {name}"


def test_icons_reference_known_entities() -> None:
    """icons.json only names entities and services that exist."""
    icons = _load_json("icons.json")
    strings = _load_json("strings.json")

    for domain, entries in icons["entity"].items():
        assert set(entries) <= set(strings["entity"][domain])
    assert set(icons["services"]) == set(strings["services"])


def test_shipped_brand_images_meet_the_specification() -> None:
    """The brand/ directory HA reads must satisfy the brands image spec.

    Home Assistant 2026.3+ serves these files directly out of the integration
    directory, applying the same rules as the brands repository: icons exactly
    square at 256/512, and a logo whose *shortest* side is 128-256 (256-512 for
    @2x). Getting a size wrong means a silently broken image in the UI.
    """
    from PIL import Image

    brand = COMPONENT / "brand"

    for name, size in (("icon.png", 256), ("icon@2x.png", 512)):
        with Image.open(brand / name) as image:
            assert image.size == (size, size), f"{name} must be {size}x{size}"
            assert image.mode == "RGBA", f"{name} must have an alpha channel"

    for name, low, high in (("logo.png", 128, 256), ("logo@2x.png", 256, 512)):
        with Image.open(brand / name) as image:
            shortest = min(image.size)
            assert low <= shortest <= high, (
                f"{name} shortest side is {shortest}, must be {low}-{high}"
            )
            assert image.mode == "RGBA", f"{name} must have an alpha channel"


def test_brand_images_are_trimmed() -> None:
    """No transparent border, beyond the padding that squares an icon."""
    from PIL import Image

    brand = COMPONENT / "brand"

    for name in ("logo.png", "logo@2x.png"):
        with Image.open(brand / name) as image:
            assert image.getbbox() == (0, 0, *image.size), f"{name} is not trimmed"

    # An icon is a landscape badge on a square canvas, so it is trimmed
    # horizontally only; vertical bands are unavoidable.
    for name in ("icon.png", "icon@2x.png"):
        with Image.open(brand / name) as image:
            left, _top, right, _bottom = image.getbbox()
            assert (left, right) == (0, image.width), f"{name} has a side border"
