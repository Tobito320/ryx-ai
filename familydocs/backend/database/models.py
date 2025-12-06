"""
SQLAlchemy Database Models for FamilyDocs
"""
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
    CheckConstraint,
    UniqueConstraint,
    ARRAY,
    BigInteger,
    Date,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from database.connection import Base


# ============================================================================
# Boards & Folders
# ============================================================================


class Board(Base):
    __tablename__ = "boards"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False, default="board")
    parent_id = Column(UUID(as_uuid=True), ForeignKey("boards.id", ondelete="CASCADE"))
    workspace_id = Column(String(100), default="default")

    # PC Sync
    is_synced_to_pc = Column(Boolean, default=False)
    pc_path = Column(String(512))
    sync_status = Column(String(50), default="pending")
    sync_error = Column(Text)
    last_synced_at = Column(DateTime(timezone=True))

    # Canvas Position
    canvas_x = Column(Float, default=0)
    canvas_y = Column(Float, default=0)
    canvas_zoom = Column(Float, default=1.0)
    canvas_width = Column(Float, default=300)
    canvas_height = Column(Float, default=200)

    # Metadata
    description = Column(Text)
    ai_description = Column(Text)
    icon = Column(String(50), default="📁")
    color = Column(String(20), default="#8b5cf6")

    # Creation Info
    created_by = Column(String(100), default="user")
    auto_created = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    parent = relationship("Board", remote_side=[id], backref="children")
    documents = relationship("BoardDocument", back_populates="board", cascade="all, delete-orphan")
    links_from = relationship(
        "BoardLink", foreign_keys="BoardLink.board_id_from", back_populates="board_from", cascade="all, delete-orphan"
    )
    links_to = relationship(
        "BoardLink", foreign_keys="BoardLink.board_id_to", back_populates="board_to", cascade="all, delete-orphan"
    )
    chat_sessions = relationship("ChatSession", back_populates="board")
    modules = relationship("Module", back_populates="board", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        CheckConstraint("type IN ('board', 'folder')", name="valid_type"),
        CheckConstraint("sync_status IN ('synced', 'pending', 'error')", name="valid_sync_status"),
    )


# ============================================================================
# Documents
# ============================================================================


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # File Info
    filename = Column(String(512), nullable=False)
    file_path = Column(String(1024), nullable=False)
    file_type = Column(String(100))
    file_size = Column(BigInteger)
    mime_type = Column(String(100))

    # Content
    extracted_text = Column(Text)
    summary = Column(Text)

    # Classification
    category = Column(String(100))
    tags = Column(ARRAY(Text))

    # Source
    source = Column(String(100), default="upload")
    source_metadata = Column(JSONB)

    # AI Analysis
    ai_confidence = Column(Float, default=0.0)
    ai_metadata = Column(JSONB)

    # Timestamps
    document_date = Column(Date)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    boards = relationship("BoardDocument", back_populates="document", cascade="all, delete-orphan")
    embeddings = relationship("Embedding", back_populates="document", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        CheckConstraint("ai_confidence >= 0.0 AND ai_confidence <= 1.0", name="valid_confidence"),
    )


# ============================================================================
# Board-Document Relationships
# ============================================================================


class BoardDocument(Base):
    __tablename__ = "board_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    board_id = Column(UUID(as_uuid=True), ForeignKey("boards.id", ondelete="CASCADE"), nullable=False)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)

    # Metadata
    added_by = Column(String(100), default="user")
    relevance_score = Column(Float, default=1.0)

    # Timestamps
    added_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    board = relationship("Board", back_populates="documents")
    document = relationship("Document", back_populates="boards")

    # Constraints
    __table_args__ = (
        UniqueConstraint("board_id", "document_id", name="unique_board_document"),
        CheckConstraint("relevance_score >= 0.0 AND relevance_score <= 1.0", name="valid_relevance"),
    )


# ============================================================================
# Board Links
# ============================================================================


class BoardLink(Base):
    __tablename__ = "board_links"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    board_id_from = Column(UUID(as_uuid=True), ForeignKey("boards.id", ondelete="CASCADE"), nullable=False)
    board_id_to = Column(UUID(as_uuid=True), ForeignKey("boards.id", ondelete="CASCADE"), nullable=False)

    # Link Type
    link_type = Column(String(50), nullable=False, default="related")
    reason = Column(Text)

    # Metadata
    created_by = Column(String(100), default="user")
    confidence = Column(Float, default=1.0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    board_from = relationship("Board", foreign_keys=[board_id_from], back_populates="links_from")
    board_to = relationship("Board", foreign_keys=[board_id_to], back_populates="links_to")

    # Constraints
    __table_args__ = (
        CheckConstraint("board_id_from != board_id_to", name="no_self_link"),
        UniqueConstraint("board_id_from", "board_id_to", "link_type", name="unique_board_link"),
        CheckConstraint("link_type IN ('related', 'depends_on', 'affects', 'references')", name="valid_link_type"),
    )


# ============================================================================
# Chat Sessions
# ============================================================================


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Session Info
    session_name = Column(String(255))
    board_id = Column(UUID(as_uuid=True), ForeignKey("boards.id", ondelete="SET NULL"))
    user_id = Column(String(100), default="default_user")

    # Session Type
    is_persistent = Column(Boolean, default=False)

    # Context Management
    active_documents = Column(ARRAY(UUID(as_uuid=True)))
    context_window_size = Column(Integer, default=8192)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_activity = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))

    # Status
    is_active = Column(Boolean, default=True)

    # Relationships
    board = relationship("Board", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")


# ============================================================================
# Chat Messages
# ============================================================================


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)

    # Message Content
    role = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)

    # AI Agent Info
    agent_used = Column(String(100))
    model_used = Column(String(100))

    # Tool/Function Calls
    function_calls = Column(JSONB)
    tool_results = Column(JSONB)

    # Metadata
    tokens_used = Column(Integer)
    response_time_ms = Column(Integer)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    session = relationship("ChatSession", back_populates="messages")

    # Constraints
    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant', 'system')", name="valid_role"),
    )


# ============================================================================
# Smart Modules
# ============================================================================


class Module(Base):
    __tablename__ = "modules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    board_id = Column(UUID(as_uuid=True), ForeignKey("boards.id", ondelete="CASCADE"))

    # Module Info
    module_type = Column(String(100), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # Configuration
    config = Column(JSONB, nullable=False, default={})

    # Data
    data = Column(JSONB, default={})

    # Refresh Settings
    refresh_interval = Column(Integer, default=86400)
    last_refreshed = Column(DateTime(timezone=True))
    next_refresh = Column(DateTime(timezone=True))

    # Status
    is_active = Column(Boolean, default=True)
    last_error = Column(Text)
    error_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    board = relationship("Board", back_populates="modules")


# ============================================================================
# Audit Log
# ============================================================================


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Action Info
    action = Column(String(100), nullable=False)
    entity_type = Column(String(100))
    entity_id = Column(UUID(as_uuid=True))

    # User Decision
    user_decision = Column(String(100))
    ai_confidence = Column(Float)

    # Context
    context = Column(JSONB)

    # Timestamp
    timestamp = Column(DateTime(timezone=True), server_default=func.now())


# ============================================================================
# Vector Embeddings
# ============================================================================


class Embedding(Base):
    __tablename__ = "embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)

    # Chunk Info
    chunk_index = Column(Integer, nullable=False)
    chunk_text = Column(Text, nullable=False)

    # Vector Info
    vector_id = Column(String(255))
    embedding_model = Column(String(100), default="qwen2.5-32b")

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    document = relationship("Document", back_populates="embeddings")

    # Constraints
    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="unique_doc_chunk"),
    )
