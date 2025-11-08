"""Domain exceptions."""


class SelfologyException(Exception):
    """Base exception for Selfology application."""
    
    def __init__(self, message: str, code: str = None):
        self.message = message
        self.code = code
        super().__init__(message)


class UserNotFoundError(SelfologyException):
    """User not found error."""
    
    def __init__(self, telegram_id: int):
        super().__init__(
            message=f"User with Telegram ID {telegram_id} not found",
            code="USER_NOT_FOUND"
        )


class TierLimitExceededError(SelfologyException):
    """User tier limit exceeded error."""
    
    def __init__(self, limit_type: str, tier: str):
        super().__init__(
            message=f"{limit_type} limit exceeded for {tier} tier",
            code="TIER_LIMIT_EXCEEDED"
        )


class AIServiceError(SelfologyException):
    """AI service error."""
    
    def __init__(self, service: str, details: str = None):
        message = f"AI service error in {service}"
        if details:
            message += f": {details}"
        
        super().__init__(
            message=message,
            code="AI_SERVICE_ERROR"
        )


class VectorServiceError(SelfologyException):
    """Vector service error."""
    
    def __init__(self, operation: str, details: str = None):
        message = f"Vector service error during {operation}"
        if details:
            message += f": {details}"
        
        super().__init__(
            message=message,
            code="VECTOR_SERVICE_ERROR"
        )


class ValidationError(SelfologyException):
    """Domain validation error."""
    
    def __init__(self, field: str, value: str, reason: str = None):
        message = f"Invalid {field}: {value}"
        if reason:
            message += f" - {reason}"
        
        super().__init__(
            message=message,
            code="VALIDATION_ERROR"
        )