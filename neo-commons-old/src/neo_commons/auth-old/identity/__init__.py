"""
Identity Resolution Module

User identity resolution for multi-provider authentication environments.
"""

from .resolver import DefaultUserIdentityResolver

__all__ = ["DefaultUserIdentityResolver"]