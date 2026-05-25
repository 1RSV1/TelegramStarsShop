from sqlalchemy import BigInteger, String, Integer, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
import datetime
from sqlalchemy.sql import func




engine = create_async_engine(url= "", pool_pre_ping=True, pool_recycle=3600)
async_session = async_sessionmaker(engine)

class Base(AsyncAttrs, DeclarativeBase):
    pass

class Stars(Base):
    __tablename__ = "stars" 
    id: Mapped[int] = mapped_column(primary_key= True)
    tg_id: Mapped[int] = mapped_column(BigInteger)
    tg_username: Mapped[str] = mapped_column(String(125))
    deposits: Mapped[int] = mapped_column(Integer, default=0)
    stars: Mapped[int] = mapped_column(Integer, default=0)
    gifts: Mapped[str] = mapped_column(String(250), default='')
    aff: Mapped[int] = mapped_column(BigInteger, default=0)
    balance: Mapped[int] = mapped_column(Integer, default=0)
    ton: Mapped[int] = mapped_column(Integer, default=0)


class Purchases(Base):
    __tablename__ = "purchases" 
    id: Mapped[int] = mapped_column(primary_key= True)
    tg_id: Mapped[int] = mapped_column(BigInteger)
    tg_username: Mapped[str] = mapped_column(String(125))
    amount: Mapped[int] = mapped_column(Integer, default=0)
    stars: Mapped[int] = mapped_column(Integer, default=0)
    ton: Mapped[int] = mapped_column(Integer, default=0) 
    net: Mapped[int] = mapped_column(Integer, default=0)
    share: Mapped[int] = mapped_column(Integer, default=0)
    affiliate: Mapped[int] = mapped_column(BigInteger, default=0)
    createdAt: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    updatedAt: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=func.now())


async def async_main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def async_shut_main():
    await engine.dispose()        

