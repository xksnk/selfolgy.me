# Selfology Comprehensive Monitoring System

## Overview

The Selfology AI Psychology Coach platform features an enterprise-grade monitoring, logging, and error tracking system designed to provide complete observability across all services. This comprehensive system ensures reliable operation, proactive issue detection, and optimal user experience.

## System Architecture

```
┌───────────────────────────────────────────────┐
│              SELFOLOGY MONITORING SYSTEM                │
├───────────────────────────────────────────────┤
│                                                      │
│  ┌──────────────────────────────────────────┐  │
│  │        MONITORING ORCHESTRATOR          │  │
│  │      (Central Coordination)            │  │
│  └──────────────────────────────────────────┘  │
│                    │                            │
│  ┌─────────────────┐ ┌──────────────────────────┐  │
│  │ Enhanced Logging │ │   Health Monitoring   │  │
│  │ & Tracing       │ │   & Auto Recovery    │  │
│  └─────────────────┘ └──────────────────────────┘  │
│                    │                            │
│  ┌─────────────────┐ ┌──────────────────────────┐  │
│  │ Real-time       │ │   Log Aggregation   │  │
│  │ Dashboard       │ │   & Analysis        │  │
│  └─────────────────┘ └──────────────────────────┘  │
│                    │                            │
│  ┌──────────────────────────────────────────┐  │
│  │        Monitoring APIs              │  │
│  │    (REST, GraphQL, Prometheus)     │  │
│  └──────────────────────────────────────────┘  │
│                                                      │
└───────────────────────────────────────────────┘
                               │
                    Data Flow & Integration
                               │
┌───────────────────────────────────────────────┐
│              SELFOLOGY SERVICES                   │
├───────────────────────────────────────────────┤
│ • Telegram Bot        • Assessment Engine    │
│ • Chat Coach          • Statistics Service   │
│ • User Profile Svc    • Vector Service       │
│ • PostgreSQL DB       • Qdrant Vector DB     │
│ • OpenAI/Claude APIs  • Question Core        │
└───────────────────────────────────────────────┘
```

## Core Components

### 1. Enhanced Logging System (`core/enhanced_logging.py`)

**Features:**
- 🔍 **Distributed Tracing**: Complete request tracking with trace and span IDs
- 🏷️ **Correlation IDs**: Link related events across services
- 📊 **Structured Logging**: JSON-formatted logs with rich metadata
- ⚡ **Performance Profiling**: Automatic operation timing and bottleneck detection
- 🚨 **Smart Error Tracking**: Pattern detection and error correlation
- 📋 **Multiple Log Levels**: Enhanced levels including SECURITY and AUDIT

**Key Classes:**
- `EnhancedFormatter`: JSON formatter with trace context
- `DistributedTracer`: Manages spans and traces
- `ErrorTracker`: Pattern detection and error analytics
- `PerformanceProfiler`: Operation timing and bottleneck identification
- `AlertManager`: Smart alerting with escalation policies

### 2. Health Monitoring System (`core/health_monitoring.py`)

**Features:**
- 🌡️ **Service Health Checks**: Comprehensive health monitoring for all services
- 🔄 **Automatic Recovery**: Self-healing capabilities for failed services
- 📈 **System Metrics**: CPU, memory, disk, and network monitoring
- 📋 **Dependency Tracking**: Service dependency mapping and health cascading
- ⏰ **Configurable Intervals**: Customizable check frequencies

**Monitored Services:**
- PostgreSQL database connectivity and performance
- AI APIs (OpenAI, Claude) availability and response times
- Qdrant vector database health and collections status
- Telegram Bot API connectivity
- System resources and performance metrics

### 3. Real-time Monitoring Dashboard (`core/monitoring_dashboard.py`)

**Features:**
- 🗺️ **Interactive Web Dashboard**: Real-time system visualization
- 📊 **Live Metrics**: WebSocket-based real-time updates
- 📝 **User Analytics**: Engagement, satisfaction, and usage patterns
- 💰 **Cost Tracking**: AI usage costs and optimization insights
- ⚠️ **Alert Management**: Visual alerts with acknowledgment
- 📈 **Historical Data**: Time-series charts and trend analysis

**Dashboard Sections:**
- System health overview with service status
- Performance metrics and response times
- User activity and engagement analytics
- Error rates and top error patterns
- AI usage and cost analysis
- Active alerts and notifications

### 4. Monitoring APIs (`core/monitoring_api.py`)

**Features:**
- 🚀 **RESTful APIs**: Comprehensive REST endpoints for all monitoring data
- 🔐 **API Key Authentication**: Secure access with rate limiting
- 📁 **Prometheus Integration**: Metrics endpoint for Prometheus scraping
- 🔗 **Webhook Support**: Real-time notifications to external systems
- 📋 **Custom Alert Rules**: Programmable alerting with external integrations
- 🌐 **CORS Support**: Web application integration

**API Endpoints:**
- `GET /v1/metrics` - System metrics with filtering
- `GET /v1/health` - Service health status
- `GET /v1/alerts` - Active alerts and history
- `POST /v1/alerts/rules` - Create custom alert rules
- `GET /v1/performance` - Performance analytics
- `GET /v1/errors` - Error analytics and patterns
- `GET /metrics` - Prometheus-compatible metrics

### 5. Centralized Log Aggregation (`core/log_aggregation.py`)

**Features:**
- 🗺️ **Log Collection**: Multi-source log aggregation
- 🔍 **Pattern Detection**: Anomaly and security event detection
- 🖾 **SQLite Storage**: Efficient local storage with indexing
- 📊 **Log Analysis**: Statistical analysis and trend identification
- 🔄 **Real-time Processing**: Stream processing with queues
- 🧹 **Automatic Cleanup**: Retention policies and cleanup

**Capabilities:**
- Parse JSON and standard log formats
- Real-time log tailing and processing
- Error pattern detection and alerting
- Log aggregation by time periods
- Full-text search and filtering
- Historical log analysis and reporting

### 6. Monitoring Orchestrator (`core/monitoring_orchestrator.py`)

**Features:**
- 🎡 **Central Coordination**: Single entry point for all monitoring
- ⚙️ **Configuration Management**: Unified configuration system
- 🚀 **Service Lifecycle**: Start/stop all monitoring components
- 📊 **Status Reporting**: Comprehensive system status
- 🔗 **Component Integration**: Seamless inter-component communication

## Installation & Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Environment Configuration

Create a `.env` file with the following variables:

```env
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_USER=n8n
DB_PASSWORD=your_password
DB_NAME=n8n

# AI Services
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_claude_key

# Vector Database
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your_qdrant_key

# Telegram Bot
BOT_TOKEN=your_telegram_bot_token

# Monitoring API
MONITORING_API_KEY=your_secure_api_key
```

### 3. Initialize Monitoring System

```python
from core.monitoring_orchestrator import (
    initialize_monitoring_system,
    start_monitoring_system,
    MonitoringConfig
)

# Create configuration
config = MonitoringConfig(
    service_name="selfology",
    environment="production",
    dashboard_port=8000,
    api_port=8001
)

# Initialize and start
orchestrator = initialize_monitoring_system(config)
await start_monitoring_system()
```

### 4. Integration with Bot

```python
from core.enhanced_logging import EnhancedLoggerMixin, trace_operation
from core.monitoring_dashboard import track_user_activity, track_performance

class SelfologyBot(EnhancedLoggerMixin):
    async def handle_user_message(self, user_id: int, message: str):
        with trace_operation("handle_user_message", user_id=user_id):
            # Track user activity
            track_user_activity(user_id, "message_sent", {"message_length": len(message)})
            
            # Process message
            response = await self.process_message(message)
            
            # Log performance
            self.log_performance("message_processing", response.processing_time)
            
            return response
```

## Usage Examples

### Monitoring Dashboard Access

```bash
# Access the real-time dashboard
http://localhost:8000

# Dashboard features:
# - System health overview
# - Real-time metrics
# - User analytics
# - Error tracking
# - AI cost analysis
```

### API Usage

```bash
# Get system health
curl -H "Authorization: Bearer your_api_key" \
     http://localhost:8001/v1/health

# Get performance metrics
curl -H "Authorization: Bearer your_api_key" \
     http://localhost:8001/v1/performance

# Get error analytics
curl -H "Authorization: Bearer your_api_key" \
     http://localhost:8001/v1/errors?time_window=3600

# Prometheus metrics
curl http://localhost:8001/metrics
```

### Log Analysis

```python
from core.log_aggregation import get_logging_service

logging_service = get_logging_service()

# Get log analysis for last 24 hours
analysis = await logging_service.get_log_analysis(hours=24)
print(f"Total errors: {analysis['error_analysis']['total_errors']}")
print(f"Unique users: {analysis['user_activity']['unique_users']}")

# Get aggregated logs
aggregations = await logging_service.get_aggregated_logs(
    hours=24, 
    period=AggregationPeriod.HOUR
)
```

### Custom Alerts

```python
from core.monitoring_api import AlertRule

# Create custom alert rule
alert_rule = AlertRule(
    name="high_user_errors",
    condition="user_error_rate > 5",
    threshold=5.0,
    severity="high",
    notification_channels=["webhook", "email"]
)

# Add via API
response = requests.post(
    "http://localhost:8001/v1/alerts/rules",
    headers={"Authorization": "Bearer your_api_key"},
    json=alert_rule.dict()
)
```

## Monitoring Metrics

### System Health Metrics
- ✅ Service availability and response times
- 📋 Database connection pool health
- 🚀 AI API response times and error rates
- 📏 Vector database performance
- 💻 System resources (CPU, memory, disk)

### User Experience Metrics
- 👥 Active users and engagement rates
- ⏱️ Response times from user perspective
- 📝 Conversation completion rates
- 🎯 User satisfaction scores
- 📊 Session duration and frequency

### Business Intelligence
- 💰 AI usage costs per model and user
- 📈 User growth and retention rates
- 🎯 Assessment completion rates
- 📝 Question effectiveness metrics
- 🔄 User journey optimization data

### Technical Performance
- ⚡ Operation response times and throughput
- 🚨 Error rates and patterns
- 🗺️ Distributed trace analysis
- 📋 Database query performance
- 🎥 Memory and resource utilization

## Alert Configuration

### Default Alert Rules

1. **High Error Rate**: > 10 errors/minute
2. **Slow Response Time**: > 5 seconds average
3. **Service Down**: Any critical service unavailable
4. **Memory Usage**: > 90% memory utilization
5. **Database Issues**: Connection failures or slow queries
6. **AI API Issues**: Rate limits or API failures
7. **User Satisfaction**: < 3.0/5.0 average rating
8. **High Costs**: AI usage exceeding budget thresholds

### Alert Channels
- 📱 Dashboard notifications
- 📧 Email alerts (configured via SMTP)
- 🔔 Webhook notifications to external systems
- 📲 Slack/Discord integration (via webhooks)
- 📊 Monitoring platform integration (DataDog, New Relic)

## Security & Privacy

### Data Protection
- 🔐 **API Key Authentication**: Secure access control
- 🔒 **Data Encryption**: Logs and metrics encrypted at rest
- 🌐 **Network Security**: HTTPS enforcement and CORS policies
- 📄 **Audit Logging**: Complete audit trail of monitoring actions
- 🚫 **Data Anonymization**: User data anonymized in logs

### Privacy Compliance
- 🎩 **GDPR Compliance**: User data handling and retention policies
- 🗺️ **Data Locality**: Configurable data storage locations
- 📋 **Retention Policies**: Automatic cleanup of old monitoring data
- 👥 **User Consent**: Monitoring with user privacy protection

## Troubleshooting

### Common Issues

#### Dashboard Not Loading
```bash
# Check if dashboard service is running
curl http://localhost:8000/health

# Check logs
tail -f logs/application/selfology.log

# Restart dashboard
python -c "from core.monitoring_orchestrator import *; asyncio.run(start_monitoring_system())"
```

#### API Authentication Errors
```bash
# Verify API key
curl -H "Authorization: Bearer wrong_key" http://localhost:8001/v1/health

# Check API logs
grep "API_AUTH" logs/application/selfology.log
```

#### Missing Metrics
```bash
# Check health monitoring
curl http://localhost:8001/v1/health

# Verify service configurations
python -c "from core.monitoring_orchestrator import get_monitoring_orchestrator; print(get_monitoring_orchestrator().get_system_status())"
```

### Log Analysis

```bash
# View recent errors
grep "ERROR\|CRITICAL" logs/errors/errors.log | tail -20

# Analyze performance issues
grep "slow_operations" logs/performance/performance.log

# Check security events
grep "SECURITY_EVENT" logs/security/security.log
```

## Performance Optimization

### System Tuning
1. **Database Optimization**: Connection pooling and query optimization
2. **Log Retention**: Adjust retention periods based on storage capacity
3. **Monitoring Intervals**: Balance monitoring frequency with performance
4. **Alert Thresholds**: Tune alert sensitivity to reduce noise
5. **Resource Allocation**: Scale monitoring resources with system load

### Scalability Considerations
- **Horizontal Scaling**: Deploy monitoring across multiple instances
- **Load Balancing**: Distribute monitoring load across services
- **Data Partitioning**: Partition logs and metrics by time periods
- **Caching**: Implement caching for frequently accessed metrics
- **Asynchronous Processing**: Use async processing for heavy operations

## Integration with External Tools

### Prometheus & Grafana
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'selfology'
    static_configs:
      - targets: ['localhost:8001']
    metrics_path: '/metrics'
    scrape_interval: 30s
```

### ELK Stack (Elasticsearch, Logstash, Kibana)
```json
{
  "logstash_config": {
    "input": {
      "file": {
        "path": "/path/to/selfology/logs/**/*.log",
        "codec": "json"
      }
    },
    "output": {
      "elasticsearch": {
        "hosts": ["localhost:9200"]
      }
    }
  }
}
```

### DataDog Integration
```python
from datadog import initialize, api

# Send custom metrics to DataDog
api.Metric.send(
    metric='selfology.user_activity',
    points=[(time.time(), user_count)],
    tags=['service:selfology', 'env:production']
)
```

## Development & Customization

### Adding Custom Metrics

```python
from core.enhanced_logging import EnhancedLoggerMixin
from core.monitoring_dashboard import track_performance

class CustomService(EnhancedLoggerMixin):
    def track_custom_metric(self, metric_name: str, value: float):
        # Log custom metric
        self.log_metric(metric_name, value, service="custom")
        
        # Track in dashboard
        track_performance(f"custom.{metric_name}", value)
```

### Custom Health Checks

```python
from core.health_monitoring import HealthCheckResult, ServiceType

class CustomHealthChecker:
    async def check_health(self) -> HealthCheckResult:
        # Custom health check logic
        healthy = await self.verify_custom_service()
        
        return HealthCheckResult(
            service_name="custom_service",
            service_type=ServiceType.API,
            status=HealthStatus.HEALTHY if healthy else HealthStatus.UNHEALTHY,
            response_time=0.1,
            timestamp=datetime.now(timezone.utc)
        )
```

### Custom Alerts

```python
from core.enhanced_logging import alert_manager

# Add custom alert rule
alert_manager.add_alert_rule(
    'custom_metric_threshold',
    lambda metrics: metrics.get('custom_value', 0) > 100,
    'high',
    'Custom metric exceeded threshold'
)
```

## Maintenance & Operations

### Daily Operations
- ✅ Review dashboard for system health
- 📊 Check error rates and performance metrics
- 🔍 Investigate any active alerts
- 📋 Review log analysis for patterns

### Weekly Operations
- 📊 Analyze user engagement trends
- 💰 Review AI usage costs and optimization
- 🔄 Update alert thresholds based on patterns
- 🧹 Clean up old logs and metrics

### Monthly Operations
- 📈 Generate comprehensive system reports
- 🎯 Review and update monitoring strategies
- 📋 Analyze long-term trends and capacity planning
- 🔄 Update monitoring system components

## Support & Documentation

### Additional Resources
- [API Documentation](api-docs/)
- [Troubleshooting Guide](troubleshooting.md)
- [Performance Tuning](performance.md)
- [Security Best Practices](security.md)

### Getting Help
- Check the logs first: `logs/application/selfology.log`
- Review dashboard alerts and metrics
- Use API endpoints to query specific issues
- Check system health via monitoring APIs

---

**The Selfology Monitoring System provides enterprise-grade observability for the AI Psychology Coach platform, ensuring reliable operation, optimal performance, and exceptional user experience. 🚀📊✨**
