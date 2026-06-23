import os

class Config:
    # Database (MariaDB)
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", 3306))
    DB_USER = os.getenv("DB_USER", "sdn_user")
    DB_PASS = os.getenv("DB_PASS", "sdn_pass")
    DB_NAME = os.getenv("DB_NAME", "sdn_db")

    SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # SSH (identique sur tous les équipements)
    SSH_USER = os.getenv("SSH_USER", "sdn")
    SSH_PASS = os.getenv("SSH_PASS", "password123")  # ou clé privée
    SSH_PORT = int(os.getenv("SSH_PORT", 22))

    # Timeout & retries
    SSH_TIMEOUT = 10
