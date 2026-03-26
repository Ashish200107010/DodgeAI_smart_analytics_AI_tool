from __future__ import annotations


class AppError(Exception):
    pass


class NotFoundError(AppError):
    pass


class BadRequestError(AppError):
    pass


class DependencyError(AppError):
    """Raised when a required dependency (DB, graph projection, LLM) is missing."""

