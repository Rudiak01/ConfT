import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv, set_key

# Load environment variables
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_FILE = os.path.join(BASE_DIR, ".env")

load_dotenv(ENV_FILE)

# Ensure a secret key exists
SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    SECRET_KEY = Fernet.generate_key().decode()
    with open(ENV_FILE, "a") as f:
        f.write(f"\nSECRET_KEY={SECRET_KEY}\n")
    # Also update current env
    os.environ["SECRET_KEY"] = SECRET_KEY

fernet = Fernet(SECRET_KEY.encode())

def encrypt_password(password: str) -> str:
    if not password:
        return ""
    return fernet.encrypt(password.encode()).decode()

def decrypt_password(encrypted_password: str) -> str:
    if not encrypted_password:
        return ""
    try:
        return fernet.decrypt(encrypted_password.encode()).decode()
    except Exception:
        return ""
