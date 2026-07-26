import uuid

from fastapi import APIRouter, Depends, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.enums import MessageType
from app.models.message import Message
from app.models.user import User
from app.schemas.messaging import ConversationRead, CounterpartRead, MessageRead, SendTextMessageRequest, StartConversationRequest
from app.services import messaging as messaging_service
from app.services.storage import get_storage_backend

router = APIRouter(prefix="/conversations", tags=["messaging"])


def _to_message_read(message: Message, current_user_id: uuid.UUID) -> MessageRead:
    storage = get_storage_backend()
    return MessageRead(
        id=message.id,
        conversation_id=message.conversation_id,
        sender_user_id=message.sender_user_id,
        is_mine=message.sender_user_id == current_user_id,
        message_type=message.message_type,
        text_body=message.text_body,
        attachment_url=storage.url_for(message.attachment_key) if message.attachment_key else None,
        attachment_original_filename=message.attachment_original_filename,
        attachment_mime_type=message.attachment_mime_type,
        attachment_size_bytes=message.attachment_size_bytes,
        created_at=message.created_at,
        read_at=message.read_at,
    )


@router.get("", response_model=list[ConversationRead])
async def list_conversations(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[ConversationRead]:
    summaries = await messaging_service.list_conversations_for_user(db, user)
    return [
        ConversationRead(
            id=s.conversation.id,
            counterpart=CounterpartRead(
                user_id=s.counterpart.user_id, name=s.counterpart.name, picture_url=s.counterpart.picture_url
            ),
            last_message=_to_message_read(s.last_message, user.id) if s.last_message else None,
            unread_count=s.unread_count,
            last_message_at=s.conversation.last_message_at,
        )
        for s in summaries
    ]


@router.post("", response_model=ConversationRead)
async def start_conversation(
    payload: StartConversationRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> ConversationRead:
    conversation = await messaging_service.get_or_create_conversation(db, user=user, counterpart_id=payload.counterpart_id)
    counterpart = await messaging_service.get_counterpart(db, conversation, user)

    last_messages = await messaging_service.list_messages(db, conversation_id=conversation.id, limit=1)
    return ConversationRead(
        id=conversation.id,
        counterpart=CounterpartRead(user_id=counterpart.user_id, name=counterpart.name, picture_url=counterpart.picture_url),
        last_message=_to_message_read(last_messages[-1], user.id) if last_messages else None,
        unread_count=0,
        last_message_at=conversation.last_message_at,
    )


@router.get("/{conversation_id}/messages", response_model=list[MessageRead])
async def get_messages(
    conversation_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[MessageRead]:
    conversation = await messaging_service.get_conversation_for_user(db, conversation_id=conversation_id, user=user)
    messages = await messaging_service.list_messages(db, conversation_id=conversation.id)
    return [_to_message_read(m, user.id) for m in messages]


@router.post("/{conversation_id}/messages", response_model=MessageRead)
async def send_message(
    conversation_id: uuid.UUID,
    payload: SendTextMessageRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageRead:
    conversation = await messaging_service.get_conversation_for_user(db, conversation_id=conversation_id, user=user)
    message = await messaging_service.send_text_message(db, conversation=conversation, sender_user_id=user.id, text=payload.text)
    return _to_message_read(message, user.id)


@router.post("/{conversation_id}/messages/attachment", response_model=MessageRead)
async def send_attachment(
    conversation_id: uuid.UUID,
    file: UploadFile,
    message_type: MessageType = Form(...),
    caption: str | None = Form(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageRead:
    conversation = await messaging_service.get_conversation_for_user(db, conversation_id=conversation_id, user=user)
    message = await messaging_service.send_attachment_message(
        db, conversation=conversation, sender_user_id=user.id, message_type=message_type, file=file, caption=caption
    )
    return _to_message_read(message, user.id)


@router.post("/{conversation_id}/read", status_code=204)
async def mark_read(
    conversation_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> None:
    conversation = await messaging_service.get_conversation_for_user(db, conversation_id=conversation_id, user=user)
    await messaging_service.mark_conversation_read(db, conversation=conversation, reader_user_id=user.id)
