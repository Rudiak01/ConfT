# config.py
import os
import json

# Keep the same dictionary object if it exists to preserve references across modules
if "SWITCH" not in globals():
    SWITCH = {}

SWITCH.clear()
SWITCH.update({
    "device_type": "cisco_ios",
    "host": "192.168.1.2",
    "username": "admin",
    "password": "azeAZE123-",
})

# Keep the same list object for protected interfaces to preserve references
if "PROTECTED_INTERFACES" not in globals():
    PROTECTED_INTERFACES = []

PROTECTED_INTERFACES.clear()
PROTECTED_INTERFACES.extend([
    "GigabitEthernet0/1",
    "GigabitEthernet0/2",
    "FastEthernet0/24"
])

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
                PROTECTED_INTERFACES.clear()
                PROTECTED_INTERFACES.extend(_data["PROTECTED_INTERFACES"])
    except Exception as _e:
        print(f"Warning: Failed to load config.json: {_e}")