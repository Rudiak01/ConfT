from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

SQLALCHEMY_POOL_SIZE = 20
SQLALCHEMY_MAX_OVERFLOW = 300
SQLALCHEMY_POOL_RECYCLE = 1800


class Base(DeclarativeBase):
    pass


engine = create_engine(
    "mysql+pymysql://root:test@127.0.0.1:3306/test?charset=utf8mb4",
    pool_size=SQLALCHEMY_POOL_SIZE,
    max_overflow=SQLALCHEMY_MAX_OVERFLOW,
    pool_pre_ping=True,
    pool_recycle=SQLALCHEMY_POOL_RECYCLE,
)

SessionLocal = sessionmaker(autoflush=False, bind=engine)