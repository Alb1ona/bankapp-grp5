"""Kunde-identitet og -profil (tabeller: customer_users, customers)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base_types import GUID, new_uuid, utcnow


class CustomerUser(Base):
    """Lokal loginkonto for kunder. KUN-01: password_hash er Argon2id."""

    __tablename__ = "customer_users"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=new_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    customer: Mapped["Customer"] = relationship(back_populates="user", uselist=False)


class Customer(Base):
    """Kundens stamdata."""

    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(GUID, primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(GUID, ForeignKey("customer_users.id"), unique=True, nullable=False)
    customer_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)

    user: Mapped[CustomerUser] = relationship(back_populates="customer")
    accounts: Mapped[list["Account"]] = relationship(back_populates="customer")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
