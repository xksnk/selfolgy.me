"""
Monitoring APIs for external integrations and third-party monitoring tools.
Provides REST and GraphQL APIs for accessing Selfology monitoring data.
"""

import asyncio
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
import logging
from dataclasses import dataclass
import hashlib
import hmac

from fastapi import FastAPI, HTTPException, Depends, Header, Query, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware

from .enhanced_logging import EnhancedLoggerMixin, get_monitoring_stats, tracer, error_tracker, profiler
from .health_monitoring import get_health_monitor
from .monitoring_dashboard import get_dashboard


security = HTTPBearer()


class MonitoringAPIConfig(BaseModel):
    """Configuration for monitoring API"""
    api_keys: List[str] = Field(default_factory=list)
    webhook_secret: Optional[str] = None
    rate_limit_per_minute: int = 100
    enable_webhooks: bool = True
    enable_graphql: bool = True
    cors_origins: List[str] = Field(default_factory=lambda: ["*"])


class MetricsRequest(BaseModel):
    """Request model for metrics query"""
    time_range: str = Field(default="1h", description="Time range: 1h, 24h, 7d, 30d")
    services: Optional[List[str]] = Field(default=None, description="Specific services to query")
    metrics: Optional[List[str]] = Field(default=None, description="Specific metrics to return")
    aggregation: str = Field(default="avg", description="Aggregation method: avg, sum, min, max")


class AlertRule(BaseModel):
    """Alert rule configuration"""
    name: str
    condition: str
    threshold: float
    severity: str = Field(default="medium", description="Alert severity: low, medium, high, critical")
    enabled: bool = True
    notification_channels: List[str] = Field(default_factory=list)


class WebhookConfig(BaseModel):
    """Webhook configuration"""
    url: str
    events: List[str] = Field(default_factory=list)
    headers: Dict[str, str] = Field(default_factory=dict)
    secret: Optional[str] = None
    enabled: bool = True


class MonitoringAPIService(EnhancedLoggerMixin):
    """Core monitoring API service"""
    
    def __init__(self, config: MonitoringAPIConfig):
        self.config = config
        self.api_keys = set(config.api_keys)
        self.rate_limiter = {}
        self.webhooks = []
        self.custom_alert_rules = []
        
    def validate_api_key(self, credentials: HTTPAuthorizationCredentials) -> bool:
        """Validate API key"""
        return credentials.credentials in self.api_keys
    
    def check_rate_limit(self, api_key: str) -> bool:
        """Check rate limit for API key"""
        current_time = time.time()
        window_start = current_time - 60  # 1 minute window
        
        if api_key not in self.rate_limiter:
            self.rate_limiter[api_key] = []
        
        # Remove old requests outside the window
        self.rate_limiter[api_key] = [
            req_time for req_time in self.rate_limiter[api_key] 
            if req_time > window_start
        ]
        
        # Check if under limit
        if len(self.rate_limiter[api_key]) >= self.config.rate_limit_per_minute:
            return False
        
        # Add current request
        self.rate_limiter[api_key].append(current_time)
        return True
    
    async def get_system_metrics(self, request: MetricsRequest) -> Dict[str, Any]:
        """Get system metrics based on request parameters"""
        time_range_hours = self._parse_time_range(request.time_range)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=time_range_hours)
        
        # Get health monitor data
        health_monitor = get_health_monitor()
        health_data = {}
        if health_monitor:
            health_data = await health_monitor.get_current_health_status()
        
        # Get dashboard data
        dashboard = get_dashboard()
        dashboard_data = {}
        if dashboard:
            dashboard_metrics = await dashboard.data_provider.get_dashboard_data()
            dashboard_data = dashboard_metrics.to_dict()
        
        # Get monitoring stats
        monitoring_stats = get_monitoring_stats()
        
        # Filter by requested services
        if request.services:
            health_data['services'] = {
                name: data for name, data in health_data.get('services', {}).items()
                if name in request.services
            }
        
        # Prepare response
        response = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'time_range': request.time_range,
            'system_health': health_data,
            'performance_metrics': monitoring_stats.get('performance', {}),
            'error_metrics': monitoring_stats.get('errors', {}),
            'user_metrics': dashboard_data.get('user_analytics', {}),
            'ai_metrics': dashboard_data.get('ai_usage', {})
        }
        
        # Filter by requested metrics
        if request.metrics:
            filtered_response = {'timestamp': response['timestamp'], 'time_range': response['time_range']}
            for metric_key in request.metrics:
                if metric_key in response:
                    filtered_response[metric_key] = response[metric_key]
            response = filtered_response
        
        return response
    
    def _parse_time_range(self, time_range: str) -> int:
        """Parse time range string to hours"""
        if time_range == '1h':
            return 1
        elif time_range == '24h':
            return 24
        elif time_range == '7d':
            return 168
        elif time_range == '30d':
            return 720
        else:
            return 1  # Default to 1 hour
    
    async def get_service_health(self, service_name: Optional[str] = None) -> Dict[str, Any]:
        """Get health status for all services or specific service"""
        health_monitor = get_health_monitor()
        if not health_monitor:
            return {'error': 'Health monitor not available'}
        
        health_data = await health_monitor.get_current_health_status()
        
        if service_name:
            if service_name in health_data.get('services', {}):
                return {
                    'service': service_name,
                    'status': health_data['services'][service_name],
                    'timestamp': health_data['timestamp']
                }
            else:
                raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")
        
        return health_data
    
    async def get_alerts(self, severity: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get active alerts"""
        dashboard = get_dashboard()
        if not dashboard:
            return []
        
        alerts = dashboard.data_provider.alerts_manager.get_active_alerts()
        
        # Filter by severity if specified
        if severity:
            alerts = [alert for alert in alerts if alert['severity'] == severity]
        
        # Limit results
        return alerts[:limit]
    
    async def create_alert_rule(self, rule: AlertRule) -> Dict[str, Any]:
        """Create custom alert rule"""
        # Add to custom alert rules
        rule_dict = rule.dict()
        rule_dict['id'] = hashlib.md5(rule.name.encode()).hexdigest()
        rule_dict['created_at'] = datetime.now(timezone.utc).isoformat()
        
        self.custom_alert_rules.append(rule_dict)
        
        self.log_with_trace('info', f"Created alert rule: {rule.name}", rule_id=rule_dict['id'])
        
        return rule_dict
    
    async def get_performance_data(self, operation: Optional[str] = None) -> Dict[str, Any]:
        """Get performance data for operations"""
        if operation:
            return profiler.get_performance_stats(operation)
        else:
            return profiler.get_performance_stats()
    
    async def get_error_analytics(self, time_window: int = 3600) -> Dict[str, Any]:
        """Get error analytics"""
        return error_tracker.get_error_stats(time_window)
    
    def add_webhook(self, webhook_config: WebhookConfig) -> str:
        """Add webhook configuration"""
        webhook_id = hashlib.md5(f"{webhook_config.url}_{time.time()}".encode()).hexdigest()
        webhook_dict = webhook_config.dict()
        webhook_dict['id'] = webhook_id
        webhook_dict['created_at'] = datetime.now(timezone.utc).isoformat()
        
        self.webhooks.append(webhook_dict)
        
        self.log_with_trace('info', f"Added webhook: {webhook_config.url}", webhook_id=webhook_id)
        
        return webhook_id
    
    async def trigger_webhook(self, event_type: str, data: Dict[str, Any]):
        """Trigger webhooks for specific event type"""
        if not self.config.enable_webhooks:
            return
        
        relevant_webhooks = [
            webhook for webhook in self.webhooks
            if webhook['enabled'] and (not webhook['events'] or event_type in webhook['events'])
        ]
        
        for webhook in relevant_webhooks:
            try:
                await self._send_webhook(webhook, event_type, data)
            except Exception as e:
                self.log_error("WEBHOOK_ERROR", f"Failed to send webhook to {webhook['url']}: {e}")
    
    async def _send_webhook(self, webhook: Dict[str, Any], event_type: str, data: Dict[str, Any]):
        """Send webhook notification"""
        import httpx
        
        payload = {
            'event_type': event_type,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'data': data
        }
        
        headers = webhook.get('headers', {})
        headers['Content-Type'] = 'application/json'
        
        # Add signature if secret is provided
        if webhook.get('secret'):
            signature = hmac.new(
                webhook['secret'].encode(),
                json.dumps(payload).encode(),
                hashlib.sha256
            ).hexdigest()
            headers['X-Selfology-Signature'] = f"sha256={signature}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                webhook['url'],
                json=payload,
                headers=headers
            )
            response.raise_for_status()


class MonitoringAPI(EnhancedLoggerMixin):
    """FastAPI application for monitoring APIs"""
    
    def __init__(self, config: MonitoringAPIConfig, host: str = "localhost", port: int = 8001):
        self.config = config
        self.host = host
        self.port = port
        self.app = FastAPI(
            title="Selfology Monitoring API",
            description="Enterprise monitoring APIs for Selfology AI Psychology Coach",
            version="1.0.0"
        )
        self.service = MonitoringAPIService(config)
        
        self._setup_middleware()
        self._setup_routes()
    
    def _setup_middleware(self):
        """Setup FastAPI middleware"""
        # CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=self.config.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # GZip middleware
        self.app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    def _setup_routes(self):
        """Setup API routes"""
        
        async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
            """Validate API key and check rate limits"""
            if not self.service.validate_api_key(credentials):
                raise HTTPException(status_code=401, detail="Invalid API key")
            
            if not self.service.check_rate_limit(credentials.credentials):
                raise HTTPException(status_code=429, detail="Rate limit exceeded")
            
            return credentials.credentials
        
        @self.app.get("/")
        async def root():
            """API root endpoint"""
            return {
                "service": "Selfology Monitoring API",
                "version": "1.0.0",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        @self.app.get("/health")
        async def health_check():
            """API health check"""
            return {
                "status": "healthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "uptime": time.time() - self.service.rate_limiter.get('_start_time', time.time())
            }
        
        @self.app.post("/v1/metrics")
        async def get_metrics(
            request: MetricsRequest,
            api_key: str = Depends(get_current_user)
        ):
            """Get system metrics"""
            try:
                metrics = await self.service.get_system_metrics(request)
                return JSONResponse(content=metrics)
            except Exception as e:
                self.log_error("METRICS_API_ERROR", f"Error getting metrics: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/v1/health/{service_name}")
        async def get_service_health(
            service_name: str,
            api_key: str = Depends(get_current_user)
        ):
            """Get health status for specific service"""
            try:
                health = await self.service.get_service_health(service_name)
                return JSONResponse(content=health)
            except HTTPException:
                raise
            except Exception as e:
                self.log_error("HEALTH_API_ERROR", f"Error getting health for {service_name}: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/v1/health")
        async def get_all_health(
            api_key: str = Depends(get_current_user)
        ):
            """Get health status for all services"""
            try:
                health = await self.service.get_service_health()
                return JSONResponse(content=health)
            except Exception as e:
                self.log_error("HEALTH_API_ERROR", f"Error getting health status: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/v1/alerts")
        async def get_alerts(
            severity: Optional[str] = Query(None, description="Filter by severity"),
            limit: int = Query(100, description="Maximum number of alerts"),
            api_key: str = Depends(get_current_user)
        ):
            """Get active alerts"""
            try:
                alerts = await self.service.get_alerts(severity, limit)
                return JSONResponse(content={"alerts": alerts})
            except Exception as e:
                self.log_error("ALERTS_API_ERROR", f"Error getting alerts: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/v1/alerts/rules")
        async def create_alert_rule(
            rule: AlertRule,
            api_key: str = Depends(get_current_user)
        ):
            """Create custom alert rule"""
            try:
                created_rule = await self.service.create_alert_rule(rule)
                return JSONResponse(content=created_rule, status_code=201)
            except Exception as e:
                self.log_error("ALERT_RULE_CREATE_ERROR", f"Error creating alert rule: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/v1/performance")
        async def get_performance(
            operation: Optional[str] = Query(None, description="Specific operation"),
            api_key: str = Depends(get_current_user)
        ):
            """Get performance metrics"""
            try:
                performance = await self.service.get_performance_data(operation)
                return JSONResponse(content=performance)
            except Exception as e:
                self.log_error("PERFORMANCE_API_ERROR", f"Error getting performance data: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/v1/errors")
        async def get_errors(
            time_window: int = Query(3600, description="Time window in seconds"),
            api_key: str = Depends(get_current_user)
        ):
            """Get error analytics"""
            try:
                errors = await self.service.get_error_analytics(time_window)
                return JSONResponse(content=errors)
            except Exception as e:
                self.log_error("ERRORS_API_ERROR", f"Error getting error analytics: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/v1/webhooks")
        async def add_webhook(
            webhook: WebhookConfig,
            api_key: str = Depends(get_current_user)
        ):
            """Add webhook configuration"""
            try:
                webhook_id = self.service.add_webhook(webhook)
                return JSONResponse(content={"webhook_id": webhook_id}, status_code=201)
            except Exception as e:
                self.log_error("WEBHOOK_ADD_ERROR", f"Error adding webhook: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/v1/webhooks")
        async def get_webhooks(
            api_key: str = Depends(get_current_user)
        ):
            """Get webhook configurations"""
            return JSONResponse(content={"webhooks": self.service.webhooks})
        
        # Prometheus metrics endpoint
        @self.app.get("/metrics")
        async def prometheus_metrics():
            """Prometheus-compatible metrics endpoint"""
            try:
                metrics = await self._generate_prometheus_metrics()
                return Response(content=metrics, media_type="text/plain")
            except Exception as e:
                self.log_error("PROMETHEUS_METRICS_ERROR", f"Error generating Prometheus metrics: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # GraphQL endpoint (if enabled)
        if self.config.enable_graphql:
            self._setup_graphql()
    
    def _setup_graphql(self):
        """Setup GraphQL endpoint"""
        # This would implement GraphQL schema and resolvers
        # For now, just a placeholder
        
        @self.app.post("/graphql")
        async def graphql_endpoint(
            query: Dict[str, Any],
            api_key: str = Depends(lambda credentials: self.service.validate_api_key(credentials))
        ):
            """GraphQL endpoint"""
            return JSONResponse(content={"message": "GraphQL endpoint - implementation pending"})
    
    async def _generate_prometheus_metrics(self) -> str:
        """Generate Prometheus-compatible metrics"""
        from .health_monitoring import get_health_monitor
        
        lines = []
        
        # System health metrics
        health_monitor = get_health_monitor()
        if health_monitor:
            health_data = await health_monitor.get_current_health_status()
            
            # Overall system status
            status_value = 1 if health_data.get('status') == 'healthy' else 0
            lines.append(f'selfology_system_healthy {status_value}')
            
            # Service health metrics
            for service_name, service_data in health_data.get('services', {}).items():
                service_healthy = 1 if service_data.get('status') == 'healthy' else 0
                lines.append(f'selfology_service_healthy{{service="{service_name}"}} {service_healthy}')
                
                response_time = service_data.get('response_time', 0)
                lines.append(f'selfology_service_response_time{{service="{service_name}"}} {response_time}')
        
        # Error metrics
        error_stats = error_tracker.get_error_stats()
        lines.append(f'selfology_errors_total {error_stats.get("total_errors", 0)}')
        lines.append(f'selfology_error_rate {error_stats.get("error_rate", 0)}')
        
        # Performance metrics
        perf_stats = profiler.get_performance_stats()
        for operation, stats in perf_stats.items():
            avg_duration = stats.get('avg_duration', 0)
            count = stats.get('count', 0)
            lines.append(f'selfology_operation_duration{{operation="{operation}"}} {avg_duration}')
            lines.append(f'selfology_operation_count{{operation="{operation}"}} {count}')
        
        return '\n'.join(lines) + '\n'
    
    async def start_api(self):
        """Start the monitoring API server"""
        self.log_with_trace('info', f"Starting monitoring API on {self.host}:{self.port}")
        
        # Initialize rate limiter start time
        self.service.rate_limiter['_start_time'] = time.time()
        
        config = uvicorn.Config(
            app=self.app,
            host=self.host,
            port=self.port,
            log_level="info",
            reload=False
        )
        
        server = uvicorn.Server(config)
        await server.serve()


class MonitoringIntegration(EnhancedLoggerMixin):
    """Integration layer for external monitoring tools"""
    
    def __init__(self, api_service: MonitoringAPIService):
        self.api_service = api_service
        self.integrations = {}
    
    def register_integration(self, name: str, integration_config: Dict[str, Any]):
        """Register external monitoring tool integration"""
        self.integrations[name] = integration_config
        self.log_with_trace('info', f"Registered monitoring integration: {name}")
    
    async def send_to_datadog(self, metrics: Dict[str, Any]):
        """Send metrics to Datadog"""
        if 'datadog' not in self.integrations:
            return
        
        # Implementation for Datadog integration
        # This would use the Datadog API client
        pass
    
    async def send_to_grafana(self, metrics: Dict[str, Any]):
        """Send metrics to Grafana/InfluxDB"""
        if 'grafana' not in self.integrations:
            return
        
        # Implementation for Grafana integration
        # This would use InfluxDB line protocol
        pass
    
    async def send_to_newrelic(self, metrics: Dict[str, Any]):
        """Send metrics to New Relic"""
        if 'newrelic' not in self.integrations:
            return
        
        # Implementation for New Relic integration
        pass
    
    async def send_to_elasticsearch(self, logs: List[Dict[str, Any]]):
        """Send logs to Elasticsearch"""
        if 'elasticsearch' not in self.integrations:
            return
        
        # Implementation for Elasticsearch integration
        pass


# Global API instance
monitoring_api = None

def initialize_monitoring_api(
    config: MonitoringAPIConfig, 
    host: str = "localhost", 
    port: int = 8001
) -> MonitoringAPI:
    """Initialize monitoring API"""
    global monitoring_api
    monitoring_api = MonitoringAPI(config, host, port)
    return monitoring_api

def get_monitoring_api() -> Optional[MonitoringAPI]:
    """Get global monitoring API instance"""
    return monitoring_api

def create_default_config(api_keys: List[str]) -> MonitoringAPIConfig:
    """Create default monitoring API configuration"""
    return MonitoringAPIConfig(
        api_keys=api_keys,
        rate_limit_per_minute=100,
        enable_webhooks=True,
        enable_graphql=True,
        cors_origins=["*"]
    )
