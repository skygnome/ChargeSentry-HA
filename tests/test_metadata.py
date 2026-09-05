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
