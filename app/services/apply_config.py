# app/services/apply_config.py
from back.apply_config import apply_device_config as _apply_device_config

def deploy_config(device_ip: str, config_data: dict) -> tuple[bool, str]:
    """
    Wrapper vers back/apply_config.py → apply_device_config()
    Retourne (success: bool, message: str)
    """
    # On construit les params de connexion à partir du device IP
    # ⚠️ En prod : récupérer les credentials depuis la BDD ou un vault
    from app.schemas.network import DeviceCredentials

    creds = DeviceCredentials(
        host=device_ip,
        username="admin",  # À remplacer par une logique réelle (ex: DB lookup)
        password="password",
        device_type="cisco_ios"
    ).model_dump()

    success, msg = _apply_device_config(creds, config_data)
    return success, msg
