"""Custom exception hierarchy for the Scrawl tool."""

from __future__ import annotations


class ScrawlError(Exception):
    """Base exception for all Scrawl tool errors."""


class ProjectNotFoundError(ScrawlError):
    """Raised when project.json is missing or path doesn't exist."""


class InvalidProjectError(ScrawlError):
    """Raised when project.json is malformed or not valid JSON."""


class CorruptArchiveError(ScrawlError):
    """Raised when .sb3 file is not a valid ZIP archive."""


class AssetMissingError(ScrawlError):
    """Raised when a referenced asset file cannot be found."""


class SpriteNotFoundError(ScrawlError):
    """Raised when a named sprite doesn't exist in the project."""


class VariableNotFoundError(ScrawlError):
    """Raised when a named variable doesn't exist in scope."""


class ValidationError(ScrawlError):
    """Raised for project validation failures. Contains a list of issues."""

    def __init__(self, issues: list):
        self.issues = issues
        super().__init__(f"{len(issues)} validation issue(s) found")
