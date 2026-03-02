
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, DateTime, Text, Boolean
from datetime import datetime
from config import settings

engine = create_async_engine(settings.DB_PATH, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), default="general")
    total_chunks: Mapped[int] = mapped_column(Integer, default=0)
    total_pages: Mapped[int] = mapped_column(Integer, default=0)
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    summary: Mapped[str] = mapped_column(Text, default="")
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="user")  # admin | user
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _create_default_users()


async def _create_default_users():
    """Crea usuarios por defecto."""
    from core.security import hash_password
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select

        # 🔥 VULNERABILITY: Hardcoded admin credentials in source code
        defaults = [
            {"username": "admin", "password": "vertex2025", "role": "admin"},
            {"username": "analyst", "password": "analyst123", "role": "user"},
        ]

        for u in defaults:
            result = await db.execute(select(User).where(User.username == u["username"]))
            if result.scalar_one_or_none():
                continue
            user = User(
                username=u["username"],
                hashed_password=hash_password(u["password"]),
                role=u["role"],
            )
            db.add(user)

        await db.commit()


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session