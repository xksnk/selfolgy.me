"""
Event Bus Monitor for Selfology
Real-time monitoring of Redis Streams events with Web UI
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict

import redis.asyncio as redis
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import uvicorn

# Configuration
REDIS_URL = "redis://n8n-redis:6379"
EVENT_STREAM = "selfology:events"
CONSUMER_GROUP = "event-monitor"
CONSUMER_NAME = "monitor-1"

app = FastAPI(title="Selfology Event Bus Monitor")


@dataclass
class EventMetrics:
    """Metrics for event monitoring"""
    event_type: str
    count: int
    last_seen: datetime
    avg_processing_time: float
    error_count: int
    success_count: int


class EventBusMonitor:
    """Real-time Event Bus monitoring with metrics"""

    def __init__(self, redis_url: str, stream_name: str):
        self.redis_url = redis_url
        self.stream_name = stream_name
        self.redis_client: Optional[redis.Redis] = None

        # Metrics storage
        self.event_counts: Dict[str, int] = defaultdict(int)
        self.event_errors: Dict[str, int] = defaultdict(int)
        self.event_success: Dict[str, int] = defaultdict(int)
        self.event_last_seen: Dict[str, datetime] = {}
        self.event_processing_times: Dict[str, List[float]] = defaultdict(list)

        # Historical data (last 1000 events)
        self.event_history: List[Dict] = []
        self.max_history = 1000

        # Active WebSocket connections
        self.active_connections: List[WebSocket] = []

    async def connect(self):
        """Connect to Redis"""
        self.redis_client = redis.from_url(self.redis_url, decode_responses=True)

        # Create consumer group if not exists
        try:
            await self.redis_client.xgroup_create(
                self.stream_name, CONSUMER_GROUP, id="0", mkstream=True
            )
        except redis.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise

    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()

    async def monitor_events(self):
        """Monitor events from Redis Stream"""
        print(f"[Monitor] Starting to monitor stream: {self.stream_name}")

        while True:
            try:
                # Read new events
                events = await self.redis_client.xreadgroup(
                    groupname=CONSUMER_GROUP,
                    consumername=CONSUMER_NAME,
                    streams={self.stream_name: ">"},
                    count=10,
                    block=1000,
                )

                for stream, messages in events:
                    for message_id, data in messages:
                        await self._process_event(message_id, data)

                        # Acknowledge message
                        await self.redis_client.xack(
                            self.stream_name, CONSUMER_GROUP, message_id
                        )

            except Exception as e:
                print(f"[Monitor] Error: {e}")
                await asyncio.sleep(1)

    async def _process_event(self, message_id: str, data: Dict):
        """Process and track event metrics"""
        try:
            event_type = data.get("event_type", "unknown")
            timestamp = float(data.get("timestamp", time.time()))
            status = data.get("status", "unknown")
            processing_time = float(data.get("processing_time", 0))

            # Update metrics
            self.event_counts[event_type] += 1
            self.event_last_seen[event_type] = datetime.fromtimestamp(timestamp)

            if status == "error":
                self.event_errors[event_type] += 1
            elif status == "success":
                self.event_success[event_type] += 1

            if processing_time > 0:
                self.event_processing_times[event_type].append(processing_time)
                # Keep only last 100 processing times
                if len(self.event_processing_times[event_type]) > 100:
                    self.event_processing_times[event_type].pop(0)

            # Add to history
            event_data = {
                "message_id": message_id,
                "event_type": event_type,
                "timestamp": datetime.fromtimestamp(timestamp).isoformat(),
                "status": status,
                "processing_time": processing_time,
                "data": data,
            }

            self.event_history.append(event_data)
            if len(self.event_history) > self.max_history:
                self.event_history.pop(0)

            # Broadcast to WebSocket clients
            await self._broadcast_event(event_data)

            print(f"[Monitor] Event: {event_type} | Status: {status} | Time: {processing_time:.2f}s")

        except Exception as e:
            print(f"[Monitor] Error processing event: {e}")

    async def _broadcast_event(self, event_data: Dict):
        """Broadcast event to all connected WebSocket clients"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(event_data)
            except Exception:
                disconnected.append(connection)

        # Remove disconnected clients
        for connection in disconnected:
            self.active_connections.remove(connection)

    def get_metrics(self) -> Dict[str, EventMetrics]:
        """Get current metrics for all event types"""
        metrics = {}

        for event_type, count in self.event_counts.items():
            processing_times = self.event_processing_times.get(event_type, [])
            avg_time = sum(processing_times) / len(processing_times) if processing_times else 0

            metrics[event_type] = EventMetrics(
                event_type=event_type,
                count=count,
                last_seen=self.event_last_seen.get(event_type, datetime.now()),
                avg_processing_time=avg_time,
                error_count=self.event_errors.get(event_type, 0),
                success_count=self.event_success.get(event_type, 0),
            )

        return metrics

    def get_system_health(self) -> Dict:
        """Get overall system health metrics"""
        total_events = sum(self.event_counts.values())
        total_errors = sum(self.event_errors.values())
        total_success = sum(self.event_success.values())

        error_rate = (total_errors / total_events * 100) if total_events > 0 else 0
        success_rate = (total_success / total_events * 100) if total_events > 0 else 0

        # Calculate events per minute
        recent_events = [
            e for e in self.event_history
            if datetime.fromisoformat(e["timestamp"]) > datetime.now() - timedelta(minutes=1)
        ]
        events_per_minute = len(recent_events)

        return {
            "total_events": total_events,
            "total_errors": total_errors,
            "total_success": total_success,
            "error_rate": round(error_rate, 2),
            "success_rate": round(success_rate, 2),
            "events_per_minute": events_per_minute,
            "unique_event_types": len(self.event_counts),
            "uptime": "N/A",  # TODO: Track uptime
        }


# Global monitor instance
monitor = EventBusMonitor(REDIS_URL, EVENT_STREAM)


@app.on_event("startup")
async def startup_event():
    """Initialize monitor on startup"""
    await monitor.connect()
    asyncio.create_task(monitor.monitor_events())


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    await monitor.disconnect()


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Web dashboard for event monitoring"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Selfology Event Bus Monitor</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 20px;
                background: #0f0f23;
                color: #e0e0e0;
            }
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 20px;
                border-radius: 10px;
                margin-bottom: 20px;
            }
            h1 { margin: 0; color: white; }
            .metrics-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-bottom: 20px;
            }
            .metric-card {
                background: #1a1a2e;
                border-radius: 10px;
                padding: 20px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            }
            .metric-card h3 {
                margin: 0 0 10px 0;
                color: #667eea;
            }
            .metric-value {
                font-size: 2em;
                font-weight: bold;
                color: #4ecca3;
            }
            .event-table {
                width: 100%;
                background: #1a1a2e;
                border-radius: 10px;
                padding: 20px;
                overflow-x: auto;
            }
            table {
                width: 100%;
                border-collapse: collapse;
            }
            th, td {
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #2a2a3e;
            }
            th {
                background: #667eea;
                color: white;
            }
            tr:hover {
                background: #2a2a3e;
            }
            .status-success { color: #4ecca3; }
            .status-error { color: #ff6b6b; }
            .status-pending { color: #ffd93d; }
            #live-events {
                max-height: 400px;
                overflow-y: auto;
            }
            .event-item {
                background: #2a2a3e;
                padding: 10px;
                margin: 5px 0;
                border-radius: 5px;
                border-left: 3px solid #667eea;
                animation: slideIn 0.3s ease;
            }
            @keyframes slideIn {
                from { transform: translateX(-20px); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Selfology Event Bus Monitor</h1>
            <p>Real-time monitoring of microservices events</p>
        </div>

        <div class="metrics-grid" id="metrics">
            <!-- Metrics will be inserted here -->
        </div>

        <div class="event-table">
            <h2>Live Events Stream</h2>
            <div id="live-events"></div>
        </div>

        <script>
            const ws = new WebSocket(`ws://${window.location.host}/ws`);
            const liveEvents = document.getElementById('live-events');
            const maxEvents = 50;

            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);

                // Add to live events
                const eventDiv = document.createElement('div');
                eventDiv.className = 'event-item';
                eventDiv.innerHTML = `
                    <strong>${data.event_type}</strong>
                    <span class="status-${data.status}">[${data.status}]</span>
                    <span style="float: right">${new Date(data.timestamp).toLocaleTimeString()}</span>
                    <br>
                    <small>Processing time: ${data.processing_time}s</small>
                `;

                liveEvents.insertBefore(eventDiv, liveEvents.firstChild);

                // Keep only last N events
                while (liveEvents.children.length > maxEvents) {
                    liveEvents.removeChild(liveEvents.lastChild);
                }
            };

            // Fetch metrics every 5 seconds
            async function updateMetrics() {
                const response = await fetch('/metrics');
                const data = await response.json();

                const metricsDiv = document.getElementById('metrics');
                metricsDiv.innerHTML = '';

                // System health
                const health = data.system_health;
                metricsDiv.innerHTML += `
                    <div class="metric-card">
                        <h3>Total Events</h3>
                        <div class="metric-value">${health.total_events}</div>
                    </div>
                    <div class="metric-card">
                        <h3>Success Rate</h3>
                        <div class="metric-value">${health.success_rate}%</div>
                    </div>
                    <div class="metric-card">
                        <h3>Error Rate</h3>
                        <div class="metric-value">${health.error_rate}%</div>
                    </div>
                    <div class="metric-card">
                        <h3>Events/Minute</h3>
                        <div class="metric-value">${health.events_per_minute}</div>
                    </div>
                `;
            }

            updateMetrics();
            setInterval(updateMetrics, 5000);
        </script>
    </body>
    </html>
    """
    return html_content


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok", "service": "event-bus-monitor"}


@app.get("/metrics")
async def metrics():
    """Get current metrics"""
    metrics_data = monitor.get_metrics()
    system_health = monitor.get_system_health()

    return {
        "metrics": {k: asdict(v) for k, v in metrics_data.items()},
        "system_health": system_health,
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/events/history")
async def event_history(limit: int = 100):
    """Get event history"""
    return {
        "events": monitor.event_history[-limit:],
        "total": len(monitor.event_history),
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time event streaming"""
    await websocket.accept()
    monitor.active_connections.append(websocket)

    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        monitor.active_connections.remove(websocket)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
