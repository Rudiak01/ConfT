# config.py
import os
import json

SWITCH = {
    "device_type": "cisco_ios",
    "host": "192.168.1.2",
    "username": "admin",
    "password": "azeAZE123-",
}

# Interfaces à protéger
PROTECTED_INTERFACES = [
    "GigabitEthernet0/1",
    "GigabitEthernet0/2",
    "FastEthernet0/24"
]

# Override dynamically if config.json exists
_dir = os.path.dirname(os.path.abspath(__file__))
_config_json_path = os.path.join(_dir, "config.json")
if os.path.exists(_config_json_path):
    try:
        with open(_config_json_path, "r", encoding="utf-8") as _f:
            _data = json.load(_f)
            if "SWITCH" in _data:
                SWITCH.update(_data["SWITCH"])
            if "PROTECTED_INTERFACES" in _data:
                PROTECTED_INTERFACES = _data["PROTECTED_INTERFACES"]
    except Exception as _e:
        print(f"Warning: Failed to load config.json: {_e}")