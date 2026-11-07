from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(30), default="STUDENT", index=True)
    wallet_balance_paise: Mapped[int] = mapped_column(Integer, default=100000)
    tier: Mapped[str] = mapped_column(String(20), default="BASIC")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    transactions = relationship("Transaction", back_populates="user")

class Transaction(Base):
    __tablename__ = "transactions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    merchant_name: Mapped[str] = mapped_column(String(100))
    category: Mapped[str] = mapped_column(String(30), index=True)
    amount_paise: Mapped[int] = mapped_column(Integer)
    raw_cashback_paise: Mapped[int] = mapped_column(Integer)
    cashback_paise: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="SUCCESS")
    idempotency_key: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    user = relationship("User", back_populates="transactions")
