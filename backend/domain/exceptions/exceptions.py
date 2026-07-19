# Custom domain exceptions

class DomainException(Exception):
    """Base exception class for domain-specific errors."""
    pass

class InvalidTransition(DomainException):
    """Raised when an invalid state transition is attempted."""
    pass

class InvalidGraph(DomainException):
    """Raised when a graph structure violates domain rules."""
    pass

class InvalidChunk(DomainException):
    """Raised when a chunk structure or data is invalid."""
    pass

class InvalidMetadata(DomainException):
    """Raised when metadata validation fails."""
    pass

class InvalidEmbedding(DomainException):
    """Raised when embedding validation fails."""
    pass

class ValidationError(DomainException):
    """Generic domain validation error."""
    pass

class ContractViolation(DomainException):
    """Raised when data violates the DTO/Contract schemas."""
    pass
