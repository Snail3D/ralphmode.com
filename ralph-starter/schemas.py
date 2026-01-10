#!/usr/bin/env python3
"""
SEC-012: API Input Validation - Pydantic Schemas

Strict input validation on all API endpoints using Pydantic.
Enforces type checking, length limits, bounds, and allowed values.
"""

from pydantic import BaseModel, Field, validator, constr, conint
from typing import Optional, List, Literal
from enum import Enum


# ====================
# Enums for Restricted Values
# ====================

class FeedbackType(str, Enum):
    """Valid feedback types for RLHF system"""
    BUG = "bug"
    FEATURE = "feature"
    IMPROVEMENT = "improvement"
    COMPLAINT = "complaint"


class UserTier(str, Enum):
    """User tier system for access control"""
    MR_WORMS = "mr_worms"
    POWER_USER = "power_user"
    VIEWER = "viewer"


class TaskStatus(str, Enum):
    """Status states for tasks in PRD"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class BuildStatus(str, Enum):
    """Build orchestrator status states"""
    QUEUED = "queued"
    BUILDING = "building"
    TESTING = "testing"
    DEPLOYING = "deploying"
    SUCCESS = "success"
    FAILED = "failed"


# ====================
# User Input Schemas
# ====================

class UserMessageInput(BaseModel):
    """Validation for user text/voice message inputs"""
    user_id: conint(ge=1)  # Positive integer, Telegram IDs are positive
    message: constr(min_length=1, max_length=10000)  # 1-10k chars
    message_type: Literal["text", "voice", "file"]

    class Config:
        str_strip_whitespace = True


class VoiceMessageInput(BaseModel):
    """Validation for voice message processing"""
    user_id: conint(ge=1)
    audio_file_id: constr(min_length=10, max_length=200)  # Telegram file ID format
    duration: conint(ge=1, le=300)  # 1-300 seconds (5 minutes max)
    mime_type: Literal["audio/ogg", "audio/mpeg", "audio/wav"]


class FileUploadInput(BaseModel):
    """Validation for file uploads (zip files with code)"""
    user_id: conint(ge=1)
    file_id: constr(min_length=10, max_length=200)
    file_name: constr(min_length=1, max_length=255)
    file_size: conint(ge=1, le=52428800)  # 1 byte to 50MB
    mime_type: Literal["application/zip", "application/x-zip-compressed"]

    @validator('file_name')
    def validate_filename(cls, v):
        """Ensure filename ends with .zip and has no path traversal"""
        if '..' in v or '/' in v or '\\' in v:
            raise ValueError('Filename cannot contain path traversal characters')
        if not v.lower().endswith('.zip'):
            raise ValueError('File must be a .zip archive')
        return v


# ====================
# Feedback System Schemas
# ====================

class FeedbackSubmission(BaseModel):
    """Validation for RLHF feedback submissions"""
    user_id: conint(ge=1)
    feedback_type: FeedbackType
    title: constr(min_length=3, max_length=200)
    description: constr(min_length=10, max_length=5000)
    priority: Optional[conint(ge=1, le=10)] = 5  # 1 (low) to 10 (high)

    class Config:
        str_strip_whitespace = True


class FeedbackStatusQuery(BaseModel):
    """Validation for /mystatus feedback queries"""
    user_id: conint(ge=1)
    limit: Optional[conint(ge=1, le=50)] = 10  # Return max 50 items


# ====================
# Admin Command Schemas
# ====================

class AdminCommand(BaseModel):
    """Validation for admin commands"""
    admin_id: conint(ge=1)
    command: constr(min_length=1, max_length=100)
    params: Optional[constr(max_length=1000)] = None

    @validator('admin_id')
    def validate_admin(cls, v):
        """Ensure admin_id matches configured admin"""
        import os
        admin_id = os.environ.get("TELEGRAM_ADMIN_ID")
        if admin_id and str(v) != admin_id:
            raise ValueError('Unauthorized admin access')
        return v


class UserManagement(BaseModel):
    """Validation for user management operations"""
    admin_id: conint(ge=1)
    target_user_id: conint(ge=1)
    action: Literal["ban", "unban", "set_tier", "reset_rate_limit"]
    tier: Optional[UserTier] = None

    @validator('tier', always=True)
    def validate_tier_for_action(cls, v, values):
        """Ensure tier is provided when action is set_tier"""
        if values.get('action') == 'set_tier' and v is None:
            raise ValueError('Tier must be provided when action is set_tier')
        return v


# ====================
# Build System Schemas
# ====================

class BuildRequest(BaseModel):
    """Validation for build orchestrator requests"""
    feedback_id: conint(ge=1)
    branch_name: constr(min_length=1, max_length=100, pattern=r'^[a-zA-Z0-9_\-/]+$')
    triggered_by: conint(ge=1)  # User ID who triggered build

    @validator('branch_name')
    def validate_branch_name(cls, v):
        """Ensure safe git branch name"""
        dangerous = ['..', '~', '^', ':', '?', '*', '[', '\\', ' ']
        if any(char in v for char in dangerous):
            raise ValueError('Branch name contains invalid characters')
        return v


class DeploymentRequest(BaseModel):
    """Validation for deployment requests"""
    build_id: conint(ge=1)
    environment: Literal["staging", "canary", "production"]
    rollback: bool = False
    percentage: Optional[conint(ge=1, le=100)] = None  # For canary deployments

    @validator('percentage', always=True)
    def validate_percentage_for_canary(cls, v, values):
        """Ensure percentage is provided for canary deployments"""
        if values.get('environment') == 'canary' and v is None:
            raise ValueError('Percentage must be provided for canary deployments')
        return v


# ====================
# API Key & Auth Schemas
# ====================

class APIKeyGeneration(BaseModel):
    """Validation for API key generation"""
    service_name: constr(min_length=3, max_length=100, pattern=r'^[a-zA-Z0-9_\-]+$')
    scopes: List[str] = Field(default_factory=list, max_items=20)
    expires_in_days: Optional[conint(ge=1, le=365)] = 90  # Max 1 year

    @validator('scopes')
    def validate_scopes(cls, v):
        """Ensure scopes are valid"""
        valid_scopes = {
            'read:feedback', 'write:feedback',
            'read:builds', 'trigger:builds',
            'read:deployments', 'trigger:deployments',
            'admin:users', 'admin:system'
        }
        for scope in v:
            if scope not in valid_scopes:
                raise ValueError(f'Invalid scope: {scope}')
        return v


class JWTTokenRequest(BaseModel):
    """Validation for JWT token requests"""
    user_id: conint(ge=1)
    username: constr(min_length=3, max_length=100)
    tier: UserTier


# ====================
# Webhook & Integration Schemas
# ====================

class WebhookPayload(BaseModel):
    """Validation for incoming webhook payloads"""
    event_type: constr(min_length=1, max_length=100)
    payload: dict
    signature: constr(min_length=32, max_length=256)  # HMAC signature
    timestamp: conint(ge=0)  # Unix timestamp

    @validator('timestamp')
    def validate_timestamp_not_too_old(cls, v):
        """Ensure webhook is not replayed (max 5 min old)"""
        from datetime import datetime
        now = int(datetime.utcnow().timestamp())
        if now - v > 300:  # 5 minutes
            raise ValueError('Webhook timestamp too old (possible replay attack)')
        return v


# ====================
# Character & Scene Schemas
# ====================

class CharacterMessage(BaseModel):
    """Validation for character dialogue generation"""
    character_name: Literal["Ralph", "Stool", "Gomer", "Mona", "Gus", "Frinky", "Otto"]
    context: constr(max_length=5000)
    mood: Optional[Literal["happy", "stressed", "neutral", "annoyed"]] = "neutral"


class SceneGeneration(BaseModel):
    """Validation for scene/atmosphere generation"""
    time_of_day: Literal["morning", "afternoon", "evening", "night"]
    weather: Optional[Literal["sunny", "cloudy", "rainy", "stormy"]] = None
    project_type: Optional[constr(max_length=100)] = None
    mood: Optional[Literal["upbeat", "tense", "relaxed", "deadline"]] = "relaxed"


# ====================
# Validation Helper Functions
# ====================

def validate_model(model: BaseModel, data: dict) -> tuple[bool, Optional[str]]:
    """
    Validate data against a Pydantic model.

    Returns:
        (is_valid, error_message)
    """
    try:
        model(**data)
        return True, None
    except Exception as e:
        return False, str(e)


def validate_and_parse(model: BaseModel, data: dict):
    """
    Validate and parse data into a Pydantic model.

    Raises:
        ValueError with detailed validation errors if invalid

    Returns:
        Parsed model instance
    """
    try:
        return model(**data)
    except Exception as e:
        raise ValueError(f"Validation failed: {str(e)}")


# Export all schemas
__all__ = [
    # Enums
    'FeedbackType', 'UserTier', 'TaskStatus', 'BuildStatus',
    # User inputs
    'UserMessageInput', 'VoiceMessageInput', 'FileUploadInput',
    # Feedback
    'FeedbackSubmission', 'FeedbackStatusQuery',
    # Admin
    'AdminCommand', 'UserManagement',
    # Build system
    'BuildRequest', 'DeploymentRequest',
    # Auth
    'APIKeyGeneration', 'JWTTokenRequest',
    # Webhooks
    'WebhookPayload',
    # Characters
    'CharacterMessage', 'SceneGeneration',
    # Helpers
    'validate_model', 'validate_and_parse'
]
