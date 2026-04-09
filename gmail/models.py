# ABOUTME: Pydantic models for Gmail API requests and responses.
# ABOUTME: Defines schemas for messages, labels, and threads.

from pydantic import BaseModel, Field
from typing import Optional, List


class MessageHeader(BaseModel):
    """Email header (name/value pair)."""
    name: str
    value: str


class MessagePartBody(BaseModel):
    """Message part body."""
    size: int = 0
    data: Optional[str] = None
    attachment_id: Optional[str] = Field(None, alias="attachmentId")


class MessagePart(BaseModel):
    """MIME message part."""
    part_id: Optional[str] = Field(None, alias="partId")
    mime_type: Optional[str] = Field(None, alias="mimeType")
    filename: Optional[str] = None
    headers: List[MessageHeader] = []
    body: Optional[MessagePartBody] = None
    parts: Optional[List["MessagePart"]] = None


class Message(BaseModel):
    """Gmail message."""
    id: str
    thread_id: Optional[str] = Field(None, alias="threadId")
    label_ids: List[str] = Field(default_factory=list, alias="labelIds")
    snippet: Optional[str] = None
    payload: Optional[MessagePart] = None
    size_estimate: Optional[int] = Field(None, alias="sizeEstimate")
    history_id: Optional[str] = Field(None, alias="historyId")
    internal_date: Optional[str] = Field(None, alias="internalDate")
    raw: Optional[str] = None


class MessageList(BaseModel):
    """List of messages response."""
    messages: List[Message] = []
    next_page_token: Optional[str] = Field(None, alias="nextPageToken")
    result_size_estimate: Optional[int] = Field(None, alias="resultSizeEstimate")


class Label(BaseModel):
    """Gmail label."""
    id: str
    name: str
    type: Optional[str] = None
    message_list_visibility: Optional[str] = Field(None, alias="messageListVisibility")
    label_list_visibility: Optional[str] = Field(None, alias="labelListVisibility")
    messages_total: Optional[int] = Field(None, alias="messagesTotal")
    messages_unread: Optional[int] = Field(None, alias="messagesUnread")
    threads_total: Optional[int] = Field(None, alias="threadsTotal")
    threads_unread: Optional[int] = Field(None, alias="threadsUnread")


class LabelList(BaseModel):
    """List of labels response."""
    labels: List[Label] = []


class Thread(BaseModel):
    """Gmail thread."""
    id: str
    snippet: Optional[str] = None
    history_id: Optional[str] = Field(None, alias="historyId")
    messages: List[Message] = []


class ThreadList(BaseModel):
    """List of threads response."""
    threads: List[Thread] = []
    next_page_token: Optional[str] = Field(None, alias="nextPageToken")
    result_size_estimate: Optional[int] = Field(None, alias="resultSizeEstimate")


class SendMessageRequest(BaseModel):
    """Request to send a message."""
    raw: str = Field(..., description="Base64url encoded email message (RFC 2822)")
    thread_id: Optional[str] = Field(None, alias="threadId", description="Thread ID to reply to")


class FriendlySendRequest(BaseModel):
    """Agent-friendly request to send an email with structured fields."""
    to: str = Field(..., description="Recipient email address(es), comma-separated for multiple")
    subject: str = Field(..., description="Email subject line")
    body: str = Field(..., description="Email body (plain text)")
    cc: Optional[str] = Field(None, description="CC recipients, comma-separated")
    bcc: Optional[str] = Field(None, description="BCC recipients, comma-separated")
    thread_id: Optional[str] = Field(None, alias="threadId", description="Thread ID to reply to")
    in_reply_to: Optional[str] = Field(None, alias="inReplyTo", description="Message-ID header of the message being replied to")
    references: Optional[str] = Field(None, description="References header for threading")


class DraftRequest(BaseModel):
    """Request to create a draft."""
    message: SendMessageRequest


# Enable forward references for recursive MessagePart
MessagePart.model_rebuild()
