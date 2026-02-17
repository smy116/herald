"""SQLAlchemy ORM models."""

import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime

from app.database import Base


class Channel(Base):
    __tablename__ = "channels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    type = Column(String(20), nullable=False)  # webhook | telegram | email
    config = Column(Text, nullable=False, default="{}")  # JSON string
    is_default = Column(Boolean, default=False)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    key = Column(String(64), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class MessageLog(Base):
    __tablename__ = "message_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    body = Column(Text, default="")
    status = Column(String(20), default="pending")  # pending | success | failed
    channel_name = Column(String(100), default="")
    error_msg = Column(Text, default="")
    api_key_name = Column(String(100), default="")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
