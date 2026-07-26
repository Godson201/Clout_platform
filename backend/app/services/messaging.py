import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.brand import Brand
from app.models.conversation import Conversation
from app.models.enums import MessageType, UserType
from app.models.influencer import Influencer
from app.models.message import Message
from app.models.user import User
from app.services.relationships import brand_and_influencer_are_connected
from app.services.storage import allowed_extensions, get_storage_backend, read_with_limit

settings = get_settings()

_DOCUMENT_EXTENSIONS = {".pdf", ".doc", ".docx", ".txt"}

_ATTACHMENT_EXTENSIONS: dict[MessageType, set[str]] = {
    MessageType.AUDIO: allowed_extensions("audio"),
    MessageType.VOICE_NOTE: allowed_extensions("audio"),
    MessageType.VIDEO: allowed_extensions("video"),
    MessageType.DOCUMENT: _DOCUMENT_EXTENSIONS,
}

_ATTACHMENT_MAX_MB: dict[MessageType, int] = {
    MessageType.AUDIO: settings.MAX_AUDIO_UPLOAD_MB,
    MessageType.VOICE_NOTE: settings.MAX_AUDIO_UPLOAD_MB,
    MessageType.VIDEO: settings.MAX_VIDEO_UPLOAD_MB,
    MessageType.DOCUMENT: settings.MAX_DOCUMENT_UPLOAD_MB,
}

_EXPECTED_CONTENT_TYPE_PREFIX: dict[MessageType, str] = {
    MessageType.AUDIO: "audio/",
    MessageType.VOICE_NOTE: "audio/",
    MessageType.VIDEO: "video/",
}


@dataclass
class Counterpart:
    user_id: uuid.UUID
    name: str
    picture_url: str | None


@dataclass
class ConversationSummary:
    conversation: Conversation
    counterpart: Counterpart
    last_message: Message | None
    unread_count: int


async def _get_user_participant_id(db: AsyncSession, user: User) -> tuple[UserType, uuid.UUID]:
    if user.user_type == UserType.BRAND:
        brand = await db.get(Brand, user.id)
        if brand is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand profile not found")
        return UserType.BRAND, brand.id
    if user.user_type == UserType.INFLUENCER:
        influencer = await db.get(Influencer, user.id)
        if influencer is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Influencer profile not found")
        return UserType.INFLUENCER, influencer.id
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only brands and influencers can message")


async def get_or_create_conversation(db: AsyncSession, *, user: User, counterpart_id: uuid.UUID) -> Conversation:
    user_kind, _ = await _get_user_participant_id(db, user)

    if user_kind == UserType.BRAND:
        brand_id, influencer_id = user.id, counterpart_id
    else:
        brand_id, influencer_id = counterpart_id, user.id

    if not await brand_and_influencer_are_connected(db, brand_id=brand_id, influencer_id=influencer_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only message someone you have an active campaign relationship with",
        )

    result = await db.execute(
        select(Conversation).where(Conversation.brand_id == brand_id, Conversation.influencer_id == influencer_id)
    )
    conversation = result.scalar_one_or_none()
    if conversation is not None:
        return conversation

    now = datetime.now(timezone.utc)
    conversation = Conversation(brand_id=brand_id, influencer_id=influencer_id, created_at=now, last_message_at=now)
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return conversation


async def get_conversation_for_user(db: AsyncSession, *, conversation_id: uuid.UUID, user: User) -> Conversation:
    conversation = await db.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    if conversation.brand_id != user.id and conversation.influencer_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a participant in this conversation")
    return conversation


async def get_counterpart(db: AsyncSession, conversation: Conversation, user: User) -> Counterpart:
    if conversation.brand_id == user.id:
        influencer = await db.get(Influencer, conversation.influencer_id)
        return Counterpart(
            user_id=conversation.influencer_id,
            name=influencer.display_name if influencer else "Unknown",
            picture_url=influencer.profile_picture_url if influencer else None,
        )
    brand = await db.get(Brand, conversation.brand_id)
    return Counterpart(
        user_id=conversation.brand_id,
        name=brand.business_name if brand else "Unknown",
        picture_url=brand.logo_url if brand else None,
    )


async def list_conversations_for_user(db: AsyncSession, user: User) -> list[ConversationSummary]:
    user_kind, _ = await _get_user_participant_id(db, user)
    filter_col = Conversation.brand_id if user_kind == UserType.BRAND else Conversation.influencer_id

    result = await db.execute(
        select(Conversation).where(filter_col == user.id).order_by(Conversation.last_message_at.desc())
    )
    conversations = result.scalars().all()

    # One extra pair of queries per conversation for the preview + unread count —
    # accepted at today's scale (a handful of conversations per user), same
    # tradeoff the marketplace's per-slot historical-boost lookup already makes.
    summaries: list[ConversationSummary] = []
    for conversation in conversations:
        counterpart = await get_counterpart(db, conversation, user)

        last_message_result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        last_message = last_message_result.scalar_one_or_none()

        unread_result = await db.execute(
            select(func.count())
            .select_from(Message)
            .where(
                Message.conversation_id == conversation.id,
                Message.sender_user_id != user.id,
                Message.read_at.is_(None),
            )
        )
        unread_count = unread_result.scalar_one()

        summaries.append(
            ConversationSummary(
                conversation=conversation, counterpart=counterpart, last_message=last_message, unread_count=unread_count
            )
        )

    return summaries


async def list_messages(db: AsyncSession, *, conversation_id: uuid.UUID, limit: int = 100) -> list[Message]:
    result = await db.execute(
        select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at.asc()).limit(limit)
    )
    return list(result.scalars().all())


async def _touch_conversation(db: AsyncSession, conversation: Conversation, at: datetime) -> None:
    conversation.last_message_at = at


async def send_text_message(db: AsyncSession, *, conversation: Conversation, sender_user_id: uuid.UUID, text: str) -> Message:
    if not text.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message text cannot be empty")

    now = datetime.now(timezone.utc)
    message = Message(
        conversation_id=conversation.id,
        sender_user_id=sender_user_id,
        message_type=MessageType.TEXT,
        text_body=text.strip(),
        created_at=now,
    )
    db.add(message)
    await _touch_conversation(db, conversation, now)
    await db.commit()
    await db.refresh(message)
    return message


def _validate_attachment(message_type: MessageType, file: UploadFile) -> str:
    allowed = _ATTACHMENT_EXTENSIONS.get(message_type)
    if allowed is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"'{message_type.value}' has no file attachment")

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension '{ext or '(none)'}' for {message_type.value}. Allowed: {', '.join(sorted(allowed))}",
        )

    expected_prefix = _EXPECTED_CONTENT_TYPE_PREFIX.get(message_type)
    if expected_prefix and file.content_type and not file.content_type.startswith(expected_prefix):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Content-Type '{file.content_type}' doesn't match expected {message_type.value} upload",
        )
    return ext


async def send_attachment_message(
    db: AsyncSession,
    *,
    conversation: Conversation,
    sender_user_id: uuid.UUID,
    message_type: MessageType,
    file: UploadFile,
    caption: str | None = None,
) -> Message:
    ext = _validate_attachment(message_type, file)

    max_bytes = _ATTACHMENT_MAX_MB[message_type] * 1024 * 1024
    content = await read_with_limit(file, max_bytes)
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")

    storage = get_storage_backend()
    storage_key = f"chat-attachments/{conversation.id}/{uuid.uuid4()}{ext}"
    storage.save(storage_key, content)

    now = datetime.now(timezone.utc)
    message = Message(
        conversation_id=conversation.id,
        sender_user_id=sender_user_id,
        message_type=message_type,
        text_body=caption.strip() if caption and caption.strip() else None,
        attachment_key=storage_key,
        attachment_original_filename=file.filename or "upload",
        attachment_mime_type=file.content_type or "application/octet-stream",
        attachment_size_bytes=len(content),
        created_at=now,
    )
    db.add(message)
    await _touch_conversation(db, conversation, now)
    await db.commit()
    await db.refresh(message)
    return message


async def mark_conversation_read(db: AsyncSession, *, conversation: Conversation, reader_user_id: uuid.UUID) -> None:
    await db.execute(
        update(Message)
        .where(
            Message.conversation_id == conversation.id,
            Message.sender_user_id != reader_user_id,
            Message.read_at.is_(None),
        )
        .values(read_at=datetime.now(timezone.utc))
    )
    await db.commit()
