"""
Shared Logging System for Selfology Services
"""
import logging
import logging.handlers
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import json

from .config import get_config


class SelfologyLogger:
    """Enhanced logger with service-specific features"""
    
    def __init__(self, name: str, service_name: Optional[str] = None):
        self.logger = logging.getLogger(name)
        self.service_name = service_name or name
        self.config = get_config()
        
        if not self.logger.handlers:
            self._setup_logger()
    
    def _setup_logger(self):
        """Setup logger with file and console handlers"""
        
        # Create logs directory
        log_dir = self.config.logging["file_path"]
        log_dir.mkdir(exist_ok=True)
        
        # Set level
        level = getattr(logging, self.config.logging["level"].upper())
        self.logger.setLevel(level)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_formatter = logging.Formatter(self.config.logging["format"])
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # File handler with rotation
        log_file = log_dir / f"{self.service_name}.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=self.config.logging["max_file_size"],
            backupCount=self.config.logging["backup_count"]
        )
        file_handler.setLevel(level)
        file_formatter = logging.Formatter(
            f"%(asctime)s - {self.service_name} - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
        
        # Service-specific log file
        service_log = log_dir / f"services.log"
        service_handler = logging.handlers.RotatingFileHandler(
            service_log,
            maxBytes=self.config.logging["max_file_size"],
            backupCount=self.config.logging["backup_count"]
        )
        service_handler.setLevel(level)
        service_handler.setFormatter(file_formatter)
        self.logger.addHandler(service_handler)
    
    def log_service_call(self, method: str, user_id: Optional[str] = None, **kwargs):
        """Log service method call"""
        context = {
            "service": self.service_name,
            "method": method,
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            **kwargs
        }
        
        self.logger.info(f"SERVICE_CALL: {method}", extra={"context": context})
    
    def log_service_result(self, method: str, success: bool = True, 
                          processing_time: Optional[float] = None, **kwargs):
        """Log service method result"""
        context = {
            "service": self.service_name,
            "method": method,
            "success": success,
            "processing_time": processing_time,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs
        }
        
        level = logging.INFO if success else logging.ERROR
        self.logger.log(level, f"SERVICE_RESULT: {method} ({'SUCCESS' if success else 'FAILED'})", 
                       extra={"context": context})
    
    def log_error(self, error_code: str, message: str, user_id: Optional[str] = None, 
                  exception: Optional[Exception] = None, **kwargs):
        """Log service error"""
        context = {
            "service": self.service_name,
            "error_code": error_code,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs
        }
        
        self.logger.error(f"SERVICE_ERROR: {error_code} - {message}", 
                         extra={"context": context}, exc_info=exception)
    
    def log_user_action(self, action: str, user_id: str, **kwargs):
        """Log user action for analytics"""
        context = {
            "action": action,
            "user_id": user_id,
            "service": self.service_name,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs
        }
        
        self.logger.info(f"USER_ACTION: {action}", extra={"context": context})
    
    def log_performance(self, operation: str, duration: float, **kwargs):
        """Log performance metrics"""
        context = {
            "service": self.service_name,
            "operation": operation,
            "duration_ms": round(duration * 1000, 2),
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs
        }
        
        self.logger.info(f"PERFORMANCE: {operation} - {duration*1000:.2f}ms", 
                        extra={"context": context})
    
    def info(self, message: str, **kwargs):
        """Standard info logging"""
        self.logger.info(message, extra=kwargs)
    
    def warning(self, message: str, **kwargs):
        """Standard warning logging"""
        self.logger.warning(message, extra=kwargs)
    
    def error(self, message: str, **kwargs):
        """Standard error logging"""
        self.logger.error(message, extra=kwargs)
    
    def debug(self, message: str, **kwargs):
        """Standard debug logging"""
        self.logger.debug(message, extra=kwargs)


class LoggerMixin:
    """Mixin to add logging capabilities to service classes"""
    
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        service_name = cls.__name__.lower().replace('service', '').replace('engine', '')
        cls._logger = SelfologyLogger(cls.__module__, service_name)
    
    @property
    def logger(self) -> SelfologyLogger:
        """Get logger instance"""
        return self._logger


def get_logger(name: str, service_name: Optional[str] = None) -> SelfologyLogger:
    """Get a logger instance for a service"""
    return SelfologyLogger(name, service_name)


# Service-specific loggers
assessment_logger = get_logger("selfology.assessment", "assessment_engine")
chat_logger = get_logger("selfology.chat", "chat_coach") 
statistics_logger = get_logger("selfology.statistics", "statistics_service")
vector_logger = get_logger("selfology.vector", "vector_service")
telegram_logger = get_logger("selfology.telegram", "telegram_interface")