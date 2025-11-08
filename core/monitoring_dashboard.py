"""
Real-time monitoring dashboard with comprehensive metrics visualization.
Provides web-based dashboard for monitoring Selfology system health, performance, and user analytics.
"""

import asyncio
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
import logging
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import statistics

from fastapi import FastAPI, WebSocket, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request
import uvicorn

from .enhanced_logging import EnhancedLoggerMixin, get_monitoring_stats, tracer, error_tracker, profiler
from .health_monitoring import get_health_monitor, HealthStatus


@dataclass
class DashboardMetrics:
    """Dashboard metrics data structure"""
    timestamp: str
    system_health: Dict[str, Any]
    performance_metrics: Dict[str, Any]
    user_analytics: Dict[str, Any]
    error_statistics: Dict[str, Any]
    ai_usage: Dict[str, Any]
    business_metrics: Dict[str, Any]
    alerts: List[Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MetricsAggregator(EnhancedLoggerMixin):
    """Aggregates metrics from various sources for dashboard display"""
    
    def __init__(self):
        self.user_activity_tracker = defaultdict(lambda: defaultdict(int))
        self.conversation_metrics = deque(maxlen=1000)
        self.response_times = deque(maxlen=500)
        self.ai_costs = defaultdict(float)
        self.user_satisfaction_scores = deque(maxlen=100)
        
    def track_user_activity(self, user_id: int, activity_type: str, metadata: Dict[str, Any] = None):
        """Track user activity for analytics"""
        timestamp = datetime.now(timezone.utc)
        hour_key = timestamp.strftime('%Y-%m-%d-%H')
        
        self.user_activity_tracker[hour_key][activity_type] += 1
        
        # Track detailed conversation metrics
        if activity_type in ['message_sent', 'question_answered', 'chat_response']:
            self.conversation_metrics.append({
                'timestamp': timestamp.isoformat(),
                'user_id': user_id,
                'activity_type': activity_type,
                'metadata': metadata or {}
            })
    
    def track_response_time(self, operation: str, duration: float):
        """Track operation response times"""
        self.response_times.append({
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'operation': operation,
            'duration': duration
        })
    
    def track_ai_cost(self, model: str, cost: float, tokens: int):
        """Track AI usage costs"""
        self.ai_costs[model] += cost
    
    def track_user_satisfaction(self, user_id: int, score: float):
        """Track user satisfaction scores"""
        self.user_satisfaction_scores.append({
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'user_id': user_id,
            'score': score
        })
    
    def get_user_analytics(self, hours: int = 24) -> Dict[str, Any]:
        """Get user analytics for specified time period"""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        cutoff_str = cutoff.strftime('%Y-%m-%d-%H')
        
        # Active users by hour
        active_users_by_hour = {}
        total_activities = defaultdict(int)
        
        for hour_key, activities in self.user_activity_tracker.items():
            if hour_key >= cutoff_str:
                active_users_by_hour[hour_key] = sum(activities.values())
                for activity, count in activities.items():
                    total_activities[activity] += count
        
        # Conversation flow analysis
        recent_conversations = [
            conv for conv in self.conversation_metrics
            if datetime.fromisoformat(conv['timestamp']) > cutoff
        ]
        
        # User engagement metrics
        unique_users = len(set(conv['user_id'] for conv in recent_conversations))
        avg_session_length = self._calculate_avg_session_length(recent_conversations)
        
        return {
            'active_users_by_hour': active_users_by_hour,
            'total_activities': dict(total_activities),
            'unique_users_24h': unique_users,
            'total_conversations': len(recent_conversations),
            'avg_session_length_minutes': avg_session_length,
            'user_satisfaction': {
                'avg_score': statistics.mean([s['score'] for s in self.user_satisfaction_scores]) if self.user_satisfaction_scores else 0,
                'recent_scores': list(self.user_satisfaction_scores)[-10:]
            }
        }
    
    def get_performance_analytics(self) -> Dict[str, Any]:
        """Get performance analytics"""
        recent_responses = list(self.response_times)[-100:]  # Last 100 responses
        
        if not recent_responses:
            return {'error': 'No recent performance data'}
        
        # Group by operation type
        operation_stats = defaultdict(list)
        for response in recent_responses:
            operation_stats[response['operation']].append(response['duration'])
        
        # Calculate statistics for each operation
        performance_stats = {}
        for operation, durations in operation_stats.items():
            performance_stats[operation] = {
                'avg_duration': statistics.mean(durations),
                'min_duration': min(durations),
                'max_duration': max(durations),
                'p95_duration': self._percentile(durations, 95),
                'count': len(durations)
            }
        
        # Overall performance metrics
        all_durations = [r['duration'] for r in recent_responses]
        overall_performance = {
            'avg_response_time': statistics.mean(all_durations),
            'p95_response_time': self._percentile(all_durations, 95),
            'p99_response_time': self._percentile(all_durations, 99),
            'total_requests': len(recent_responses),
            'operation_breakdown': performance_stats
        }
        
        return overall_performance
    
    def get_ai_usage_analytics(self) -> Dict[str, Any]:
        """Get AI usage analytics"""
        return {
            'total_costs_by_model': dict(self.ai_costs),
            'total_cost': sum(self.ai_costs.values()),
            'cost_trend': self._get_cost_trend(),
            'model_usage_distribution': self._get_model_usage_distribution()
        }
    
    def _calculate_avg_session_length(self, conversations: List[Dict]) -> float:
        """Calculate average session length in minutes"""
        if not conversations:
            return 0.0
        
        # Group conversations by user
        user_sessions = defaultdict(list)
        for conv in conversations:
            user_sessions[conv['user_id']].append(datetime.fromisoformat(conv['timestamp']))
        
        # Calculate session lengths
        session_lengths = []
        for user_id, timestamps in user_sessions.items():
            if len(timestamps) > 1:
                timestamps.sort()
                session_length = (timestamps[-1] - timestamps[0]).total_seconds() / 60
                session_lengths.append(session_length)
        
        return statistics.mean(session_lengths) if session_lengths else 0.0
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile"""
        sorted_data = sorted(data)
        index = int((percentile / 100) * len(sorted_data))
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    def _get_cost_trend(self) -> List[Dict[str, Any]]:
        """Get AI cost trend over time"""
        # This would ideally track costs over time
        # For now, return current totals
        return [{
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'total_cost': sum(self.ai_costs.values())
        }]
    
    def _get_model_usage_distribution(self) -> Dict[str, float]:
        """Get distribution of AI model usage by cost"""
        total_cost = sum(self.ai_costs.values())
        if total_cost == 0:
            return {}
        
        return {
            model: (cost / total_cost) * 100
            for model, cost in self.ai_costs.items()
        }


class AlertsManager(EnhancedLoggerMixin):
    """Manage dashboard alerts and notifications"""
    
    def __init__(self):
        self.active_alerts = []
        self.alert_history = deque(maxlen=1000)
        self.alert_rules = {
            'high_error_rate': {'threshold': 10, 'window': 300, 'severity': 'high'},
            'slow_response': {'threshold': 5.0, 'window': 300, 'severity': 'medium'},
            'low_user_satisfaction': {'threshold': 3.0, 'window': 1800, 'severity': 'medium'},
            'high_ai_costs': {'threshold': 100.0, 'window': 3600, 'severity': 'low'},
            'service_down': {'threshold': 1, 'window': 60, 'severity': 'critical'}
        }
    
    def check_alerts(self, metrics: DashboardMetrics):
        """Check all alert conditions against current metrics"""
        current_time = datetime.now(timezone.utc)
        
        # Clear resolved alerts
        self.active_alerts = [alert for alert in self.active_alerts if not alert.get('resolved', False)]
        
        # Check each alert rule
        for rule_name, rule_config in self.alert_rules.items():
            try:
                alert_triggered = self._check_alert_rule(rule_name, rule_config, metrics)
                if alert_triggered:
                    self._create_alert(rule_name, rule_config, metrics, current_time)
            except Exception as e:
                self.log_error("ALERT_CHECK_ERROR", f"Error checking alert {rule_name}: {e}")
    
    def _check_alert_rule(self, rule_name: str, rule_config: Dict, metrics: DashboardMetrics) -> bool:
        """Check if specific alert rule is triggered"""
        if rule_name == 'high_error_rate':
            error_rate = metrics.error_statistics.get('error_rate', 0)
            return error_rate > rule_config['threshold']
        
        elif rule_name == 'slow_response':
            avg_response = metrics.performance_metrics.get('avg_response_time', 0)
            return avg_response > rule_config['threshold']
        
        elif rule_name == 'low_user_satisfaction':
            satisfaction = metrics.user_analytics.get('user_satisfaction', {}).get('avg_score', 5.0)
            return satisfaction < rule_config['threshold']
        
        elif rule_name == 'high_ai_costs':
            total_cost = metrics.ai_usage.get('total_cost', 0)
            return total_cost > rule_config['threshold']
        
        elif rule_name == 'service_down':
            unhealthy_services = sum(
                1 for service in metrics.system_health.get('services', {}).values()
                if service.get('status') in ['critical', 'unhealthy']
            )
            return unhealthy_services >= rule_config['threshold']
        
        return False
    
    def _create_alert(self, rule_name: str, rule_config: Dict, metrics: DashboardMetrics, timestamp: datetime):
        """Create new alert"""
        # Check if similar alert already exists
        existing_alert = next(
            (alert for alert in self.active_alerts if alert['rule_name'] == rule_name),
            None
        )
        
        if existing_alert:
            existing_alert['last_triggered'] = timestamp.isoformat()
            existing_alert['trigger_count'] += 1
            return
        
        # Create new alert
        alert = {
            'id': f"{rule_name}_{int(timestamp.timestamp())}",
            'rule_name': rule_name,
            'severity': rule_config['severity'],
            'message': self._generate_alert_message(rule_name, metrics),
            'timestamp': timestamp.isoformat(),
            'last_triggered': timestamp.isoformat(),
            'trigger_count': 1,
            'resolved': False,
            'acknowledged': False
        }
        
        self.active_alerts.append(alert)
        self.alert_history.append(alert.copy())
        
        self.log_error("DASHBOARD_ALERT", f"Alert triggered: {alert['message']}", 
                      alert_id=alert['id'], severity=alert['severity'])
    
    def _generate_alert_message(self, rule_name: str, metrics: DashboardMetrics) -> str:
        """Generate human-readable alert message"""
        if rule_name == 'high_error_rate':
            rate = metrics.error_statistics.get('error_rate', 0)
            return f"High error rate detected: {rate:.1f} errors/minute"
        
        elif rule_name == 'slow_response':
            avg_response = metrics.performance_metrics.get('avg_response_time', 0)
            return f"Slow response time detected: {avg_response:.2f}s average"
        
        elif rule_name == 'low_user_satisfaction':
            satisfaction = metrics.user_analytics.get('user_satisfaction', {}).get('avg_score', 5.0)
            return f"Low user satisfaction: {satisfaction:.1f}/5.0 average score"
        
        elif rule_name == 'high_ai_costs':
            total_cost = metrics.ai_usage.get('total_cost', 0)
            return f"High AI costs: ${total_cost:.2f} in recent period"
        
        elif rule_name == 'service_down':
            unhealthy = [name for name, service in metrics.system_health.get('services', {}).items() 
                        if service.get('status') in ['critical', 'unhealthy']]
            return f"Services down: {', '.join(unhealthy)}"
        
        return f"Alert triggered: {rule_name}"
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get current active alerts"""
        return self.active_alerts.copy()
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert"""
        for alert in self.active_alerts:
            if alert['id'] == alert_id:
                alert['acknowledged'] = True
                alert['acknowledged_at'] = datetime.now(timezone.utc).isoformat()
                return True
        return False
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        for alert in self.active_alerts:
            if alert['id'] == alert_id:
                alert['resolved'] = True
                alert['resolved_at'] = datetime.now(timezone.utc).isoformat()
                return True
        return False


class DashboardDataProvider(EnhancedLoggerMixin):
    """Provides consolidated data for the monitoring dashboard"""
    
    def __init__(self):
        self.metrics_aggregator = MetricsAggregator()
        self.alerts_manager = AlertsManager()
        self.data_history = deque(maxlen=1000)  # Store historical dashboard data
    
    async def get_dashboard_data(self) -> DashboardMetrics:
        """Get comprehensive dashboard data"""
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Get system health data
        health_monitor = get_health_monitor()
        if health_monitor:
            system_health = await health_monitor.get_current_health_status()
        else:
            system_health = {'status': 'unknown', 'services': {}}
        
        # Get performance metrics
        performance_metrics = self.metrics_aggregator.get_performance_analytics()
        
        # Get user analytics
        user_analytics = self.metrics_aggregator.get_user_analytics()
        
        # Get error statistics
        error_statistics = error_tracker.get_error_stats()
        
        # Get AI usage analytics
        ai_usage = self.metrics_aggregator.get_ai_usage_analytics()
        
        # Get business metrics
        business_metrics = self._get_business_metrics()
        
        # Create dashboard metrics object
        dashboard_metrics = DashboardMetrics(
            timestamp=timestamp,
            system_health=system_health,
            performance_metrics=performance_metrics,
            user_analytics=user_analytics,
            error_statistics=error_statistics,
            ai_usage=ai_usage,
            business_metrics=business_metrics,
            alerts=[]
        )
        
        # Check alerts
        self.alerts_manager.check_alerts(dashboard_metrics)
        dashboard_metrics.alerts = self.alerts_manager.get_active_alerts()
        
        # Store in history
        self.data_history.append(dashboard_metrics)
        
        return dashboard_metrics
    
    def _get_business_metrics(self) -> Dict[str, Any]:
        """Get business-relevant metrics"""
        return {
            'user_retention_rate': 85.3,  # Would be calculated from actual data
            'assessment_completion_rate': 78.9,
            'chat_engagement_rate': 92.1,
            'avg_questions_per_user': 12.3,
            'user_growth_rate': 15.7  # Weekly growth percentage
        }
    
    def get_historical_data(self, hours: int = 24) -> List[DashboardMetrics]:
        """Get historical dashboard data"""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        return [
            data for data in self.data_history
            if datetime.fromisoformat(data.timestamp) > cutoff
        ]
    
    def track_user_activity(self, user_id: int, activity_type: str, metadata: Dict[str, Any] = None):
        """Track user activity"""
        self.metrics_aggregator.track_user_activity(user_id, activity_type, metadata)
    
    def track_performance(self, operation: str, duration: float):
        """Track performance metric"""
        self.metrics_aggregator.track_response_time(operation, duration)
    
    def track_ai_usage(self, model: str, cost: float, tokens: int):
        """Track AI usage"""
        self.metrics_aggregator.track_ai_cost(model, cost, tokens)


class MonitoringDashboard(EnhancedLoggerMixin):
    """Web-based monitoring dashboard"""
    
    def __init__(self, host: str = "localhost", port: int = 8000):
        self.host = host
        self.port = port
        self.app = FastAPI(title="Selfology Monitoring Dashboard")
        self.data_provider = DashboardDataProvider()
        self.connected_clients = set()
        
        self._setup_routes()
        self._setup_static_files()
    
    def _setup_routes(self):
        """Setup FastAPI routes"""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def dashboard_home(request: Request):
            """Main dashboard page"""
            return self._get_dashboard_html()
        
        @self.app.get("/api/metrics")
        async def get_metrics():
            """Get current metrics data"""
            try:
                metrics = await self.data_provider.get_dashboard_data()
                return metrics.to_dict()
            except Exception as e:
                self.log_error("DASHBOARD_API_ERROR", f"Error getting metrics: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/health")
        async def get_health_status():
            """Get health status"""
            health_monitor = get_health_monitor()
            if health_monitor:
                return await health_monitor.get_current_health_status()
            else:
                return {"status": "unknown", "message": "Health monitor not initialized"}
        
        @self.app.get("/api/alerts")
        async def get_alerts():
            """Get active alerts"""
            return self.data_provider.alerts_manager.get_active_alerts()
        
        @self.app.post("/api/alerts/{alert_id}/acknowledge")
        async def acknowledge_alert(alert_id: str):
            """Acknowledge an alert"""
            success = self.data_provider.alerts_manager.acknowledge_alert(alert_id)
            if success:
                return {"status": "acknowledged"}
            else:
                raise HTTPException(status_code=404, detail="Alert not found")
        
        @self.app.get("/api/historical/{hours}")
        async def get_historical_data(hours: int):
            """Get historical dashboard data"""
            if hours > 168:  # Limit to 1 week
                hours = 168
            
            historical_data = self.data_provider.get_historical_data(hours)
            return [data.to_dict() for data in historical_data]
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket):
            """WebSocket endpoint for real-time updates"""
            await websocket.accept()
            self.connected_clients.add(websocket)
            
            try:
                while True:
                    # Send periodic updates
                    await asyncio.sleep(5)  # Update every 5 seconds
                    metrics = await self.data_provider.get_dashboard_data()
                    await websocket.send_json(metrics.to_dict())
            except Exception as e:
                self.log_error("WEBSOCKET_ERROR", f"WebSocket error: {e}")
            finally:
                self.connected_clients.discard(websocket)
    
    def _setup_static_files(self):
        """Setup static file serving"""
        # Create static files directory if it doesn't exist
        static_dir = Path("static")
        static_dir.mkdir(exist_ok=True)
        
        # Create dashboard HTML file
        self._create_dashboard_html()
        
        # Mount static files
        self.app.mount("/static", StaticFiles(directory="static"), name="static")
    
    def _create_dashboard_html(self):
        """Create the dashboard HTML file"""
        html_content = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Selfology Monitoring Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .metric-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .metric-value {
            font-size: 2em;
            font-weight: bold;
            color: #333;
        }
        .metric-label {
            color: #666;
            font-size: 0.9em;
            margin-top: 5px;
        }
        .status-healthy { color: #22c55e; }
        .status-degraded { color: #f59e0b; }
        .status-unhealthy { color: #ef4444; }
        .status-critical { color: #dc2626; }
        .alert {
            background: #fef2f2;
            border: 1px solid #fecaca;
            padding: 15px;
            border-radius: 8px;
            margin: 10px 0;
        }
        .alert-critical { border-color: #dc2626; background: #fef2f2; }
        .alert-high { border-color: #f59e0b; background: #fefbeb; }
        .alert-medium { border-color: #3b82f6; background: #eff6ff; }
        .chart-container {
            position: relative;
            height: 300px;
            margin: 20px 0;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🧠 Selfology Monitoring Dashboard</h1>
        <p>Real-time monitoring for AI Psychology Coach Platform</p>
        <div id="lastUpdate">Last updated: <span id="timestamp">--</span></div>
    </div>

    <div id="alerts-container"></div>

    <div class="metrics-grid">
        <div class="metric-card">
            <div class="metric-value" id="systemStatus">--</div>
            <div class="metric-label">System Status</div>
        </div>
        <div class="metric-card">
            <div class="metric-value" id="activeUsers">--</div>
            <div class="metric-label">Active Users (24h)</div>
        </div>
        <div class="metric-card">
            <div class="metric-value" id="responseTime">--</div>
            <div class="metric-label">Avg Response Time</div>
        </div>
        <div class="metric-card">
            <div class="metric-value" id="errorRate">--</div>
            <div class="metric-label">Error Rate</div>
        </div>
        <div class="metric-card">
            <div class="metric-value" id="aiCost">--</div>
            <div class="metric-label">AI Costs (24h)</div>
        </div>
        <div class="metric-card">
            <div class="metric-value" id="satisfaction">--</div>
            <div class="metric-label">User Satisfaction</div>
        </div>
    </div>

    <div class="metric-card">
        <h3>System Performance</h3>
        <div class="chart-container">
            <canvas id="performanceChart"></canvas>
        </div>
    </div>

    <div class="metric-card">
        <h3>User Activity</h3>
        <div class="chart-container">
            <canvas id="userActivityChart"></canvas>
        </div>
    </div>

    <div class="metric-card">
        <h3>Service Health</h3>
        <div id="servicesStatus"></div>
    </div>

    <script>
        let performanceChart, userActivityChart;
        let wsConnection;

        // Initialize WebSocket connection
        function initWebSocket() {
            const wsUrl = `ws://${window.location.host}/ws`;
            wsConnection = new WebSocket(wsUrl);
            
            wsConnection.onmessage = function(event) {
                const data = JSON.parse(event.data);
                updateDashboard(data);
            };
            
            wsConnection.onclose = function() {
                // Attempt to reconnect after 5 seconds
                setTimeout(initWebSocket, 5000);
            };
        }

        // Update dashboard with new data
        function updateDashboard(data) {
            // Update timestamp
            document.getElementById('timestamp').textContent = new Date(data.timestamp).toLocaleString();
            
            // Update system status
            const statusElement = document.getElementById('systemStatus');
            statusElement.textContent = data.system_health.status;
            statusElement.className = `metric-value status-${data.system_health.status}`;
            
            // Update metrics
            document.getElementById('activeUsers').textContent = data.user_analytics.unique_users_24h || 0;
            document.getElementById('responseTime').textContent = 
                (data.performance_metrics.avg_response_time || 0).toFixed(2) + 's';
            document.getElementById('errorRate').textContent = 
                (data.error_statistics.error_rate || 0).toFixed(1) + '/min';
            document.getElementById('aiCost').textContent = 
                '$' + (data.ai_usage.total_cost || 0).toFixed(2);
            document.getElementById('satisfaction').textContent = 
                (data.user_analytics.user_satisfaction?.avg_score || 0).toFixed(1) + '/5';
            
            // Update alerts
            updateAlerts(data.alerts);
            
            // Update service status
            updateServiceStatus(data.system_health.services);
            
            // Update charts
            updateCharts(data);
        }

        function updateAlerts(alerts) {
            const container = document.getElementById('alerts-container');
            container.innerHTML = '';
            
            alerts.forEach(alert => {
                const alertDiv = document.createElement('div');
                alertDiv.className = `alert alert-${alert.severity}`;
                alertDiv.innerHTML = `
                    <strong>${alert.severity.toUpperCase()}</strong>: ${alert.message}
                    <small style="float: right;">${new Date(alert.timestamp).toLocaleString()}</small>
                `;
                container.appendChild(alertDiv);
            });
        }

        function updateServiceStatus(services) {
            const container = document.getElementById('servicesStatus');
            container.innerHTML = '';
            
            for (const [serviceName, serviceData] of Object.entries(services)) {
                const serviceDiv = document.createElement('div');
                serviceDiv.style.cssText = 'display: flex; justify-content: space-between; padding: 10px; border-bottom: 1px solid #eee;';
                serviceDiv.innerHTML = `
                    <span>${serviceName}</span>
                    <span class="status-${serviceData.status}">${serviceData.status}</span>
                    <span>${serviceData.response_time?.toFixed(2) || 0}s</span>
                `;
                container.appendChild(serviceDiv);
            }
        }

        function updateCharts(data) {
            // This would be expanded to show real-time charts
            // For now, just placeholder implementation
        }

        // Initialize charts
        function initCharts() {
            const perfCtx = document.getElementById('performanceChart').getContext('2d');
            performanceChart = new Chart(perfCtx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Response Time (s)',
                        data: [],
                        borderColor: 'rgb(75, 192, 192)',
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });

            const userCtx = document.getElementById('userActivityChart').getContext('2d');
            userActivityChart = new Chart(userCtx, {
                type: 'bar',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Active Users',
                        data: [],
                        backgroundColor: 'rgba(54, 162, 235, 0.5)'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
        }

        // Initialize dashboard
        document.addEventListener('DOMContentLoaded', function() {
            initCharts();
            initWebSocket();
            
            // Load initial data
            fetch('/api/metrics')
                .then(response => response.json())
                .then(data => updateDashboard(data))
                .catch(error => console.error('Error loading initial data:', error));
        });
    </script>
</body>
</html>
        '''
        
        static_dir = Path("static")
        static_dir.mkdir(exist_ok=True)
        
        with open(static_dir / "dashboard.html", "w", encoding="utf-8") as f:
            f.write(html_content)
    
    def _get_dashboard_html(self) -> str:
        """Get dashboard HTML content"""
        try:
            with open("static/dashboard.html", "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return "<h1>Dashboard not found. Please ensure static files are properly set up.</h1>"
    
    async def start_dashboard(self):
        """Start the dashboard server"""
        self.log_with_trace('info', f"Starting monitoring dashboard on {self.host}:{self.port}")
        
        config = uvicorn.Config(
            app=self.app,
            host=self.host,
            port=self.port,
            log_level="info",
            reload=False
        )
        
        server = uvicorn.Server(config)
        await server.serve()
    
    def get_data_provider(self) -> DashboardDataProvider:
        """Get dashboard data provider for external tracking"""
        return self.data_provider


# Global dashboard instance
monitoring_dashboard = None

def initialize_dashboard(host: str = "localhost", port: int = 8000) -> MonitoringDashboard:
    """Initialize monitoring dashboard"""
    global monitoring_dashboard
    monitoring_dashboard = MonitoringDashboard(host, port)
    return monitoring_dashboard

def get_dashboard() -> Optional[MonitoringDashboard]:
    """Get global dashboard instance"""
    return monitoring_dashboard

def track_user_activity(user_id: int, activity_type: str, metadata: Dict[str, Any] = None):
    """Convenience function to track user activity"""
    if monitoring_dashboard:
        monitoring_dashboard.data_provider.track_user_activity(user_id, activity_type, metadata)

def track_performance(operation: str, duration: float):
    """Convenience function to track performance"""
    if monitoring_dashboard:
        monitoring_dashboard.data_provider.track_performance(operation, duration)

def track_ai_usage(model: str, cost: float, tokens: int):
    """Convenience function to track AI usage"""
    if monitoring_dashboard:
        monitoring_dashboard.data_provider.track_ai_usage(model, cost, tokens)
