from pydantic import BaseModel

class node(BaseModel):
    label: str
    link_count: int
    color: str



from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import base, relationship, Mapped, mapped_column
from sqlalchemy import create_engine, String
from sqlalchemy.orm import sessionmaker
engine = create_engine("mysql+pymysql://root:test@127.0.0.1:3306/test")

class Base(DeclarativeBase):
    pass

class TableNode(Base):
    __tablename__ = "user_account"
    id: Mapped[int] = mapped_column(primary_key=True)

    label: Mapped[str] = mapped_column(String(50))
    link_count: Mapped[int]
    color: Mapped[str] = mapped_column(String(30))


Base.metadata.create_all(engine)

Session = sessionmaker(engine,autoflush=False)