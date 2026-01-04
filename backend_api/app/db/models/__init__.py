"""Convenience imports for ORM models."""

from .auth import OTPVerificationRequest, User, UserRole
from .jobs import (
    ApplicationStatus,
    JobApplication,
    JobPost,
    JobStatus,
    MediaUpload,
    Notification,
)

__all__ = [
    "User",
    "UserRole",
    "OTPVerificationRequest",
    "JobPost",
    "JobStatus",
    "JobApplication",
    "ApplicationStatus",
    "MediaUpload",
    "Notification",
]
