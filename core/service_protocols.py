"""
Service Communication Protocols - Standardized interfaces between services
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ServiceResult:
    """Standardized result object for all service operations"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    processing_time: Optional[float] = None
    service_name: Optional[str] = None
    operation: Optional[str] = None


@dataclass
class ServiceError:
    """Standardized error information"""
    error_code: str
    error_message: str
    error_details: Optional[Dict[str, Any]] = None
    timestamp: datetime = datetime.utcnow()


class ServiceProtocol(ABC):
    """Base protocol for all services"""
    
    @property
    @abstractmethod
    def service_name(self) -> str:
        """Return the name of the service"""
        pass
    
    @abstractmethod
    async def health_check(self) -> ServiceResult:
        """Check if service is healthy and operational"""
        pass
    
    @abstractmethod
    async def get_service_info(self) -> ServiceResult:
        """Get information about the service (version, capabilities, etc.)"""
        pass


class AssessmentServiceProtocol(ServiceProtocol):
    """Protocol for Assessment Engine service"""
    
    @abstractmethod
    async def start_assessment(self, user_id: str, telegram_data: Dict[str, Any]) -> ServiceResult:
        """Start assessment for user"""
        pass
    
    @abstractmethod
    async def process_answer(self, user_id: str, question_id: str, answer_text: str) -> ServiceResult:
        """Process user answer to question"""
        pass
    
    @abstractmethod
    async def get_assessment_status(self, user_id: str) -> ServiceResult:
        """Get current assessment status for user"""
        pass


class ChatServiceProtocol(ServiceProtocol):
    """Protocol for Chat Coach service"""
    
    @abstractmethod
    async def start_chat_session(self, user_id: str) -> ServiceResult:
        """Start new chat session"""
        pass
    
    @abstractmethod
    async def process_message(self, user_id: str, message: str) -> ServiceResult:
        """Process chat message from user"""
        pass
    
    @abstractmethod
    async def get_conversation_history(self, user_id: str, limit: int = 20) -> ServiceResult:
        """Get conversation history for user"""
        pass


class StatisticsServiceProtocol(ServiceProtocol):
    """Protocol for Statistics service"""
    
    @abstractmethod
    async def get_user_statistics(self, user_id: str, include_detailed: bool = False) -> ServiceResult:
        """Get statistics for specific user"""
        pass
    
    @abstractmethod
    async def get_system_overview(self) -> ServiceResult:
        """Get system-wide statistics"""
        pass
    
    @abstractmethod
    async def get_engagement_analysis(self, days: int = 30) -> ServiceResult:
        """Get engagement analysis for specified period"""
        pass


class ProfileServiceProtocol(ServiceProtocol):
    """Protocol for User Profile service"""
    
    @abstractmethod
    async def get_profile(self, user_id: str, include_insights: bool = True) -> ServiceResult:
        """Get user profile with optional insights"""
        pass
    
    @abstractmethod
    async def export_profile_data(self, user_id: str) -> ServiceResult:
        """Export all user data (GDPR compliance)"""
        pass
    
    @abstractmethod
    async def delete_profile(self, user_id: str) -> ServiceResult:
        """Delete user profile completely (GDPR compliance)"""
        pass


class VectorServiceProtocol(ServiceProtocol):
    """Protocol for Vector service"""
    
    @abstractmethod
    async def store_personality_profile(self, user_id: str, personality_data: Dict[str, Any], 
                                      text_description: str) -> ServiceResult:
        """Store personality profile as vector"""
        pass
    
    @abstractmethod
    async def find_personality_matches(self, user_id: str, limit: int = 10,
                                     min_similarity: float = 0.7) -> ServiceResult:
        """Find users with similar personalities"""
        pass
    
    @abstractmethod
    async def update_personality_dimensions(self, user_id: str, 
                                          dimension_updates: Dict[str, float]) -> ServiceResult:
        """Update specific personality dimensions"""
        pass


class ServiceRegistry:
    """Registry for service discovery and communication"""
    
    def __init__(self):
        self._services: Dict[str, ServiceProtocol] = {}
    
    def register_service(self, service: ServiceProtocol):
        """Register a service in the registry"""
        self._services[service.service_name] = service
    
    def get_service(self, service_name: str) -> Optional[ServiceProtocol]:
        """Get a service by name"""
        return self._services.get(service_name)
    
    def list_services(self) -> List[str]:
        """List all registered service names"""
        return list(self._services.keys())
    
    async def health_check_all(self) -> Dict[str, ServiceResult]:
        """Check health of all registered services"""
        results = {}
        for name, service in self._services.items():
            try:
                results[name] = await service.health_check()
            except Exception as e:
                results[name] = ServiceResult(
                    success=False,
                    message=f"Health check failed: {str(e)}",
                    service_name=name
                )
        return results


class ServiceInterceptor:
    """Interceptor for cross-cutting concerns (logging, monitoring, etc.)"""
    
    def __init__(self, service: ServiceProtocol):
        self.service = service
    
    async def __call__(self, method_name: str, *args, **kwargs) -> ServiceResult:
        """Intercept service calls for logging and monitoring"""
        import time
        from ..core.logging import get_logger
        
        logger = get_logger(f"service_interceptor.{self.service.service_name}")
        start_time = time.time()
        
        try:
            # Log service call
            logger.log_service_call(method_name, 
                                   service=self.service.service_name,
                                   args_count=len(args),
                                   kwargs_count=len(kwargs))
            
            # Execute service method
            method = getattr(self.service, method_name)
            result = await method(*args, **kwargs)
            
            # Add processing time to result
            processing_time = time.time() - start_time
            if hasattr(result, 'processing_time') and result.processing_time is None:
                result.processing_time = processing_time
            
            # Add service info to result
            if hasattr(result, 'service_name') and result.service_name is None:
                result.service_name = self.service.service_name
            
            if hasattr(result, 'operation') and result.operation is None:
                result.operation = method_name
            
            # Log success
            logger.log_service_result(method_name, result.success, processing_time,
                                    service=self.service.service_name)
            
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            
            # Log error
            logger.log_error("SERVICE_CALL_ERROR", 
                           f"Service call failed: {method_name}",
                           exception=e,
                           service=self.service.service_name)
            
            # Return error result
            return ServiceResult(
                success=False,
                message=f"Service call failed: {str(e)}",
                processing_time=processing_time,
                service_name=self.service.service_name,
                operation=method_name
            )


class ServiceValidator:
    """Validator for service inputs and outputs"""
    
    @staticmethod
    def validate_user_id(user_id: str) -> bool:
        """Validate user ID format"""
        if not isinstance(user_id, str):
            return False
        if not user_id.strip():
            return False
        if len(user_id) > 50:  # Reasonable limit
            return False
        return True
    
    @staticmethod
    def validate_service_result(result: ServiceResult) -> bool:
        """Validate service result structure"""
        if not isinstance(result, ServiceResult):
            return False
        if not isinstance(result.success, bool):
            return False
        if not isinstance(result.message, str):
            return False
        return True
    
    @staticmethod
    def sanitize_user_input(text: str, max_length: int = 10000) -> str:
        """Sanitize user input text"""
        if not isinstance(text, str):
            return ""
        
        # Trim and limit length
        sanitized = text.strip()[:max_length]
        
        # Remove potential harmful patterns (basic)
        # In production, would use more sophisticated sanitization
        
        return sanitized


class ServiceMetrics:
    """Metrics collection for services"""
    
    def __init__(self):
        self.call_counts: Dict[str, int] = {}
        self.error_counts: Dict[str, int] = {}
        self.response_times: Dict[str, List[float]] = {}
    
    def record_call(self, service_name: str, method_name: str, 
                   success: bool, response_time: float):
        """Record service call metrics"""
        key = f"{service_name}.{method_name}"
        
        # Count calls
        self.call_counts[key] = self.call_counts.get(key, 0) + 1
        
        # Count errors
        if not success:
            self.error_counts[key] = self.error_counts.get(key, 0) + 1
        
        # Record response times
        if key not in self.response_times:
            self.response_times[key] = []
        self.response_times[key].append(response_time)
        
        # Keep only last 100 response times per method
        if len(self.response_times[key]) > 100:
            self.response_times[key] = self.response_times[key][-100:]
    
    def get_metrics(self, service_name: Optional[str] = None) -> Dict[str, Any]:
        """Get metrics for service or all services"""
        
        if service_name:
            # Filter metrics for specific service
            prefix = f"{service_name}."
            filtered_calls = {k: v for k, v in self.call_counts.items() if k.startswith(prefix)}
            filtered_errors = {k: v for k, v in self.error_counts.items() if k.startswith(prefix)}
            filtered_times = {k: v for k, v in self.response_times.items() if k.startswith(prefix)}
            
            return {
                "service": service_name,
                "call_counts": filtered_calls,
                "error_counts": filtered_errors,
                "response_times": filtered_times,
                "error_rate": self._calculate_error_rate(filtered_calls, filtered_errors),
                "avg_response_time": self._calculate_avg_response_time(filtered_times)
            }
        
        else:
            # Return all metrics
            return {
                "call_counts": self.call_counts,
                "error_counts": self.error_counts,
                "response_times": {k: len(v) for k, v in self.response_times.items()},
                "total_calls": sum(self.call_counts.values()),
                "total_errors": sum(self.error_counts.values()),
                "overall_error_rate": self._calculate_error_rate(self.call_counts, self.error_counts)
            }
    
    def _calculate_error_rate(self, calls: Dict[str, int], errors: Dict[str, int]) -> float:
        """Calculate error rate"""
        total_calls = sum(calls.values())
        total_errors = sum(errors.values())
        return (total_errors / total_calls) if total_calls > 0 else 0.0
    
    def _calculate_avg_response_time(self, response_times: Dict[str, List[float]]) -> float:
        """Calculate average response time"""
        all_times = []
        for times in response_times.values():
            all_times.extend(times)
        return sum(all_times) / len(all_times) if all_times else 0.0


# Global instances
service_registry = ServiceRegistry()
service_metrics = ServiceMetrics()


def create_service_interceptor(service: ServiceProtocol) -> ServiceInterceptor:
    """Create service interceptor with monitoring"""
    return ServiceInterceptor(service)


def validate_service_call(user_id: str = None, **kwargs) -> bool:
    """Validate common service call parameters"""
    if user_id and not ServiceValidator.validate_user_id(user_id):
        return False
    
    # Add more validation as needed
    return True