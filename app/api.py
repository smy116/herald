"""RPC-style action API endpoints (POST /api/{action})."""

import json
import secrets
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import require_login
from app.models import Channel, APIKey, MessageLog
from app.schemas import (
    ApiResponse,
    CreateChannelRequest,
    UpdateChannelRequest,
    DeleteChannelRequest,
    TestChannelRequest,
    CreateKeyRequest,
    DeleteKeyRequest,
    RetryMsgRequest,
)
from app.services import dispatch_message

router = APIRouter(prefix="/api", dependencies=[Depends(require_login)])


# ── Channel CRUD ─────────────────────────────────────────

@router.post("/create_channel", response_model=ApiResponse)
async def create_channel(req: CreateChannelRequest, db: Session = Depends(get_db)):
    existing = db.query(Channel).filter(Channel.name == req.name).first()
    if existing:
        return ApiResponse(ok=False, msg=f"渠道名 '{req.name}' 已存在")
    ch = Channel(
        name=req.name,
        type=req.type,
        config=json.dumps(req.config, ensure_ascii=False),
        is_default=req.is_default,
    )
    db.add(ch)
    db.commit()
    return ApiResponse(msg="渠道已创建")


@router.post("/update_channel", response_model=ApiResponse)
async def update_channel(req: UpdateChannelRequest, db: Session = Depends(get_db)):
    ch = db.query(Channel).filter(Channel.id == req.id).first()
    if not ch:
        return ApiResponse(ok=False, msg="渠道不存在")
    ch.name = req.name
    ch.type = req.type
    ch.config = json.dumps(req.config, ensure_ascii=False)
    ch.is_default = req.is_default
    ch.enabled = req.enabled
    db.commit()
    return ApiResponse(msg="渠道已更新")


@router.post("/delete_channel", response_model=ApiResponse)
async def delete_channel(req: DeleteChannelRequest, db: Session = Depends(get_db)):
    ch = db.query(Channel).filter(Channel.id == req.id).first()
    if not ch:
        return ApiResponse(ok=False, msg="渠道不存在")
    db.delete(ch)
    db.commit()
    return ApiResponse(msg="渠道已删除")


@router.post("/test_channel", response_model=ApiResponse)
async def test_channel(req: TestChannelRequest, db: Session = Depends(get_db)):
    ch = db.query(Channel).filter(Channel.id == req.id).first()
    if not ch:
        return ApiResponse(ok=False, msg="渠道不存在")
    logs = await dispatch_message(
        db, title="Herald 测试消息", body="这是一条来自 Herald 的测试消息。", channels=[ch], api_key_name="[test]"
    )
    log = logs[0]
    if log.status == "failed":
        return ApiResponse(ok=False, msg=f"发送失败: {log.error_msg}")
    return ApiResponse(msg="测试消息已发送")


# ── API Key CRUD ─────────────────────────────────────────

@router.post("/create_key", response_model=ApiResponse)
async def create_key(req: CreateKeyRequest, db: Session = Depends(get_db)):
    key_value = secrets.token_hex(16)  # 32-char lowercase alphanumeric
    k = APIKey(name=req.name, key=key_value)
    db.add(k)
    db.commit()
    return ApiResponse(msg="密钥已创建", data={"key": key_value})


@router.post("/delete_key", response_model=ApiResponse)
async def delete_key(req: DeleteKeyRequest, db: Session = Depends(get_db)):
    k = db.query(APIKey).filter(APIKey.id == req.id).first()
    if not k:
        return ApiResponse(ok=False, msg="密钥不存在")
    db.delete(k)
    db.commit()
    return ApiResponse(msg="密钥已删除")


# ── Log Operations ───────────────────────────────────────

@router.post("/clear_logs", response_model=ApiResponse)
async def clear_logs(db: Session = Depends(get_db)):
    db.query(MessageLog).delete()
    db.commit()
    return ApiResponse(msg="日志已清空")


@router.post("/retry_msg", response_model=ApiResponse)
async def retry_msg(req: RetryMsgRequest, db: Session = Depends(get_db)):
    log = db.query(MessageLog).filter(MessageLog.id == req.log_id).first()
    if not log:
        return ApiResponse(ok=False, msg="日志不存在")
    ch = db.query(Channel).filter(Channel.name == log.channel_name).first()
    if not ch:
        return ApiResponse(ok=False, msg=f"渠道 '{log.channel_name}' 已被删除")
    new_logs = await dispatch_message(
        db, title=log.title, body=log.body, channels=[ch], api_key_name=log.api_key_name
    )
    new_log = new_logs[0]
    if new_log.status == "failed":
        return ApiResponse(ok=False, msg=f"重试失败: {new_log.error_msg}")
    return ApiResponse(msg="消息已重新发送")
