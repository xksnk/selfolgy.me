"""
Real-time monitoring and metrics system for Selfology bot.
Tracks performance, usage, and system health.
"""

import asyncio
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict
import json
from pathlib import Path

from .logging import LoggerMixin, get_logger, metrics_logger
from .error_handling import error_tracker


@dataclass
class MetricPoint:
    """A single metric measurement"""
    timestamp: datetime
    metric_name: str
    value: Any
    tags: Dict[str, str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp.isoformat(),
            'metric_name': self.metric_name,
            'value': self.value,
            'tags': self.tags
        }


class MetricsCollector(LoggerMixin):
    """
    Collects and stores system metrics for monitoring and analysis.
    """
    
    def __init__(self, max_points: int = 10000):
        self.metrics = defaultdict(deque)
        self.max_points = max_points
        self.start_time = datetime.now(timezone.utc)
        
        # System counters
        self.counters = defaultdict(int)
        self.gauges = defaultdict(float)
        self.timers = defaultdict(list)
        
        # Performance tracking
        self.response_times = deque(maxlen=1000)
        self.error_rates = deque(maxlen=1000)
        
    def increment(self, metric_name: str, value: int = 1, tags: Dict[str, str] = None):
        """Increment a counter metric"""
        self.counters[metric_name] += value
        
        point = MetricPoint(
            timestamp=datetime.now(timezone.utc),
            metric_name=metric_name,
            value=self.counters[metric_name],
            tags=tags or {}
        )
        
        self._add_point(point)
        
    def gauge(self, metric_name: str, value: float, tags: Dict[str, str] = None):
        """Set a gauge metric value"""
        self.gauges[metric_name] = value
        
        point = MetricPoint(
            timestamp=datetime.now(timezone.utc),
            metric_name=metric_name,
            value=value,
            tags=tags or {}
        )
        
        self._add_point(point)
    
    def timer(self, metric_name: str, duration: float, tags: Dict[str, str] = None):
        """Record a timing metric"""
        self.timers[metric_name].append(duration)
        
        # Keep only recent timings
        if len(self.timers[metric_name]) > 1000:
            self.timers[metric_name] = self.timers[metric_name][-1000:]
        
        point = MetricPoint(
            timestamp=datetime.now(timezone.utc),
            metric_name=metric_name,
            value=duration,
            tags=tags or {}
        )
        
        self._add_point(point)
    
    def _add_point(self, point: MetricPoint):
        """Add metric point to storage"""
        queue = self.metrics[point.metric_name]
        queue.append(point)
        
        # Limit queue size
        if len(queue) > self.max_points:
            queue.popleft()
        
        # Log metric
        extra = {
            'metric_name': point.metric_name,
            'metric_value': point.value,
            'context': {'tags': point.tags}
        }
        metrics_logger.info(f"Metric: {point.metric_name}={point.value}", extra=extra)
    
    def get_metric_stats(self, metric_name: str, time_window: timedelta = None) -> Dict[str, Any]:
        """Get statistics for a specific metric"""
        if metric_name not in self.metrics:
            return {}
        
        points = list(self.metrics[metric_name])
        
        # Filter by time window if specified
        if time_window:
            cutoff = datetime.now(timezone.utc) - time_window
            points = [p for p in points if p.timestamp > cutoff]
        
        if not points:
            return {}
        
        values = [p.value for p in points if isinstance(p.value, (int, float))]
        if not values:
            return {'count': len(points), 'latest': points[-1].value}
        
        return {
            'count': len(values),
            'latest': values[-1],
            'min': min(values),
            'max': max(values),
            'avg': sum(values) / len(values),
            'sum': sum(values)
        }
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get current state of all metrics"""
        return {
            'counters': dict(self.counters),
            'gauges': dict(self.gauges),
            'uptime_seconds': (datetime.now(timezone.utc) - self.start_time).total_seconds()
        }


class PerformanceMonitor(LoggerMixin):
    """
    Monitors system performance and health metrics.
    """
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self.health_checks = {}
        self.last_health_check = None
        
    async def start_monitoring(self):
        """Start continuous monitoring tasks"""
        await asyncio.gather(
            self.collect_system_metrics(),
            self.monitor_bot_health(),
            self.monitor_error_rates(),
            return_exceptions=True
        )
    
    async def collect_system_metrics(self):
        """Collect system performance metrics"""
        while True:
            try:
                import psutil
                
                # CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)
                self.metrics.gauge('system.cpu_percent', cpu_percent)
                
                # Memory usage
                memory = psutil.virtual_memory()
                self.metrics.gauge('system.memory_percent', memory.percent)
                self.metrics.gauge('system.memory_available_mb', memory.available / 1024 / 1024)
                
                # Disk usage
                disk = psutil.disk_usage('/')
                self.metrics.gauge('system.disk_percent', (disk.used / disk.total) * 100)
                
                await asyncio.sleep(60)  # Collect every minute
                
            except ImportError:
                # psutil not available, skip system metrics
                await asyncio.sleep(300)  # Check every 5 minutes
            except Exception as e:
                self.log_error("MONITORING_ERROR", f"Error collecting system metrics: {e}")
                await asyncio.sleep(60)
    
    async def monitor_bot_health(self):
        """Monitor bot health and connectivity"""
        while True:
            try:
                health_status = await self.check_bot_health()
                self.metrics.gauge('bot.health_score', health_status['score'])
                
                # Log health check results
                self.log_metric('bot_health_check', health_status['score'], 
                              healthy=health_status['healthy'])
                
                self.last_health_check = datetime.now(timezone.utc)
                
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                self.log_error("HEALTH_CHECK_ERROR", f"Health check failed: {e}")
                await asyncio.sleep(60)
    
    async def monitor_error_rates(self):
        """Monitor and alert on error rates"""
        while True:
            try:
                error_stats = error_tracker.get_error_stats()
                
                # Calculate error rate per minute
                total_errors = error_stats['total_errors']
                recent_errors = error_stats['recent_errors']
                
                self.metrics.gauge('errors.total', total_errors)
                self.metrics.gauge('errors.recent_per_hour', recent_errors)
                
                # Check for error spikes
                if recent_errors > 50:  # More than 50 errors per hour
                    self.log_error("HIGH_ERROR_RATE", 
                                 f"High error rate: {recent_errors} errors in last hour")
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                self.log_error("ERROR_MONITORING_FAILED", f"Error rate monitoring failed: {e}")
                await asyncio.sleep(60)
    
    async def check_bot_health(self) -> Dict[str, Any]:
        """Perform comprehensive bot health check"""
        health_score = 100
        issues = []
        
        try:
            # Check database connectivity
            # This would be implemented with actual DB check
            db_healthy = True  # Placeholder
            if not db_healthy:
                health_score -= 30
                issues.append("Database connectivity issues")
            
            # Check AI service availability
            ai_healthy = True  # Placeholder - would check AI APIs
            if not ai_healthy:
                health_score -= 20
                issues.append("AI service issues")
            
            # Check vector database
            vector_healthy = True  # Placeholder
            if not vector_healthy:
                health_score -= 20
                issues.append("Vector database issues")
            
            # Check error rate
            error_stats = error_tracker.get_error_stats()
            if error_stats['recent_errors'] > 100:
                health_score -= 15
                issues.append("High error rate")
            
            # Check memory usage (if available)
            try:
                import psutil
                memory = psutil.virtual_memory()
                if memory.percent > 90:
                    health_score -= 15
                    issues.append("High memory usage")
            except ImportError:
                pass
            
        except Exception as e:
            health_score = 0
            issues.append(f"Health check failed: {e}")
        
        return {
            'healthy': health_score > 70,
            'score': max(0, health_score),
            'issues': issues,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }


class BotAnalytics(LoggerMixin):
    """
    Track and analyze bot usage patterns and user behavior.
    """
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
        self.user_sessions = {}
        self.daily_stats = defaultdict(int)
        
    def track_user_action(self, user_id: int, action: str, **context):
        """Track user action for analytics"""
        self.metrics.increment(f'user_actions.{action}', tags={
            'user_id': str(user_id),
            'action': action
        })
        
        # Track unique users
        today = datetime.now(timezone.utc).date()
        self.daily_stats[f'unique_users_{today}'] = len(set([user_id] + 
            [int(k.split('_')[-1]) for k in self.daily_stats.keys() 
             if k.startswith(f'user_seen_{today}')]))
        
        # Log user action
        self.log_user_action(action, user_id, **context)
    
    def track_conversation_flow(self, user_id: int, from_state: str, to_state: str):
        """Track conversation flow transitions"""
        flow_key = f'{from_state}->{to_state}'
        self.metrics.increment(f'conversation_flows.{flow_key}', tags={
            'user_id': str(user_id),
            'from_state': from_state,
            'to_state': to_state
        })
    
    def track_ai_usage(self, user_id: int, model: str, tokens: int, cost: float, response_time: float):
        """Track AI service usage"""
        self.metrics.increment('ai.requests', tags={'model': model})
        self.metrics.gauge('ai.tokens_used', tokens, tags={'model': model})
        self.metrics.gauge('ai.cost', cost, tags={'model': model})
        self.metrics.timer('ai.response_time', response_time, tags={'model': model})
        
        # Log AI interaction
        self.log_ai_interaction(model, tokens, cost, response_time, user_id=user_id)
    
    def get_analytics_summary(self, days: int = 7) -> Dict[str, Any]:
        """Get analytics summary for specified period"""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        
        summary = {
            'period_days': days,
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'user_metrics': {
                'total_actions': self.metrics.get_metric_stats('user_actions', 
                                                             timedelta(days=days)),
                'conversation_flows': {},
                'ai_usage': {}
            },
            'system_metrics': {
                'uptime': self.metrics.get_all_metrics()['uptime_seconds'],
                'error_rate': error_tracker.get_error_stats(),
                'performance': {}
            }
        }
        
        return summary


class DashboardGenerator:
    """
    Generate monitoring dashboard data and reports.
    """
    
    def __init__(self, metrics_collector: MetricsCollector, analytics: BotAnalytics):
        self.metrics = metrics_collector
        self.analytics = analytics
    
    def generate_dashboard_data(self) -> Dict[str, Any]:
        """Generate data for monitoring dashboard"""
        now = datetime.now(timezone.utc)
        
        dashboard = {
            'timestamp': now.isoformat(),
            'system_status': {
                'uptime_hours': self.metrics.get_all_metrics()['uptime_seconds'] / 3600,
                'error_count': error_tracker.get_error_stats()['total_errors'],
                'recent_errors': error_tracker.get_error_stats()['recent_errors'],
                'health_status': 'healthy'  # Would be determined by health checks
            },
            'user_activity': {
                'active_users_24h': self.metrics.get_metric_stats('user_actions', timedelta(days=1)),
                'total_conversations': self.metrics.counters.get('conversations_started', 0),
                'messages_processed': self.metrics.counters.get('messages_processed', 0)
            },
            'ai_usage': {
                'total_requests': self.metrics.counters.get('ai.requests', 0),
                'avg_response_time': self.get_avg_ai_response_time(),
                'total_cost': self.get_total_ai_cost()
            },
            'performance': {
                'cpu_usage': self.metrics.gauges.get('system.cpu_percent', 0),
                'memory_usage': self.metrics.gauges.get('system.memory_percent', 0),
                'disk_usage': self.metrics.gauges.get('system.disk_percent', 0)
            }
        }
        
        return dashboard
    
    def get_avg_ai_response_time(self) -> float:
        """Calculate average AI response time"""
        response_times = self.metrics.timers.get('ai.response_time', [])
        return sum(response_times) / len(response_times) if response_times else 0.0
    
    def get_total_ai_cost(self) -> float:
        """Calculate total AI costs"""
        # This would aggregate cost metrics over time
        return self.metrics.gauges.get('ai.total_cost', 0.0)
    
    async def save_dashboard_snapshot(self):
        """Save dashboard snapshot to file"""
        dashboard_data = self.generate_dashboard_data()
        
        # Create dashboard directory
        dashboard_dir = Path("logs/dashboard")
        dashboard_dir.mkdir(exist_ok=True)
        
        # Save with timestamp
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = dashboard_dir / f"dashboard_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(dashboard_data, f, indent=2, ensure_ascii=False)


# Global instances
metrics_collector = MetricsCollector()
performance_monitor = PerformanceMonitor(metrics_collector)
bot_analytics = BotAnalytics(metrics_collector)
dashboard_generator = DashboardGenerator(metrics_collector, bot_analytics)


# Convenience functions
def track_user_action(user_id: int, action: str, **context):
    """Track user action"""
    bot_analytics.track_user_action(user_id, action, **context)


def track_performance(metric_name: str, duration: float, **tags):
    """Track performance metric"""
    metrics_collector.timer(metric_name, duration, tags)


def increment_counter(metric_name: str, value: int = 1, **tags):
    """Increment counter metric"""
    metrics_collector.increment(metric_name, value, tags)


def set_gauge(metric_name: str, value: float, **tags):
    """Set gauge metric"""
    metrics_collector.gauge(metric_name, value, tags)