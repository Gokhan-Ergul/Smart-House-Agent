import json

from smart_house_agent.persistence.home_status import HomeStatusStore


def test_home_status_load_save_roundtrip(tmp_path):
    path = tmp_path / "home_status.json"
    path.write_text(
        json.dumps(
            {
                "light": "off",
                "tv": "on",
                "curtain": "closed",
                "door_lock": "unlocked",
                "thermostat_mode": "on",
                "main_water_valve": "closed",
            }
        ),
        encoding="utf-8",
    )
    store = HomeStatusStore(path)
    data = store.load()
    assert data["light"] == "off"
    store.update_device("light", "on")
    store.save()
    again = json.loads(path.read_text(encoding="utf-8"))
    assert again["light"] == "on"


def test_home_status_thermostat_alias(tmp_path):
    path = tmp_path / "home_status.json"
    path.write_text(
        json.dumps(
            {
                "light": "off",
                "tv": "off",
                "curtain": "closed",
                "door_lock": "locked",
                "thermostat_mode": "off",
                "main_water_valve": "closed",
            }
        ),
        encoding="utf-8",
    )
    store = HomeStatusStore(path)
    store.load()
    store.update_device("main_thermostat", "on")
    assert store.data["thermostat_mode"] == "on"
