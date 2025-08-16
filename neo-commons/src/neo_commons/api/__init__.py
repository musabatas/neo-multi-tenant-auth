"""
API utilities for FastAPI applications.

This module provides common API components that can be used across
all services in the NeoMultiTenant platform.
"""

from .exception_handlers import ExceptionHandlerRegistry, register_exception_handlers

__all__ = [
    "ExceptionHandlerRegistry",
    "register_exception_handlers",
]