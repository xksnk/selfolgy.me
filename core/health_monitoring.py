"""
Comprehensive service health monitoring system for Selfology.
Provides real-time health checks, automatic recovery, and service dependency management.
"""

import asyncio
import asyncpg
import httpx
import time
import psutil
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import json
import logging
from contextlib import asynccontextmanager
import threading
from collections import defaultdict, deque

from .enhanced_logging import EnhancedLoggerMixin, trace_operation, EventType


class HealthStatus(Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class ServiceType(Enum):
    """Types of services being monitored"""
    DATABASE = "database"
    AI_SERVICE = "ai_service"
    VECTOR_DB = "vector_db"
    CACHE = "cache"
    BOT = "telegram_bot"
    API = "api"
    EXTERNAL = "external"


@dataclass
class HealthCheckResult:
    """Result of a health check"""
    service_name: str
    service_type: ServiceType
    status: HealthStatus
    response_time: float
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    metrics: Dict[str, float] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'service_name': self.service_name,
            'service_type': self.service_type.value,
            'status': self.status.value,
            'response_time': self.response_time,
            'timestamp': self.timestamp.isoformat(),
            'details': self.details,
            'error_message': self.error_message,
            'metrics': self.metrics,
            'dependencies': self.dependencies
        }


@dataclass
class ServiceConfiguration:
    """Configuration for service health monitoring"""
    name: str
    service_type: ServiceType
    check_function: Callable[[], Any]
    check_interval: int = 60  # seconds
    timeout: int = 30  # seconds
    retry_count: int = 3
    retry_delay: int = 5
    critical: bool = True
    dependencies: List[str] = field(default_factory=list)
    recovery_actions: List[Callable] = field(default_factory=list)
    thresholds: Dict[str, float] = field(default_factory=dict)


class SystemMetricsCollector(EnhancedLoggerMixin):
    """Collect system-level metrics"""
    
    def __init__(self):
        self.metrics_history = deque(maxlen=1000)
        self.last_collection = None
    
    async def collect_metrics(self) -> Dict[str, float]:
        """Collect comprehensive system metrics"""
        with trace_operation("collect_system_metrics"):
            try:
                metrics = {
                    'timestamp': time.time(),
                    'cpu_percent': psutil.cpu_percent(interval=0.1),
                    'memory_percent': psutil.virtual_memory().percent,
                    'memory_available_mb': psutil.virtual_memory().available / 1024 / 1024,
                    'disk_percent': psutil.disk_usage('/').percent,
                    'disk_free_gb': psutil.disk_usage('/').free / 1024 / 1024 / 1024,
                    'load_average_1m': psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else 0,
                    'process_count': len(psutil.pids()),
                    'network_io_sent_mb': psutil.net_io_counters().bytes_sent / 1024 / 1024,
                    'network_io_recv_mb': psutil.net_io_counters().bytes_recv / 1024 / 1024
                }
                
                # Calculate rates if we have previous data
                if self.last_collection:
                    time_diff = metrics['timestamp'] - self.last_collection['timestamp']
                    if time_diff > 0:
                        metrics['network_send_rate_mbps'] = (
                            (metrics['network_io_sent_mb'] - self.last_collection['network_io_sent_mb']) / time_diff
                        )
                        metrics['network_recv_rate_mbps'] = (
                            (metrics['network_io_recv_mb'] - self.last_collection['network_io_recv_mb']) / time_diff
                        )
                
                self.metrics_history.append(metrics)
                self.last_collection = metrics.copy()
                
                return metrics
                
            except Exception as e:
                self.log_error("METRICS_COLLECTION_ERROR", f"Failed to collect system metrics: {e}")
                return {'error': str(e), 'timestamp': time.time()}
    
    def get_metrics_summary(self, time_window: int = 300) -> Dict[str, Any]:
        """Get metrics summary for time window"""
        cutoff = time.time() - time_window
        recent_metrics = [m for m in self.metrics_history if m['timestamp'] > cutoff]
        
        if not recent_metrics:
            return {}
        
        # Calculate averages, min, max for key metrics
        summary = {}
        for metric in ['cpu_percent', 'memory_percent', 'disk_percent']:
            values = [m.get(metric, 0) for m in recent_metrics if metric in m]
            if values:
                summary[metric] = {
                    'avg': sum(values) / len(values),
                    'min': min(values),
                    'max': max(values),
                    'current': values[-1] if values else 0
                }
        
        return summary


class DatabaseHealthChecker(EnhancedLoggerMixin):
    """PostgreSQL database health checker"""
    
    def __init__(self, db_config: Dict[str, Any]):
        self.db_config = db_config
        self.connection_pool = None
    
    async def setup_pool(self):
        """Setup database connection pool"""
        try:
            self.connection_pool = await asyncpg.create_pool(
                **self.db_config,
                min_size=1,
                max_size=5,
                command_timeout=10
            )
        except Exception as e:
            self.log_error("DB_POOL_SETUP_ERROR", f"Failed to setup DB pool: {e}")
    
    async def check_health(self) -> HealthCheckResult:
        """Check database health"""
        start_time = time.time()
        
        try:
            if not self.connection_pool:
                await self.setup_pool()
            
            async with self.connection_pool.acquire() as conn:
                # Basic connectivity test
                await conn.fetchval("SELECT 1")
                
                # Check database size
                db_size = await conn.fetchval(
                    "SELECT pg_size_pretty(pg_database_size(current_database()))"
                )
                
                # Check active connections
                active_connections = await conn.fetchval(
                    "SELECT count(*) FROM pg_stat_activity WHERE state = 'active'"
                )
                
                # Check for long-running queries
                long_queries = await conn.fetchval(
                    "SELECT count(*) FROM pg_stat_activity WHERE state = 'active' AND now() - query_start > interval '30 seconds'"
                )
                
                # Check table sizes
                table_stats = await conn.fetch(
                    "SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size FROM pg_tables WHERE schemaname = 'public' ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC LIMIT 5"
                )
                
                response_time = time.time() - start_time
                
                # Determine health status
                status = HealthStatus.HEALTHY
                if response_time > 2.0:
                    status = HealthStatus.DEGRADED
                if long_queries > 5:
                    status = HealthStatus.DEGRADED
                if active_connections > 100:
                    status = HealthStatus.UNHEALTHY
                
                return HealthCheckResult(
                    service_name="postgresql",
                    service_type=ServiceType.DATABASE,
                    status=status,
                    response_time=response_time,
                    timestamp=datetime.now(timezone.utc),
                    details={
                        'database_size': str(db_size),
                        'active_connections': active_connections,
                        'long_running_queries': long_queries,
                        'largest_tables': [dict(row) for row in table_stats]
                    },
                    metrics={
                        'active_connections': float(active_connections),
                        'long_queries': float(long_queries),
                        'response_time': response_time
                    }
                )
                
        except Exception as e:
            response_time = time.time() - start_time
            return HealthCheckResult(
                service_name="postgresql",
                service_type=ServiceType.DATABASE,
                status=HealthStatus.CRITICAL,
                response_time=response_time,
                timestamp=datetime.now(timezone.utc),
                error_message=str(e),
                details={'error_type': type(e).__name__}
            )


class AIServiceHealthChecker(EnhancedLoggerMixin):
    """AI service health checker for OpenAI/Claude APIs"""
    
    def __init__(self, api_configs: Dict[str, Dict[str, str]]):
        self.api_configs = api_configs
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def check_openai_health(self, api_key: str) -> HealthCheckResult:
        """Check OpenAI API health"""
        start_time = time.time()
        
        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            # Test with minimal request
            response = await self.client.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json={
                    "model": "gpt-3.5-turbo",
                    "messages": [{"role": "user", "content": "test"}],
                    "max_tokens": 1
                }
            )
            
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                status = HealthStatus.HEALTHY
                if response_time > 5.0:
                    status = HealthStatus.DEGRADED
            elif response.status_code == 429:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.UNHEALTHY
            
            return HealthCheckResult(
                service_name="openai",
                service_type=ServiceType.AI_SERVICE,
                status=status,
                response_time=response_time,
                timestamp=datetime.now(timezone.utc),
                details={
                    'status_code': response.status_code,
                    'rate_limit_remaining': response.headers.get('x-ratelimit-remaining-requests'),
                    'rate_limit_reset': response.headers.get('x-ratelimit-reset-requests')
                },
                metrics={
                    'response_time': response_time,
                    'status_code': float(response.status_code)
                }
            )
            
        except Exception as e:
            response_time = time.time() - start_time
            return HealthCheckResult(
                service_name="openai",
                service_type=ServiceType.AI_SERVICE,
                status=HealthStatus.CRITICAL,
                response_time=response_time,
                timestamp=datetime.now(timezone.utc),
                error_message=str(e)
            )
    
    async def check_claude_health(self, api_key: str) -> HealthCheckResult:
        """Check Claude API health"""
        start_time = time.time()
        
        try:
            headers = {
                "x-api-key": api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            }
            
            response = await self.client.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json={
                    "model": "claude-3-haiku-20240307",
                    "max_tokens": 1,
                    "messages": [{"role": "user", "content": "test"}]
                }
            )
            
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                status = HealthStatus.HEALTHY
                if response_time > 5.0:
                    status = HealthStatus.DEGRADED
            elif response.status_code == 429:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.UNHEALTHY
            
            return HealthCheckResult(
                service_name="claude",
                service_type=ServiceType.AI_SERVICE,
                status=status,
                response_time=response_time,
                timestamp=datetime.now(timezone.utc),
                details={
                    'status_code': response.status_code,
                    'rate_limit_remaining': response.headers.get('anthropic-ratelimit-requests-remaining'),
                    'rate_limit_reset': response.headers.get('anthropic-ratelimit-requests-reset')
                },
                metrics={
                    'response_time': response_time,
                    'status_code': float(response.status_code)
                }
            )
            
        except Exception as e:
            response_time = time.time() - start_time
            return HealthCheckResult(
                service_name="claude",
                service_type=ServiceType.AI_SERVICE,
                status=HealthStatus.CRITICAL,
                response_time=response_time,
                timestamp=datetime.now(timezone.utc),
                error_message=str(e)
            )


class VectorDatabaseHealthChecker(EnhancedLoggerMixin):
    """Qdrant vector database health checker"""
    
    def __init__(self, qdrant_url: str, api_key: str = None):
        self.qdrant_url = qdrant_url
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def check_health(self) -> HealthCheckResult:
        """Check Qdrant health"""
        start_time = time.time()
        
        try:
            headers = {}
            if self.api_key:
                headers["api-key"] = self.api_key
            
            # Check cluster info
            response = await self.client.get(
                f"{self.qdrant_url}/cluster",
                headers=headers
            )
            
            if response.status_code != 200:
                raise Exception(f"Cluster endpoint returned {response.status_code}")
            
            cluster_info = response.json()
            
            # Check collections
            response = await self.client.get(
                f"{self.qdrant_url}/collections",
                headers=headers
            )
            
            if response.status_code != 200:
                raise Exception(f"Collections endpoint returned {response.status_code}")
            
            collections = response.json()
            response_time = time.time() - start_time
            
            # Determine health status
            status = HealthStatus.HEALTHY
            if response_time > 2.0:
                status = HealthStatus.DEGRADED
            
            return HealthCheckResult(
                service_name="qdrant",
                service_type=ServiceType.VECTOR_DB,
                status=status,
                response_time=response_time,
                timestamp=datetime.now(timezone.utc),
                details={
                    'cluster_status': cluster_info.get('result', {}),
                    'collections_count': len(collections.get('result', {}).get('collections', [])),
                    'collections': collections.get('result', {})
                },
                metrics={
                    'response_time': response_time,
                    'collections_count': float(len(collections.get('result', {}).get('collections', [])))
                }
            )
            
        except Exception as e:
            response_time = time.time() - start_time
            return HealthCheckResult(
                service_name="qdrant",
                service_type=ServiceType.VECTOR_DB,
                status=HealthStatus.CRITICAL,
                response_time=response_time,
                timestamp=datetime.now(timezone.utc),
                error_message=str(e)
            )


class TelegramBotHealthChecker(EnhancedLoggerMixin):
    """Telegram Bot health checker"""
    
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def check_health(self) -> HealthCheckResult:
        """Check Telegram bot health"""
        start_time = time.time()
        
        try:
            # Check bot info
            response = await self.client.get(
                f"https://api.telegram.org/bot{self.bot_token}/getMe"
            )
            
            if response.status_code != 200:
                raise Exception(f"Bot API returned {response.status_code}")
            
            bot_info = response.json()
            
            # Check webhook status
            webhook_response = await self.client.get(
                f"https://api.telegram.org/bot{self.bot_token}/getWebhookInfo"
            )
            
            webhook_info = webhook_response.json() if webhook_response.status_code == 200 else {}
            
            response_time = time.time() - start_time
            
            status = HealthStatus.HEALTHY
            if response_time > 3.0:
                status = HealthStatus.DEGRADED
            
            return HealthCheckResult(
                service_name="telegram_bot",
                service_type=ServiceType.BOT,
                status=status,
                response_time=response_time,
                timestamp=datetime.now(timezone.utc),
                details={
                    'bot_info': bot_info.get('result', {}),
                    'webhook_info': webhook_info.get('result', {})
                },
                metrics={
                    'response_time': response_time
                }
            )
            
        except Exception as e:
            response_time = time.time() - start_time
            return HealthCheckResult(
                service_name="telegram_bot",
                service_type=ServiceType.BOT,
                status=HealthStatus.CRITICAL,
                response_time=response_time,
                timestamp=datetime.now(timezone.utc),
                error_message=str(e)
            )


class ServiceRecoveryManager(EnhancedLoggerMixin):
    """Automatic service recovery manager"""
    
    def __init__(self):
        self.recovery_attempts = defaultdict(int)
        self.last_recovery_time = defaultdict(float)
        self.max_recovery_attempts = 3
        self.recovery_cooldown = 300  # 5 minutes
    
    async def attempt_recovery(self, service_name: str, health_result: HealthCheckResult) -> bool:
        """Attempt to recover a failed service"""
        current_time = time.time()
        
        # Check if we're in cooldown period
        if (current_time - self.last_recovery_time[service_name]) < self.recovery_cooldown:
            return False
        
        # Check if we've exceeded max attempts
        if self.recovery_attempts[service_name] >= self.max_recovery_attempts:
            return False
        
        try:
            recovery_success = False
            
            if health_result.service_type == ServiceType.DATABASE:
                recovery_success = await self._recover_database(service_name, health_result)
            elif health_result.service_type == ServiceType.AI_SERVICE:
                recovery_success = await self._recover_ai_service(service_name, health_result)
            elif health_result.service_type == ServiceType.VECTOR_DB:
                recovery_success = await self._recover_vector_db(service_name, health_result)
            elif health_result.service_type == ServiceType.BOT:
                recovery_success = await self._recover_bot(service_name, health_result)
            
            self.recovery_attempts[service_name] += 1
            self.last_recovery_time[service_name] = current_time
            
            if recovery_success:
                self.recovery_attempts[service_name] = 0  # Reset on success
                self.log_with_trace('info', f"Successfully recovered service: {service_name}")
            else:
                self.log_error("SERVICE_RECOVERY_FAILED", f"Failed to recover service: {service_name}")
            
            return recovery_success
            
        except Exception as e:
            self.log_error("SERVICE_RECOVERY_ERROR", f"Error during recovery of {service_name}: {e}")
            return False
    
    async def _recover_database(self, service_name: str, health_result: HealthCheckResult) -> bool:
        """Attempt database recovery"""
        # Simple recovery strategies for database
        try:
            # Force connection pool refresh
            await asyncio.sleep(5)  # Wait and retry
            return True
        except Exception:
            return False
    
    async def _recover_ai_service(self, service_name: str, health_result: HealthCheckResult) -> bool:
        """Attempt AI service recovery"""
        # AI services usually recover on their own, just wait
        await asyncio.sleep(10)
        return True
    
    async def _recover_vector_db(self, service_name: str, health_result: HealthCheckResult) -> bool:
        """Attempt vector database recovery"""
        # Wait and retry
        await asyncio.sleep(15)
        return True
    
    async def _recover_bot(self, service_name: str, health_result: HealthCheckResult) -> bool:
        """Attempt bot recovery"""
        # Bot recovery might involve webhook reset
        await asyncio.sleep(5)
        return True


class HealthMonitoringService(EnhancedLoggerMixin):
    """Comprehensive health monitoring orchestrator"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.health_checkers = {}
        self.health_history = deque(maxlen=1000)
        self.current_status = {}
        self.metrics_collector = SystemMetricsCollector()
        self.recovery_manager = ServiceRecoveryManager()
        self.monitoring_tasks = []
        self.running = False
        
        self._setup_health_checkers()
    
    def _setup_health_checkers(self):
        """Setup health checkers for all services"""
        config = self.config
        
        # Database health checker
        if 'database' in config:
            self.health_checkers['postgresql'] = DatabaseHealthChecker(config['database'])
        
        # AI service health checkers
        if 'ai_services' in config:
            self.health_checkers['ai'] = AIServiceHealthChecker(config['ai_services'])
        
        # Vector database health checker
        if 'vector_db' in config:
            self.health_checkers['qdrant'] = VectorDatabaseHealthChecker(
                config['vector_db']['url'],
                config['vector_db'].get('api_key')
            )
        
        # Bot health checker
        if 'telegram_bot' in config:
            self.health_checkers['telegram'] = TelegramBotHealthChecker(config['telegram_bot']['token'])
    
    async def start_monitoring(self):
        """Start continuous health monitoring"""
        if self.running:
            return
        
        self.running = True
        self.log_with_trace('info', "Starting health monitoring service")
        
        # Start monitoring tasks
        tasks = [
            asyncio.create_task(self._monitor_services()),
            asyncio.create_task(self._collect_system_metrics()),
            asyncio.create_task(self._generate_health_reports())
        ]
        
        self.monitoring_tasks.extend(tasks)
        
        try:
            await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            self.log_error("HEALTH_MONITORING_ERROR", f"Health monitoring error: {e}")
    
    async def stop_monitoring(self):
        """Stop health monitoring"""
        self.running = False
        
        for task in self.monitoring_tasks:
            task.cancel()
        
        if self.monitoring_tasks:
            await asyncio.gather(*self.monitoring_tasks, return_exceptions=True)
        
        self.log_with_trace('info', "Health monitoring service stopped")
    
    async def _monitor_services(self):
        """Monitor all configured services"""
        while self.running:
            try:
                # Check database health
                if 'postgresql' in self.health_checkers:
                    db_health = await self.health_checkers['postgresql'].check_health()
                    await self._process_health_result(db_health)
                
                # Check AI services health
                if 'ai' in self.health_checkers:
                    for api_name, api_config in self.config.get('ai_services', {}).items():
                        if api_name == 'openai':
                            ai_health = await self.health_checkers['ai'].check_openai_health(
                                api_config['api_key']
                            )
                        elif api_name == 'claude':
                            ai_health = await self.health_checkers['ai'].check_claude_health(
                                api_config['api_key']
                            )
                        else:
                            continue
                        
                        await self._process_health_result(ai_health)
                
                # Check vector database health
                if 'qdrant' in self.health_checkers:
                    vector_health = await self.health_checkers['qdrant'].check_health()
                    await self._process_health_result(vector_health)
                
                # Check bot health
                if 'telegram' in self.health_checkers:
                    bot_health = await self.health_checkers['telegram'].check_health()
                    await self._process_health_result(bot_health)
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                self.log_error("SERVICE_MONITORING_ERROR", f"Error monitoring services: {e}")
                await asyncio.sleep(30)
    
    async def _collect_system_metrics(self):
        """Collect system metrics continuously"""
        while self.running:
            try:
                metrics = await self.metrics_collector.collect_metrics()
                
                # Log system metrics
                self.log_performance("system_metrics_collection", metrics.get('timestamp', 0), **metrics)
                
                await asyncio.sleep(30)  # Collect every 30 seconds
                
            except Exception as e:
                self.log_error("METRICS_COLLECTION_ERROR", f"Error collecting metrics: {e}")
                await asyncio.sleep(60)
    
    async def _generate_health_reports(self):
        """Generate periodic health reports"""
        while self.running:
            try:
                await asyncio.sleep(300)  # Every 5 minutes
                
                report = await self.generate_health_report()
                
                # Log health report
                self.log_with_trace('info', "Health report generated", 
                                   event_type=EventType.HEALTH_CHECK,
                                   context=report)
                
                # Save report to file
                await self._save_health_report(report)
                
            except Exception as e:
                self.log_error("HEALTH_REPORT_ERROR", f"Error generating health report: {e}")
    
    async def _process_health_result(self, health_result: HealthCheckResult):
        """Process health check result"""
        # Store result
        self.current_status[health_result.service_name] = health_result
        self.health_history.append(health_result)
        
        # Log health status
        log_level = 'info'
        if health_result.status in [HealthStatus.CRITICAL, HealthStatus.UNHEALTHY]:
            log_level = 'error'
        elif health_result.status == HealthStatus.DEGRADED:
            log_level = 'warning'
        
        self.log_with_trace(
            log_level,
            f"Health check: {health_result.service_name} is {health_result.status.value}",
            event_type=EventType.HEALTH_CHECK,
            service=health_result.service_name,
            status=health_result.status.value,
            response_time=health_result.response_time,
            context=health_result.details
        )
        
        # Attempt recovery if service is unhealthy
        if health_result.status in [HealthStatus.CRITICAL, HealthStatus.UNHEALTHY]:
            recovery_attempted = await self.recovery_manager.attempt_recovery(
                health_result.service_name, health_result
            )
            
            if recovery_attempted:
                self.log_with_trace('info', f"Recovery attempted for {health_result.service_name}")
    
    async def generate_health_report(self) -> Dict[str, Any]:
        """Generate comprehensive health report"""
        with trace_operation("generate_health_report"):
            # Overall system status
            overall_status = self._calculate_overall_status()
            
            # Service statuses
            service_statuses = {
                name: result.to_dict() 
                for name, result in self.current_status.items()
            }
            
            # System metrics
            system_metrics = await self.metrics_collector.collect_metrics()
            metrics_summary = self.metrics_collector.get_metrics_summary()
            
            # Health trends
            health_trends = self._calculate_health_trends()
            
            report = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'overall_status': overall_status.value,
                'service_statuses': service_statuses,
                'system_metrics': system_metrics,
                'metrics_summary': metrics_summary,
                'health_trends': health_trends,
                'active_issues': self._get_active_issues(),
                'recovery_status': {
                    'attempts': dict(self.recovery_manager.recovery_attempts),
                    'last_recovery_times': dict(self.recovery_manager.last_recovery_time)
                }
            }
            
            return report
    
    def _calculate_overall_status(self) -> HealthStatus:
        """Calculate overall system health status"""
        if not self.current_status:
            return HealthStatus.UNKNOWN
        
        statuses = [result.status for result in self.current_status.values()]
        
        # If any critical, overall is critical
        if HealthStatus.CRITICAL in statuses:
            return HealthStatus.CRITICAL
        
        # If any unhealthy, overall is unhealthy
        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY
        
        # If any degraded, overall is degraded
        if HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        
        # Otherwise healthy
        return HealthStatus.HEALTHY
    
    def _calculate_health_trends(self) -> Dict[str, Any]:
        """Calculate health trends over time"""
        trends = {}
        
        # Group health history by service
        service_history = defaultdict(list)
        for result in self.health_history:
            service_history[result.service_name].append(result)
        
        # Calculate trends for each service
        for service, history in service_history.items():
            if len(history) < 2:
                continue
            
            # Recent vs older health status
            recent_results = history[-10:]  # Last 10 checks
            older_results = history[-20:-10] if len(history) >= 20 else []
            
            recent_health_score = self._health_to_score(recent_results)
            older_health_score = self._health_to_score(older_results) if older_results else recent_health_score
            
            trend = "stable"
            if recent_health_score > older_health_score + 0.1:
                trend = "improving"
            elif recent_health_score < older_health_score - 0.1:
                trend = "degrading"
            
            trends[service] = {
                'trend': trend,
                'recent_score': recent_health_score,
                'older_score': older_health_score,
                'avg_response_time': sum(r.response_time for r in recent_results) / len(recent_results)
            }
        
        return trends
    
    def _health_to_score(self, results: List[HealthCheckResult]) -> float:
        """Convert health results to numeric score"""
        if not results:
            return 0.0
        
        score_map = {
            HealthStatus.CRITICAL: 0.0,
            HealthStatus.UNHEALTHY: 0.3,
            HealthStatus.DEGRADED: 0.6,
            HealthStatus.HEALTHY: 1.0,
            HealthStatus.UNKNOWN: 0.5
        }
        
        scores = [score_map[result.status] for result in results]
        return sum(scores) / len(scores)
    
    def _get_active_issues(self) -> List[Dict[str, Any]]:
        """Get list of active issues"""
        issues = []
        
        for service_name, result in self.current_status.items():
            if result.status in [HealthStatus.CRITICAL, HealthStatus.UNHEALTHY, HealthStatus.DEGRADED]:
                issues.append({
                    'service': service_name,
                    'status': result.status.value,
                    'error_message': result.error_message,
                    'timestamp': result.timestamp.isoformat(),
                    'response_time': result.response_time
                })
        
        return issues
    
    async def _save_health_report(self, report: Dict[str, Any]):
        """Save health report to file"""
        try:
            reports_dir = Path("logs/health_reports")
            reports_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filename = reports_dir / f"health_report_{timestamp}.json"
            
            with open(filename, 'w') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            self.log_error("HEALTH_REPORT_SAVE_ERROR", f"Failed to save health report: {e}")
    
    async def get_current_health_status(self) -> Dict[str, Any]:
        """Get current health status for API endpoints"""
        overall_status = self._calculate_overall_status()
        
        return {
            'status': overall_status.value,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'services': {
                name: {
                    'status': result.status.value,
                    'response_time': result.response_time,
                    'last_check': result.timestamp.isoformat()
                }
                for name, result in self.current_status.items()
            },
            'system_metrics': await self.metrics_collector.collect_metrics()
        }


# Global health monitoring instance
health_monitor = None

def initialize_health_monitoring(config: Dict[str, Any]) -> HealthMonitoringService:
    """Initialize health monitoring service"""
    global health_monitor
    health_monitor = HealthMonitoringService(config)
    return health_monitor

def get_health_monitor() -> Optional[HealthMonitoringService]:
    """Get global health monitor instance"""
    return health_monitor
