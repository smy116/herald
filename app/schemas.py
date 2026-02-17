"""Pydantic request/response schemas."""

from typing import Any, Optional
from pydantic import BaseModel


# --- Unified Response ---
class ApiResponse(BaseModel):
    ok: bool = True
    msg: str = ""
    data: Any = None


# --- /send ---
class SendRequest(BaseModel):
    title: str
    body: str = ""
    channel: Optional[str] = None


# --- Channel ---
class CreateChannelRequest(BaseModel):
    name: str
    type: str  # webhook | telegram | email
    config: dict = {}
    is_default: bool = False


class UpdateChannelRequest(BaseModel):
    id: int
    name: str
    type: str
    config: dict = {}
    is_default: bool = False
    enabled: bool = True


class DeleteChannelRequest(BaseModel):
    id: int


class TestChannelRequest(BaseModel):
    id: int


# --- API Key ---
class CreateKeyRequest(BaseModel):
    name: str


class DeleteKeyRequest(BaseModel):
    id: int


# --- Log ---
class RetryMsgRequest(BaseModel):
    log_id: int
