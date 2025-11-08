"""Username value object."""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Username:
    """Value object for Telegram usernames."""
    
    value: str
    
    USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_]{5,32}$')
    
    def __post_init__(self) -> None:
        """Validate username."""
        if not isinstance(self.value, str):
            raise ValueError("Username must be a string")
        
        if not self.USERNAME_PATTERN.match(self.value):
            raise ValueError(
                "Username must be 5-32 characters long and contain only "
                "letters, numbers, and underscores"
            )
    
    def __str__(self) -> str:
        """String representation."""
        return self.value
    
    @property
    def with_at(self) -> str:
        """Username with @ prefix."""
        return f"@{self.value}"