from netmiko import ConnectHandler
try:
    from .config import SWITCH
except ImportError:
    from config import SWITCH

def connect(connection_params=None):
    if connection_params is None:
        connection_params = SWITCH
    connection = ConnectHandler(**connection_params)
    try:
        connection.enable()
    except Exception:
        pass
    if connection_params.get("device_type", "cisco_ios") == "cisco_ios":
        try:
            connection.send_command("terminal length 0")
        except Exception:
            pass
    return connection