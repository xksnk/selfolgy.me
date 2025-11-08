"""Telegram ID value object."""

from dataclasses import dataclass
from typing import Union


@dataclass(frozen=True)
class TelegramId:
    """Value object for Telegram user IDs."""
    
    value: int
    
    def __post_init__(self) -> None:
        """Validate Telegram ID."""
        if not isinstance(self.value, int):
            raise ValueError("Telegram ID must be an integer")
        
        if self.value <= 0:
            raise ValueError("Telegram ID must be positive")
    
    def __str__(self) -> str:
        """String representation."""
        return str(self.value)
    
    @classmethod
    def from_string(cls, value: Union[str, int]) -> "TelegramId":
        """Create TelegramId from string or int."""
        if isinstance(value, str):
            try:
                value = int(value)
            except ValueError:
                raise ValueError(f"Invalid Telegram ID format: {value}")
        
        return cls(value)