"""SQLAlchemy database models."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, String, Boolean, DateTime, Text, JSON, Integer, Float, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from .connection import Base


class UserModel(Base):
    """User database model."""
    
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    telegram_id = Column(String(50), unique=True, index=True, nullable=False)
    username = Column(String(100), nullable=True, index=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    
    # User tier and state
    tier = Column(String(20), default="free", nullable=False)
    privacy_level = Column(String(20), default="balanced", nullable=False)
    gdpr_consent = Column(Boolean, default=False, nullable=False)
    onboarding_completed = Column(Boolean, default=False, nullable=False)
    current_state = Column(String(50), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_active = Column(DateTime(timezone=True), nullable=True)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_users_tier', 'tier'),
        Index('idx_users_last_active', 'last_active'),
        Index('idx_users_onboarding', 'onboarding_completed'),
    )


class PersonalityProfileModel(Base):
    """Personality profile database model."""
    
    __tablename__ = "personality_profiles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    user_id = Column(String(50), index=True, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    
    # Personality data
    traits = Column(JSON, nullable=False, default=dict)
    overall_confidence = Column(Float, default=0.0, nullable=False)
    
    # Vector storage reference
    qdrant_point_id = Column(String(100), nullable=True, index=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_personality_user_version', 'user_id', 'version'),
        Index('idx_personality_confidence', 'overall_confidence'),
    )


class ChatMessageModel(Base):
    """Chat message database model."""
    
    __tablename__ = "chat_messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    user_id = Column(String(50), index=True, nullable=False)
    message_type = Column(String(20), default="user", nullable=False)
    content = Column(Text, nullable=False)
    
    # AI processing info
    ai_model_used = Column(String(50), nullable=True)
    cost_estimate = Column(Float, nullable=True)
    
    # Analysis results
    context = Column(JSON, nullable=True)
    insights = Column(JSON, nullable=True)
    personality_updates = Column(JSON, nullable=True)
    vector_updated = Column(Boolean, default=False, nullable=False)
    
    # Timestamp
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_chat_user_timestamp', 'user_id', 'timestamp'),
        Index('idx_chat_message_type', 'message_type'),
        Index('idx_chat_ai_model', 'ai_model_used'),
    )


class AssessmentResponseModel(Base):
    """Assessment response database model."""
    
    __tablename__ = "assessment_responses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    user_id = Column(String(50), index=True, nullable=False)
    assessment_type = Column(String(50), nullable=False)
    
    # Assessment data
    answers = Column(JSON, nullable=False, default=dict)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Processing results
    vector_id = Column(String(100), nullable=True, index=True)
    insights_generated = Column(Boolean, default=False, nullable=False)
    metadata = Column(JSON, nullable=True, default=dict)
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_assessment_user_type', 'user_id', 'assessment_type'),
        Index('idx_assessment_completed', 'completed_at'),
        Index('idx_assessment_insights', 'insights_generated'),
    )