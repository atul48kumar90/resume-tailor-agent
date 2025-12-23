# db/models.py
"""
SQLAlchemy models for PostgreSQL database.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text, JSON,
    ForeignKey, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

Base = declarative_base()


class User(Base):
    """User model for authentication and data isolation."""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    resumes = relationship("Resume", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"


class Resume(Base):
    """Resume model for storing resume metadata and content."""
    __tablename__ = "resumes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    tags = Column(JSON, default=list)  # List of tags
    resume_data = Column(JSON, nullable=True)  # Structured resume data
    resume_text = Column(Text, nullable=True)  # Plain text version
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Statistics
    version_count = Column(Integer, default=1, nullable=False)
    application_count = Column(Integer, default=0, nullable=False)
    total_applications = Column(Integer, default=0, nullable=False)
    interviews = Column(Integer, default=0, nullable=False)
    rejections = Column(Integer, default=0, nullable=False)
    average_ats_score = Column(Float, default=0.0, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="resumes")
    versions = relationship("ResumeVersion", back_populates="resume", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="resume", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_resume_user_created", "user_id", "created_at"),
        Index("idx_resume_title", "title"),
    )
    
    def __repr__(self):
        return f"<Resume(id={self.id}, title={self.title}, user_id={self.user_id})>"


class ResumeVersion(Base):
    """Resume version model for version control."""
    __tablename__ = "resume_versions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resume_id = Column(UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_version_id = Column(UUID(as_uuid=True), ForeignKey("resume_versions.id", ondelete="SET NULL"), nullable=True)
    version_number = Column(Integer, nullable=False)
    resume_data = Column(JSON, nullable=False)
    change_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    resume = relationship("Resume", back_populates="versions")
    parent = relationship("ResumeVersion", remote_side=[id], backref="children")
    
    # Indexes
    __table_args__ = (
        Index("idx_version_resume_created", "resume_id", "created_at"),
    )
    
    def __repr__(self):
        return f"<ResumeVersion(id={self.id}, resume_id={self.resume_id}, version={self.version_number})>"


class JobDescription(Base):
    """Job description model for storing analyzed JDs."""
    __tablename__ = "job_descriptions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    company = Column(String(255), nullable=True)
    jd_text = Column(Text, nullable=False)
    
    # Analyzed data (cached from LLM)
    role = Column(String(100), nullable=True)
    seniority = Column(String(50), nullable=True)
    required_skills = Column(JSON, default=list)
    optional_skills = Column(JSON, default=list)
    tools = Column(JSON, default=list)
    responsibilities = Column(JSON, default=list)
    ats_keywords = Column(JSON, default=list)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    applications = relationship("Application", back_populates="job_description")
    
    # Indexes
    __table_args__ = (
        Index("idx_jd_user_created", "user_id", "created_at"),
        Index("idx_jd_title", "title"),
    )
    
    def __repr__(self):
        return f"<JobDescription(id={self.id}, title={self.title})>"


class Application(Base):
    """Application model for tracking resume applications to jobs."""
    __tablename__ = "applications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resume_id = Column(UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True)
    job_description_id = Column(UUID(as_uuid=True), ForeignKey("job_descriptions.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Application metadata
    job_title = Column(String(255), nullable=False)
    company = Column(String(255), nullable=True)
    application_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(String(50), default="applied", nullable=False)  # applied, interview, offer, rejected
    
    # ATS scoring results
    ats_score = Column(Float, nullable=True)
    fit_score = Column(Float, nullable=True)
    skill_gap_severity = Column(String(50), nullable=True)
    required_coverage = Column(Float, nullable=True)
    missing_required_count = Column(Integer, nullable=True)
    
    # Detailed results (stored as JSON)
    ats_details = Column(JSON, nullable=True)
    skill_gap_details = Column(JSON, nullable=True)
    recommendations = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    resume = relationship("Resume", back_populates="applications")
    job_description = relationship("JobDescription", back_populates="applications")
    user = relationship("User", foreign_keys=[user_id])
    
    # Indexes
    __table_args__ = (
        Index("idx_application_user_date", "user_id", "application_date"),
        Index("idx_application_status", "status"),
        Index("idx_application_resume", "resume_id", "application_date"),
    )
    
    def __repr__(self):
        return f"<Application(id={self.id}, resume_id={self.resume_id}, status={self.status})>"


class Job(Base):
    """Job model for tracking background job processing."""
    __tablename__ = "jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rq_job_id = Column(String(255), unique=True, nullable=True, index=True)  # RQ job ID
    status = Column(String(50), default="pending", nullable=False, index=True)  # pending, queued, started, completed, failed
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Indexes
    __table_args__ = (
        Index("idx_job_status_created", "status", "created_at"),
    )
    
    def __repr__(self):
        return f"<Job(id={self.id}, status={self.status})>"


class APIUsage(Base):
    """API usage tracking model for analytics."""
    __tablename__ = "api_usage"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    endpoint = Column(String(255), nullable=False, index=True)  # e.g., "/tailor", "/ats/compare"
    method = Column(String(10), nullable=False, index=True)  # GET, POST, PUT, DELETE
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    client_ip = Column(String(45), nullable=True)  # IPv4 or IPv6
    status_code = Column(Integer, nullable=False, index=True)
    response_time_ms = Column(Integer, nullable=True)  # Response time in milliseconds
    request_size_bytes = Column(Integer, nullable=True)  # Request body size
    response_size_bytes = Column(Integer, nullable=True)  # Response body size
    user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Additional metadata
    error_message = Column(Text, nullable=True)  # Error message if status >= 400
    
    # Indexes for common queries
    __table_args__ = (
        Index("idx_api_usage_endpoint_created", "endpoint", "created_at"),
        Index("idx_api_usage_user_created", "user_id", "created_at"),
        Index("idx_api_usage_status_created", "status_code", "created_at"),
        Index("idx_api_usage_created", "created_at"),
    )
    
    def __repr__(self):
        return f"<APIUsage(endpoint={self.endpoint}, method={self.method}, status={self.status_code})>"

