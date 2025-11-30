"""
Enterprise-grade logging system with correlation IDs, distributed tracing, and structured logging.
Enhances the existing Selfology logging with comprehensive monitoring capabilities.
"""

import json
import logging
import sys
import uuid
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, List, Union
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import traceback
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, asdict, field
from enum import Enum
import threading
from collections import defaultdict, deque
import asyncio

# Context variables for tracking request context across async boundaries
trace_id_context: ContextVar[str] = ContextVar('trace_id', default=None)
span_id_context: ContextVar[str] = ContextVar('span_id', default=None)
user_id_context: ContextVar[int] = ContextVar('user_id', default=None)
operation_context: ContextVar[str] = ContextVar('operation', default=None)


class LogLevel(Enum):
    """Enhanced log levels for enterprise monitoring"""
    TRACE = 5
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50
    SECURITY = 60
    AUDIT = 70


class EventType(Enum):
    """Standardized event types for classification"""
    USER_ACTION = "user_action"
    SYSTEM_EVENT = "system_event"
    ERROR_EVENT = "error_event"
    PERFORMANCE_EVENT = "performance_event"
    SECURITY_EVENT = "security_event"
    AI_INTERACTION = "ai_interaction"
    DATABASE_EVENT = "database_event"
    API_REQUEST = "api_request"
    HEALTH_CHECK = "health_check"
    BUSINESS_EVENT = "business_event"


@dataclass
class TraceContext:
    """Distributed tracing context"""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    operation_name: str = ""
    start_time: float = field(default_factory=time.time)
    tags: Dict[str, Any] = field(default_factory=dict)
    baggage: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LogEntry:
    """Structured log entry with enterprise features"""
    timestamp: str
    level: str
    logger: str
    message: str
    trace_context: Optional[TraceContext] = None
    user_id: Optional[int] = None
    session_id: Optional[str] = None
    event_type: Optional[EventType] = None
    module: Optional[str] = None
    function: Optional[str] = None
    line: Optional[int] = None
    duration: Optional[float] = None
    error_code: Optional[str] = None
    correlation_id: Optional[str] = None
    service_name: str = "selfology"
    service_version: str = "1.0.0"
    environment: str = "development"
    context: Dict[str, Any] = field(default_factory=dict)
    tags: Dict[str, str] = field(default_factory=dict)
    metrics: Dict[str, float] = field(default_factory=dict)
    exception: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        # Convert trace_context to dict if present
        if self.trace_context:
            data['trace_context'] = self.trace_context.to_dict()
        # Convert enum to string
        if self.event_type:
            data['event_type'] = self.event_type.value
        return data


class EnhancedFormatter(logging.Formatter):
    """Enterprise-grade formatter with correlation IDs and structured data"""
    
    def format(self, record) -> str:
        # Get trace context from context vars
        trace_id = trace_id_context.get(None)
        span_id = span_id_context.get(None)
        user_id = user_id_context.get(None)
        operation = operation_context.get(None)
        
        # Create trace context if available
        trace_context = None
        if trace_id and span_id:
            trace_context = TraceContext(
                trace_id=trace_id,
                span_id=span_id,
                operation_name=operation or record.funcName
            )
        
        # Create structured log entry
        log_entry = LogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            level=record.levelname,
            logger=record.name,
            message=record.getMessage(),
            trace_context=trace_context,
            user_id=user_id,
            module=record.module,
            function=record.funcName,
            line=record.lineno
        )
        
        # Add extra fields from record
        for attr in ['user_id', 'session_id', 'event_type', 'duration', 'error_code', 
                    'correlation_id', 'service_name', 'service_version', 'environment',
                    'context', 'tags', 'metrics']:
            if hasattr(record, attr):
                setattr(log_entry, attr, getattr(record, attr))
        
        # Add exception info if present
        if record.exc_info:
            log_entry.exception = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        return json.dumps(log_entry.to_dict(), ensure_ascii=False, separators=(',', ':'))


class CorrelationIDGenerator:
    """Generate correlation IDs for request tracking"""
    
    @staticmethod
    def generate_trace_id() -> str:
        """Generate unique trace ID"""
        return str(uuid.uuid4())
    
    @staticmethod
    def generate_span_id() -> str:
        """Generate unique span ID"""
        return str(uuid.uuid4())[:8]
    
    @staticmethod
    def generate_correlation_id() -> str:
        """Generate correlation ID"""
        return str(uuid.uuid4())


class DistributedTracer:
    """Distributed tracing implementation"""
    
    def __init__(self):
        self.active_spans = {}
        self.span_storage = deque(maxlen=10000)
        self.lock = threading.Lock()
    
    def start_span(self, operation_name: str, parent_span_id: str = None, **tags) -> TraceContext:
        """Start a new span"""
        trace_id = trace_id_context.get(None)
        if not trace_id:
            trace_id = CorrelationIDGenerator.generate_trace_id()
            trace_id_context.set(trace_id)
        
        span_id = CorrelationIDGenerator.generate_span_id()
        
        context = TraceContext(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            operation_name=operation_name,
            start_time=time.time(),
            tags=tags
        )
        
        with self.lock:
            self.active_spans[span_id] = context
        
        # Set context vars
        span_id_context.set(span_id)
        operation_context.set(operation_name)
        
        return context
    
    def finish_span(self, span_id: str, **tags):
        """Finish a span and record duration"""
        with self.lock:
            if span_id in self.active_spans:
                context = self.active_spans.pop(span_id)
                context.tags.update(tags)
                context.tags['duration'] = time.time() - context.start_time
                
                # Store completed span
                self.span_storage.append(context)
    
    def get_active_spans(self) -> Dict[str, TraceContext]:
        """Get all active spans"""
        with self.lock:
            return self.active_spans.copy()
    
    def get_trace_spans(self, trace_id: str) -> List[TraceContext]:
        """Get all spans for a trace"""
        return [span for span in self.span_storage if span.trace_id == trace_id]


class ErrorTracker:
    """Enhanced error tracking with pattern detection"""
    
    def __init__(self):
        self.error_counts = defaultdict(int)
        self.error_patterns = defaultdict(list)
        self.recent_errors = deque(maxlen=1000)
        self.error_thresholds = {
            'critical': 5,  # errors per minute
            'high': 20,     # errors per hour
            'medium': 100   # errors per day
        }
        self.lock = threading.Lock()
    
    def track_error(self, error_code: str, error_msg: str, context: Dict[str, Any] = None):
        """Track error occurrence"""
        timestamp = time.time()
        
        error_entry = {
            'timestamp': timestamp,
            'error_code': error_code,
            'message': error_msg,
            'context': context or {},
            'trace_id': trace_id_context.get(None),
            'user_id': user_id_context.get(None)
        }
        
        with self.lock:
            self.error_counts[error_code] += 1
            self.error_patterns[error_code].append(error_entry)
            self.recent_errors.append(error_entry)
            
            # Keep only recent patterns (last 24 hours)
            cutoff = timestamp - 86400
            self.error_patterns[error_code] = [
                e for e in self.error_patterns[error_code] 
                if e['timestamp'] > cutoff
            ]
    
    def get_error_stats(self, time_window: int = 3600) -> Dict[str, Any]:
        """Get error statistics for time window"""
        cutoff = time.time() - time_window
        
        with self.lock:
            recent_errors = [e for e in self.recent_errors if e['timestamp'] > cutoff]
            
            stats = {
                'total_errors': len(recent_errors),
                'error_rate': len(recent_errors) / (time_window / 60),  # per minute
                'unique_errors': len(set(e['error_code'] for e in recent_errors)),
                'top_errors': self._get_top_errors(recent_errors),
                'error_distribution': self._get_error_distribution(recent_errors)
            }
        
        return stats
    
    def _get_top_errors(self, errors: List[Dict]) -> List[Dict]:
        """Get top occurring errors"""
        error_counts = defaultdict(int)
        for error in errors:
            error_counts[error['error_code']] += 1
        
        return sorted(
            [{'error_code': code, 'count': count} for code, count in error_counts.items()],
            key=lambda x: x['count'],
            reverse=True
        )[:10]
    
    def _get_error_distribution(self, errors: List[Dict]) -> Dict[str, int]:
        """Get error distribution by hour"""
        distribution = defaultdict(int)
        for error in errors:
            hour = datetime.fromtimestamp(error['timestamp']).strftime('%H:00')
            distribution[hour] += 1
        return dict(distribution)


class PerformanceProfiler:
    """Performance profiling and bottleneck detection"""
    
    def __init__(self):
        self.operation_stats = defaultdict(list)
        self.slow_operations = deque(maxlen=100)
        self.thresholds = {
            'database_query': 1.0,      # 1 second
            'ai_request': 5.0,          # 5 seconds
            'user_response': 3.0,       # 3 seconds
            'default': 2.0              # 2 seconds
        }
        self.lock = threading.Lock()
    
    def record_operation(self, operation: str, duration: float, **context):
        """Record operation performance"""
        timestamp = time.time()
        
        with self.lock:
            self.operation_stats[operation].append({
                'duration': duration,
                'timestamp': timestamp,
                'context': context
            })
            
            # Keep only recent stats (last hour)
            cutoff = timestamp - 3600
            self.operation_stats[operation] = [
                stat for stat in self.operation_stats[operation]
                if stat['timestamp'] > cutoff
            ]
            
            # Track slow operations
            threshold = self.thresholds.get(operation, self.thresholds['default'])
            if duration > threshold:
                self.slow_operations.append({
                    'operation': operation,
                    'duration': duration,
                    'timestamp': timestamp,
                    'context': context,
                    'trace_id': trace_id_context.get(None)
                })
    
    def get_performance_stats(self, operation: str = None) -> Dict[str, Any]:
        """Get performance statistics"""
        with self.lock:
            if operation:
                stats = self.operation_stats.get(operation, [])
                if not stats:
                    return {}
                
                durations = [s['duration'] for s in stats]
                return {
                    'operation': operation,
                    'count': len(durations),
                    'avg_duration': sum(durations) / len(durations),
                    'min_duration': min(durations),
                    'max_duration': max(durations),
                    'p95_duration': self._percentile(durations, 95),
                    'p99_duration': self._percentile(durations, 99)
                }
            
            else:
                # Return stats for all operations
                all_stats = {}
                for op, stats in self.operation_stats.items():
                    if stats:
                        durations = [s['duration'] for s in stats]
                        all_stats[op] = {
                            'count': len(durations),
                            'avg_duration': sum(durations) / len(durations),
                            'max_duration': max(durations)
                        }
                
                return all_stats
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile"""
        sorted_data = sorted(data)
        index = int((percentile / 100) * len(sorted_data))
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    def get_slow_operations(self, limit: int = 10) -> List[Dict]:
        """Get recent slow operations"""
        with self.lock:
            return list(self.slow_operations)[-limit:]


class AlertManager:
    """Smart alerting system with escalation policies"""
    
    def __init__(self):
        self.alert_rules = []
        self.active_alerts = {}
        self.alert_history = deque(maxlen=1000)
        self.escalation_policies = {
            'critical': {'immediate': True, 'retry_interval': 300},
            'high': {'immediate': False, 'retry_interval': 900},
            'medium': {'immediate': False, 'retry_interval': 3600}
        }
        self.lock = threading.Lock()
    
    def add_alert_rule(self, name: str, condition: callable, severity: str, message: str):
        """Add alert rule"""
        self.alert_rules.append({
            'name': name,
            'condition': condition,
            'severity': severity,
            'message': message
        })
    
    def check_alerts(self, metrics: Dict[str, Any]):
        """Check all alert rules against current metrics"""
        with self.lock:
            for rule in self.alert_rules:
                try:
                    if rule['condition'](metrics):
                        self._trigger_alert(rule)
                except Exception as e:
                    logger.error(f"Alert rule check failed: {rule['name']}: {e}")
    
    def _trigger_alert(self, rule: Dict[str, Any]):
        """Trigger an alert"""
        alert_id = f"{rule['name']}_{int(time.time())}"
        
        alert = {
            'id': alert_id,
            'name': rule['name'],
            'severity': rule['severity'],
            'message': rule['message'],
            'timestamp': time.time(),
            'acknowledged': False,
            'resolved': False
        }
        
        self.active_alerts[alert_id] = alert
        self.alert_history.append(alert)
        
        # Log alert
        logger.critical(f"ALERT: {rule['message']}", extra={
            'event_type': EventType.SECURITY_EVENT,
            'alert_id': alert_id,
            'severity': rule['severity']
        })


class EnhancedLoggerMixin:
    """Enhanced mixin with distributed tracing and correlation IDs"""
    
    @property
    def logger(self):
        """Get logger instance for the class"""
        if not hasattr(self, '_logger'):
            self._logger = logging.getLogger(f'selfology.{self.__class__.__name__}')
        return self._logger
    
    def start_trace(self, operation: str, **tags) -> TraceContext:
        """Start distributed trace"""
        return tracer.start_span(operation, **tags)
    
    def log_with_trace(self, level: str, message: str, **kwargs):
        """Log message with trace context"""
        extra = {
            'trace_id': trace_id_context.get(None),
            'span_id': span_id_context.get(None),
            'user_id': user_id_context.get(None),
            **kwargs
        }
        
        getattr(self.logger, level.lower())(message, extra=extra)
    
    def log_user_action(self, action: str, user_id: int, **context):
        """Log user action with enhanced context"""
        user_id_context.set(user_id)
        
        extra = {
            'event_type': EventType.USER_ACTION,
            'user_id': user_id,
            'context': context,
            'correlation_id': CorrelationIDGenerator.generate_correlation_id()
        }
        
        self.logger.info(f"User action: {action}", extra=extra)
    
    def log_performance(self, operation: str, duration: float, **context):
        """Log performance metric with profiling"""
        profiler.record_operation(operation, duration, **context)
        
        extra = {
            'event_type': EventType.PERFORMANCE_EVENT,
            'duration': duration,
            'operation': operation,
            'context': context
        }
        
        self.logger.info(f"Performance: {operation} completed in {duration:.3f}s", extra=extra)
    
    def log_error(self, error_code: str, message: str, **context):
        """Log error with enhanced tracking"""
        error_tracker.track_error(error_code, message, context)
        
        extra = {
            'event_type': EventType.ERROR_EVENT,
            'error_code': error_code,
            'context': context
        }
        
        self.logger.error(f"Error {error_code}: {message}", extra=extra)
    
    def log_security_event(self, event: str, **context):
        """Log security event"""
        extra = {
            'event_type': EventType.SECURITY_EVENT,
            'security_event': event,
            'context': context,
            'severity': 'high'
        }
        
        self.logger.warning(f"Security event: {event}", extra=extra)
    
    def log_business_event(self, event: str, **context):
        """Log business-critical event"""
        extra = {
            'event_type': EventType.BUSINESS_EVENT,
            'business_event': event,
            'context': context
        }
        
        self.logger.info(f"Business event: {event}", extra=extra)


@contextmanager
def trace_operation(operation_name: str, **tags):
    """Context manager for distributed tracing"""
    context = tracer.start_span(operation_name, **tags)
    start_time = time.time()
    
    try:
        yield context
        
        # Record successful completion
        duration = time.time() - start_time
        profiler.record_operation(operation_name, duration, status='success', **tags)
        
    except Exception as e:
        # Record error
        duration = time.time() - start_time
        profiler.record_operation(operation_name, duration, status='error', error=str(e), **tags)
        
        # Track error
        error_tracker.track_error(
            f"{operation_name.upper()}_ERROR",
            str(e),
            {'operation': operation_name, 'duration': duration, **tags}
        )
        
        raise
    
    finally:
        tracer.finish_span(context.span_id, **tags)


class EnhancedLoggingSystem:
    """Enterprise-grade logging system orchestrator"""
    
    def __init__(self, service_name: str = "selfology", environment: str = "development"):
        self.service_name = service_name
        self.environment = environment
        self.setup_directories()
        self.setup_logging()
        
    def setup_directories(self):
        """Create logging directories"""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # Create subdirectories for different log types
        for subdir in ['application', 'errors', 'users', 'ai', 'metrics', 
                      'security', 'performance', 'traces', 'alerts']:
            (log_dir / subdir).mkdir(exist_ok=True)
    
    def setup_logging(self):
        """Setup comprehensive logging configuration"""
        # Root logger configuration
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        root_logger.handlers.clear()
        
        # Console handler for development
        if self.environment == 'development':
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            console_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(console_formatter)
            root_logger.addHandler(console_handler)
        
        # Application log with enhanced formatting
        app_handler = RotatingFileHandler(
            "logs/application/selfology.log",
            maxBytes=100*1024*1024,  # 100MB
            backupCount=20,
            encoding='utf-8'
        )
        app_handler.setLevel(logging.INFO)
        app_handler.setFormatter(EnhancedFormatter())
        root_logger.addHandler(app_handler)
        
        # Error log with traces
        error_handler = TimedRotatingFileHandler(
            "logs/errors/errors.log",
            when='midnight',
            interval=1,
            backupCount=90,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(EnhancedFormatter())
        root_logger.addHandler(error_handler)
        
        # Trace log for distributed tracing
        trace_handler = TimedRotatingFileHandler(
            "logs/traces/traces.log",
            when='H',
            interval=1,
            backupCount=72,  # Keep 3 days
            encoding='utf-8'
        )
        trace_handler.setLevel(logging.DEBUG)
        trace_handler.setFormatter(EnhancedFormatter())
        
        trace_logger = logging.getLogger('selfology.traces')
        trace_logger.addHandler(trace_handler)
        
        # Performance log
        perf_handler = TimedRotatingFileHandler(
            "logs/performance/performance.log",
            when='H',
            interval=1,
            backupCount=48,  # Keep 2 days
            encoding='utf-8'
        )
        perf_handler.setLevel(logging.INFO)
        perf_handler.setFormatter(EnhancedFormatter())
        
        perf_logger = logging.getLogger('selfology.performance')
        perf_logger.addHandler(perf_handler)
        
        # Security log
        security_handler = TimedRotatingFileHandler(
            "logs/security/security.log",
            when='midnight',
            interval=1,
            backupCount=365,  # Keep 1 year
            encoding='utf-8'
        )
        security_handler.setLevel(logging.WARNING)
        security_handler.setFormatter(EnhancedFormatter())
        
        security_logger = logging.getLogger('selfology.security')
        security_logger.addHandler(security_handler)
        
        # Alert log
        alert_handler = TimedRotatingFileHandler(
            "logs/alerts/alerts.log",
            when='H',
            interval=1,
            backupCount=168,  # Keep 1 week
            encoding='utf-8'
        )
        alert_handler.setLevel(logging.CRITICAL)
        alert_handler.setFormatter(EnhancedFormatter())
        
        alert_logger = logging.getLogger('selfology.alerts')
        alert_logger.addHandler(alert_handler)
    
    def setup_default_alerts(self):
        """Setup default alert rules"""
        # High error rate
        alert_manager.add_alert_rule(
            'high_error_rate',
            lambda m: m.get('error_rate', 0) > 10,  # 10 errors per minute
            'high',
            'High error rate detected'
        )
        
        # Slow operations
        alert_manager.add_alert_rule(
            'slow_operations',
            lambda m: any(s.get('avg_duration', 0) > 5 for s in m.get('performance', {}).values()),
            'medium',
            'Slow operations detected'
        )
        
        # Memory usage
        alert_manager.add_alert_rule(
            'high_memory',
            lambda m: m.get('memory_usage', 0) > 90,
            'critical',
            'High memory usage detected'
        )


# Global instances
tracer = DistributedTracer()
error_tracker = ErrorTracker()
profiler = PerformanceProfiler()
alert_manager = AlertManager()

# Initialize enhanced logging system
enhanced_logging = None

def initialize_enhanced_logging(service_name: str = "selfology", environment: str = "development"):
    """Initialize the enhanced logging system"""
    global enhanced_logging
    enhanced_logging = EnhancedLoggingSystem(service_name, environment)
    enhanced_logging.setup_default_alerts()
    
    # Setup exception handler
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        logger = logging.getLogger('selfology.errors')
        logger.critical(
            "Uncaught exception",
            exc_info=(exc_type, exc_value, exc_traceback),
            extra={'error_code': 'UNCAUGHT_EXCEPTION', 'event_type': EventType.ERROR_EVENT}
        )
    
    sys.excepthook = handle_exception
    
    return enhanced_logging


# Convenience functions for common operations
def set_user_context(user_id: int):
    """Set user context for tracing"""
    user_id_context.set(user_id)

def get_trace_id() -> Optional[str]:
    """Get current trace ID"""
    return trace_id_context.get(None)

def get_monitoring_stats() -> Dict[str, Any]:
    """Get comprehensive monitoring statistics"""
    return {
        'errors': error_tracker.get_error_stats(),
        'performance': profiler.get_performance_stats(),
        'slow_operations': profiler.get_slow_operations(),
        'active_spans': len(tracer.get_active_spans()),
        'active_alerts': len(alert_manager.active_alerts)
    }

# Export enhanced logger
get_enhanced_logger = lambda name='selfology': logging.getLogger(name)
