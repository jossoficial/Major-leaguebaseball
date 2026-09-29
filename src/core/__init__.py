"""Application-level exceptions and error context."""


class MLBPipelineError(Exception):
    """Base exception for expected pipeline failures."""


class ExternalServiceError(MLBPipelineError):
    """An upstream data provider could not be reached or returned invalid data."""


class ConfigurationError(MLBPipelineError):
    """Application configuration is missing or invalid."""
