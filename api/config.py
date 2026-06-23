import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Database (MariaDB)
    DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT = int(os.getenv("DB_PORT", 3306))
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASS = os.getenv("DB_PASS", "test")
    DB_NAME = os.getenv("DB_NAME", "test")

    SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # SSH (identique sur tous les équipements)
    SSH_USER = os.getenv("SSH_USER", "sdn")
    SSH_PASS = os.getenv("SSH_PASS", "")  # Défini dans .env, pas en dur
    SSH_PORT = int(os.getenv("SSH_PORT", 22))

    # Timeout & retries
    SSH_TIMEOUT = 10
