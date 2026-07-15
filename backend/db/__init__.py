from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

db_url = os.getenv("MARIADB_STRING")
if not db_url:
    db_host = os.getenv("DB_HOST", "127.0.0.1")
    db_port = os.getenv("DB_PORT", "3306")
    db_user = os.getenv("DB_USER", "root")
    db_pass = os.getenv("DB_PASS", "test")
    db_name = os.getenv("DB_NAME", "test")
    db_url = f"mysql+pymysql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}?charset=utf8mb4"

SQLALCHEMY_POOL_SIZE = 20
SQLALCHEMY_MAX_OVERFLOW = 300
SQLALCHEMY_POOL_RECYCLE = 1800


class Base(DeclarativeBase):
    pass


engine = create_engine(
    db_url,
    pool_size=SQLALCHEMY_POOL_SIZE,
    max_overflow=SQLALCHEMY_MAX_OVERFLOW,
    pool_pre_ping=True,
    pool_recycle=SQLALCHEMY_POOL_RECYCLE,
)

SessionLocal = sessionmaker(autoflush=False, bind=engine)

