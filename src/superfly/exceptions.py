"""Custom exceptions for superfly."""


class SuperflyError(Exception):
    """Base exception for all superfly errors."""

    pass


class AuthenticationError(SuperflyError):
    """Raised when CAVE/FlyWire authentication fails."""

    pass


class RegionNotFoundError(SuperflyError):
    """Raised when a requested anatomical region is not found."""

    pass


class EmptyGraphError(SuperflyError):
    """Raised when graph construction yields no neurons/edges."""

    pass
