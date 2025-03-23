"""
Exception classes for the summary service.
"""


class SummaryError(Exception):
    """Base class for summary-related errors."""
    pass


class StateNotFoundError(SummaryError):
    """Raised when state cannot be found."""
    pass


class SummaryGenerationError(SummaryError):
    """Raised when summary generation fails."""
    pass