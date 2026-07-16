from netmiko import ConnectHandler
try:
    from .config import SWITCH
except ImportError:
    from config import SWITCH

def connect(connection_params=None):
    if connection_params is None:
        connection_params = SWITCH
    
    params = connection_params.copy()
    if "read_timeout_override" not in params:
        params["read_timeout_override"] = 60
    if "conn_timeout" not in params:
        params["conn_timeout"] = 20

    connection = ConnectHandler(**params)
    try:
        connection.enable()
    except Exception:
        pass
    if params.get("device_type", "cisco_ios") == "cisco_ios":
        try:
            connection.send_command("terminal length 0")
        except Exception:
            pass
    return connection