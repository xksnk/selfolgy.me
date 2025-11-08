from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..core.database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String(50), unique=True, index=True, nullable=False)
    username = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    
    # User tier and state
    tier = Column(String(20), default="free")  # free, premium, professional
    onboarding_completed = Column(Boolean, default=False)
    current_state = Column(String(50), nullable=True)
    
    # Privacy settings
    privacy_level = Column(String(20), default="balanced")  # minimal, balanced, full
    gdpr_consent = Column(Boolean, default=False)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_active = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    questionnaires = relationship("Questionnaire", back_populates="user")
    chat_history = relationship("ChatMessage", back_populates="user")
    personality_vectors = relationship("PersonalityVector", back_populates="user")


class Questionnaire(Base):
    __tablename__ = "questionnaires"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), index=True, nullable=False)
    questionnaire_type = Column(String(50), nullable=False)  # personality, values, goals
    responses = Column(JSON, nullable=False)
    completed_at = Column(DateTime(timezone=True), server_default=func.now())
    vector_id = Column(String(100), nullable=True)  # Qdrant vector ID
    
    # Relationships
    user = relationship("User", back_populates="questionnaires")


class ChatMessage(Base):
    __tablename__ = "chat_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), index=True, nullable=False)
    message_type = Column(String(20), default="user")  # user, assistant, system
    content = Column(Text, nullable=False)
    ai_model_used = Column(String(50), nullable=True)
    cost_estimate = Column(String(20), nullable=True)
    
    # AI analysis and insights
    insights = Column(JSON, nullable=True)
    personality_updates = Column(JSON, nullable=True)
    vector_updated = Column(Boolean, default=False)
    
    # Metadata
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="chat_history")


class PersonalityVector(Base):
    __tablename__ = "personality_vectors"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), index=True, nullable=False)
    vector_version = Column(Integer, default=1)
    
    # Personality traits
    traits = Column(JSON, nullable=False)  # Big Five + custom traits
    confidence_score = Column(String(10), nullable=True)
    
    # Vector metadata
    qdrant_point_id = Column(String(100), nullable=True)
    source_data = Column(String(100), nullable=True)  # questionnaire, chat, analysis
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="personality_vectors")