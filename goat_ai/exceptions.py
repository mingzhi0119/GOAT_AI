"""Domain exceptions for the shared goat_ai layer (no HTTP imports)."""

from __future__ import annotations


class GoatAIError(Exception):
    """Base class for all GOAT AI domain errors."""


class OllamaUnavailable(GoatAIError):
    """Raised when Ollama cannot be reached or returns an unexpected HTTP error."""


class UploadParseError(GoatAIError):
    """Raised when a CSV/XLSX file cannot be parsed."""


class UploadTooLarge(GoatAIError):
    """Raised when an uploaded file exceeds the configured size limit."""


class UploadTooManyRows(GoatAIError):
    """Raised when a parsed DataFrame exceeds the configured row limit."""
