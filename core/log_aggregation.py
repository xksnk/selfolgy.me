"""
Centralized log aggregation and analysis system for Selfology.
Provides log collection, parsing, analysis, and alerting capabilities.
"""

import asyncio
import json
import re
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Pattern, Callable, Iterator
from pathlib import Path
import logging
from dataclasses import dataclass, field
from collections import defaultdict, deque, Counter
from enum import Enum
import gzip
import sqlite3
from concurrent.futures import ThreadPoolExecutor
import threading
from queue import Queue, Empty

from .enhanced_logging import EnhancedLoggerMixin, EventType, LogLevel
from .monitoring_api import get_monitoring_api


class LogLevel(Enum):
    """Log levels for analysis"""
    TRACE = 5
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50
    SECURITY = 60
    AUDIT = 70


class AggregationPeriod(Enum):
    """Log aggregation periods"""
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"


@dataclass
class LogEntry:
    """Parsed log entry"""
    timestamp: datetime
    level: str
    logger: str
    message: str
    service: Optional[str] = None
    user_id: Optional[int] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    error_code: Optional[str] = None
    event_type: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    tags: Dict[str, str] = field(default_factory=dict)
    metrics: Dict[str, float] = field(default_factory=dict)
    raw_line: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp.isoformat(),
            'level': self.level,
            'logger': self.logger,
            'message': self.message,
            'service': self.service,
            'user_id': self.user_id,
            'trace_id': self.trace_id,
            'span_id': self.span_id,
            'error_code': self.error_code,
            'event_type': self.event_type,
            'context': self.context,
            'tags': self.tags,
            'metrics': self.metrics
        }


@dataclass
class LogPattern:
    """Log pattern for anomaly detection"""
    pattern: Pattern
    severity: str
    description: str
    action: Optional[Callable] = None
    count_threshold: int = 5
    time_window: int = 300  # 5 minutes


@dataclass
class LogAggregation:
    """Aggregated log statistics"""
    period: AggregationPeriod
    timestamp: datetime
    count_by_level: Dict[str, int] = field(default_factory=dict)
    count_by_service: Dict[str, int] = field(default_factory=dict)
    count_by_logger: Dict[str, int] = field(default_factory=dict)
    error_patterns: Dict[str, int] = field(default_factory=dict)
    unique_users: int = 0
    unique_traces: int = 0
    avg_response_time: float = 0.0
    total_events: int = 0


class LogParser(EnhancedLoggerMixin):
    """Parse log entries from various formats"""
    
    def __init__(self):
        # Define log parsing patterns
        self.json_pattern = re.compile(r'^\{.*\}$')
        self.standard_pattern = re.compile(
            r'(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - '
            r'(?P<logger>[\w\.]+) - (?P<level>\w+) - (?P<message>.*?)$'
        )
        
        # Error patterns for detection
        self.error_patterns = [
            LogPattern(
                pattern=re.compile(r'(?i)database.*connection.*failed'),
                severity='critical',
                description='Database connection failure'
            ),
            LogPattern(
                pattern=re.compile(r'(?i)out of memory|memory error'),
                severity='critical',
                description='Memory exhaustion'
            ),
            LogPattern(
                pattern=re.compile(r'(?i)timeout|timed out'),
                severity='high',
                description='Operation timeout'
            ),
            LogPattern(
                pattern=re.compile(r'(?i)rate limit|throttl'),
                severity='medium',
                description='Rate limiting'
            ),
            LogPattern(
                pattern=re.compile(r'(?i)authentication.*fail|unauthorized'),
                severity='high',
                description='Authentication failure'
            ),
            LogPattern(
                pattern=re.compile(r'(?i)security|breach|attack'),
                severity='critical',
                description='Security event'
            )
        ]
    
    def parse_log_line(self, line: str) -> Optional[LogEntry]:
        """Parse a single log line into LogEntry"""
        line = line.strip()
        if not line:
            return None
        
        try:
            # Try JSON format first
            if self.json_pattern.match(line):
                return self._parse_json_log(line)
            
            # Try standard format
            match = self.standard_pattern.match(line)
            if match:
                return self._parse_standard_log(match, line)
            
            # Fallback: create basic log entry
            return LogEntry(
                timestamp=datetime.now(timezone.utc),
                level='INFO',
                logger='unknown',
                message=line,
                raw_line=line
            )
            
        except Exception as e:
            self.log_error("LOG_PARSE_ERROR", f"Failed to parse log line: {e}", line=line)
            return None
    
    def _parse_json_log(self, line: str) -> LogEntry:
        """Parse JSON-formatted log entry"""
        data = json.loads(line)
        
        # Parse timestamp
        timestamp_str = data.get('timestamp', '')
        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except ValueError:
            timestamp = datetime.now(timezone.utc)
        
        # Extract trace context
        trace_context = data.get('trace_context', {})
        
        return LogEntry(
            timestamp=timestamp,
            level=data.get('level', 'INFO'),
            logger=data.get('logger', 'unknown'),
            message=data.get('message', ''),
            service=data.get('service_name'),
            user_id=data.get('user_id'),
            trace_id=trace_context.get('trace_id') if isinstance(trace_context, dict) else data.get('trace_id'),
            span_id=trace_context.get('span_id') if isinstance(trace_context, dict) else data.get('span_id'),
            error_code=data.get('error_code'),
            event_type=data.get('event_type'),
            context=data.get('context', {}),
            tags=data.get('tags', {}),
            metrics=data.get('metrics', {}),
            raw_line=line
        )
    
    def _parse_standard_log(self, match, line: str) -> LogEntry:
        """Parse standard-formatted log entry"""
        groups = match.groupdict()
        
        # Parse timestamp
        try:
            timestamp = datetime.strptime(
                groups['timestamp'], 
                '%Y-%m-%d %H:%M:%S,%f'
            ).replace(tzinfo=timezone.utc)
        except ValueError:
            timestamp = datetime.now(timezone.utc)
        
        return LogEntry(
            timestamp=timestamp,
            level=groups['level'],
            logger=groups['logger'],
            message=groups['message'],
            raw_line=line
        )
    
    def detect_patterns(self, log_entry: LogEntry) -> List[LogPattern]:
        """Detect patterns in log entry"""
        detected_patterns = []
        
        for pattern in self.error_patterns:
            if pattern.pattern.search(log_entry.message) or pattern.pattern.search(log_entry.raw_line):
                detected_patterns.append(pattern)
        
        return detected_patterns


class LogStorage(EnhancedLoggerMixin):
    """Storage backend for log aggregation"""
    
    def __init__(self, db_path: str = "logs/aggregation.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database for log storage"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS log_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    level TEXT NOT NULL,
                    logger TEXT NOT NULL,
                    message TEXT NOT NULL,
                    service TEXT,
                    user_id INTEGER,
                    trace_id TEXT,
                    span_id TEXT,
                    error_code TEXT,
                    event_type TEXT,
                    context TEXT,
                    tags TEXT,
                    metrics TEXT,
                    raw_line TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS log_aggregations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    period TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    count_by_level TEXT,
                    count_by_service TEXT,
                    count_by_logger TEXT,
                    error_patterns TEXT,
                    unique_users INTEGER,
                    unique_traces INTEGER,
                    avg_response_time REAL,
                    total_events INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_log_timestamp ON log_entries(timestamp)
            ''')
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_log_level ON log_entries(level)
            ''')
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_log_trace ON log_entries(trace_id)
            ''')
            
            conn.commit()
    
    def store_log_entry(self, log_entry: LogEntry):
        """Store log entry in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO log_entries (
                        timestamp, level, logger, message, service, user_id,
                        trace_id, span_id, error_code, event_type, context,
                        tags, metrics, raw_line
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    log_entry.timestamp.isoformat(),
                    log_entry.level,
                    log_entry.logger,
                    log_entry.message,
                    log_entry.service,
                    log_entry.user_id,
                    log_entry.trace_id,
                    log_entry.span_id,
                    log_entry.error_code,
                    log_entry.event_type,
                    json.dumps(log_entry.context),
                    json.dumps(log_entry.tags),
                    json.dumps(log_entry.metrics),
                    log_entry.raw_line
                ))
                conn.commit()
        except Exception as e:
            self.log_error("LOG_STORAGE_ERROR", f"Failed to store log entry: {e}")
    
    def store_aggregation(self, aggregation: LogAggregation):
        """Store log aggregation"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO log_aggregations (
                        period, timestamp, count_by_level, count_by_service,
                        count_by_logger, error_patterns, unique_users,
                        unique_traces, avg_response_time, total_events
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    aggregation.period.value,
                    aggregation.timestamp.isoformat(),
                    json.dumps(aggregation.count_by_level),
                    json.dumps(aggregation.count_by_service),
                    json.dumps(aggregation.count_by_logger),
                    json.dumps(aggregation.error_patterns),
                    aggregation.unique_users,
                    aggregation.unique_traces,
                    aggregation.avg_response_time,
                    aggregation.total_events
                ))
                conn.commit()
        except Exception as e:
            self.log_error("AGGREGATION_STORAGE_ERROR", f"Failed to store aggregation: {e}")
    
    def query_logs(
        self, 
        start_time: datetime, 
        end_time: datetime,
        level: Optional[str] = None,
        service: Optional[str] = None,
        limit: int = 1000
    ) -> List[LogEntry]:
        """Query log entries"""
        query = '''
            SELECT timestamp, level, logger, message, service, user_id,
                   trace_id, span_id, error_code, event_type, context,
                   tags, metrics, raw_line
            FROM log_entries
            WHERE timestamp BETWEEN ? AND ?
        '''
        params = [start_time.isoformat(), end_time.isoformat()]
        
        if level:
            query += ' AND level = ?'
            params.append(level)
        
        if service:
            query += ' AND service = ?'
            params.append(service)
        
        query += ' ORDER BY timestamp DESC LIMIT ?'
        params.append(limit)
        
        results = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(query, params)
                for row in cursor.fetchall():
                    results.append(LogEntry(
                        timestamp=datetime.fromisoformat(row[0]),
                        level=row[1],
                        logger=row[2],
                        message=row[3],
                        service=row[4],
                        user_id=row[5],
                        trace_id=row[6],
                        span_id=row[7],
                        error_code=row[8],
                        event_type=row[9],
                        context=json.loads(row[10]) if row[10] else {},
                        tags=json.loads(row[11]) if row[11] else {},
                        metrics=json.loads(row[12]) if row[12] else {},
                        raw_line=row[13]
                    ))
        except Exception as e:
            self.log_error("LOG_QUERY_ERROR", f"Failed to query logs: {e}")
        
        return results
    
    def cleanup_old_logs(self, retention_days: int = 30):
        """Clean up old log entries"""
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                result = conn.execute(
                    'DELETE FROM log_entries WHERE timestamp < ?',
                    (cutoff.isoformat(),)
                )
                deleted_count = result.rowcount
                conn.commit()
                
                self.log_with_trace('info', f"Cleaned up {deleted_count} old log entries")
        except Exception as e:
            self.log_error("LOG_CLEANUP_ERROR", f"Failed to cleanup logs: {e}")


class LogAnalyzer(EnhancedLoggerMixin):
    """Analyze log patterns and generate insights"""
    
    def __init__(self, storage: LogStorage):
        self.storage = storage
        self.pattern_counters = defaultdict(lambda: defaultdict(int))
        self.anomaly_detectors = []
        self._setup_anomaly_detectors()
    
    def _setup_anomaly_detectors(self):
        """Setup anomaly detection rules"""
        # High error rate detector
        self.anomaly_detectors.append({
            'name': 'high_error_rate',
            'condition': lambda stats: stats.get('error_rate', 0) > 10,
            'message': 'High error rate detected'
        })
        
        # Memory usage detector
        self.anomaly_detectors.append({
            'name': 'memory_pattern',
            'condition': lambda stats: 'memory' in str(stats.get('top_errors', [])).lower(),
            'message': 'Memory-related errors detected'
        })
        
        # Security event detector
        self.anomaly_detectors.append({
            'name': 'security_events',
            'condition': lambda stats: stats.get('security_events', 0) > 0,
            'message': 'Security events detected'
        })
    
    def analyze_logs(
        self, 
        start_time: datetime, 
        end_time: datetime
    ) -> Dict[str, Any]:
        """Analyze logs for patterns and anomalies"""
        logs = self.storage.query_logs(start_time, end_time, limit=10000)
        
        if not logs:
            return {'message': 'No logs found in time range'}
        
        analysis = {
            'time_range': {
                'start': start_time.isoformat(),
                'end': end_time.isoformat()
            },
            'total_entries': len(logs),
            'level_distribution': self._analyze_level_distribution(logs),
            'service_distribution': self._analyze_service_distribution(logs),
            'error_analysis': self._analyze_errors(logs),
            'user_activity': self._analyze_user_activity(logs),
            'trace_analysis': self._analyze_traces(logs),
            'time_patterns': self._analyze_time_patterns(logs),
            'anomalies': self._detect_anomalies(logs)
        }
        
        return analysis
    
    def _analyze_level_distribution(self, logs: List[LogEntry]) -> Dict[str, Any]:
        """Analyze distribution of log levels"""
        level_counts = Counter(log.level for log in logs)
        total = len(logs)
        
        distribution = {}
        for level, count in level_counts.items():
            distribution[level] = {
                'count': count,
                'percentage': (count / total) * 100 if total > 0 else 0
            }
        
        # Calculate error rate
        error_logs = sum(count for level, count in level_counts.items() 
                        if level in ['ERROR', 'CRITICAL'])
        error_rate = (error_logs / total) * 100 if total > 0 else 0
        
        return {
            'distribution': distribution,
            'error_rate': error_rate,
            'total_errors': error_logs
        }
    
    def _analyze_service_distribution(self, logs: List[LogEntry]) -> Dict[str, Any]:
        """Analyze distribution across services"""
        service_counts = Counter(log.service or 'unknown' for log in logs)
        
        return {
            'distribution': dict(service_counts),
            'unique_services': len(service_counts)
        }
    
    def _analyze_errors(self, logs: List[LogEntry]) -> Dict[str, Any]:
        """Analyze error patterns"""
        error_logs = [log for log in logs if log.level in ['ERROR', 'CRITICAL']]
        
        if not error_logs:
            return {'message': 'No errors found'}
        
        # Group by error code
        error_codes = Counter(log.error_code for log in error_logs if log.error_code)
        
        # Group by message patterns
        message_patterns = defaultdict(int)
        for log in error_logs:
            # Simplify error messages for pattern detection
            pattern = re.sub(r'\d+', 'N', log.message)[:100]
            message_patterns[pattern] += 1
        
        # Top error patterns
        top_patterns = sorted(message_patterns.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            'total_errors': len(error_logs),
            'error_codes': dict(error_codes.most_common(10)),
            'top_patterns': [{'pattern': p, 'count': c} for p, c in top_patterns],
            'services_with_errors': list(set(log.service for log in error_logs if log.service))
        }
    
    def _analyze_user_activity(self, logs: List[LogEntry]) -> Dict[str, Any]:
        """Analyze user activity patterns"""
        user_logs = [log for log in logs if log.user_id]
        
        if not user_logs:
            return {'message': 'No user activity found'}
        
        unique_users = set(log.user_id for log in user_logs)
        user_activity = Counter(log.user_id for log in user_logs)
        
        return {
            'unique_users': len(unique_users),
            'total_user_events': len(user_logs),
            'avg_events_per_user': len(user_logs) / len(unique_users) if unique_users else 0,
            'top_active_users': dict(user_activity.most_common(10))
        }
    
    def _analyze_traces(self, logs: List[LogEntry]) -> Dict[str, Any]:
        """Analyze distributed traces"""
        trace_logs = [log for log in logs if log.trace_id]
        
        if not trace_logs:
            return {'message': 'No traces found'}
        
        unique_traces = set(log.trace_id for log in trace_logs)
        trace_spans = defaultdict(list)
        
        for log in trace_logs:
            trace_spans[log.trace_id].append(log)
        
        # Calculate trace durations
        trace_durations = []
        for trace_id, spans in trace_spans.items():
            if len(spans) > 1:
                spans.sort(key=lambda x: x.timestamp)
                duration = (spans[-1].timestamp - spans[0].timestamp).total_seconds()
                trace_durations.append(duration)
        
        avg_duration = sum(trace_durations) / len(trace_durations) if trace_durations else 0
        
        return {
            'unique_traces': len(unique_traces),
            'total_spans': len(trace_logs),
            'avg_spans_per_trace': len(trace_logs) / len(unique_traces) if unique_traces else 0,
            'avg_trace_duration': avg_duration,
            'longest_traces': sorted(trace_durations, reverse=True)[:5]
        }
    
    def _analyze_time_patterns(self, logs: List[LogEntry]) -> Dict[str, Any]:
        """Analyze temporal patterns in logs"""
        if not logs:
            return {}
        
        # Group by hour
        hourly_counts = defaultdict(int)
        for log in logs:
            hour = log.timestamp.hour
            hourly_counts[hour] += 1
        
        # Group by day of week
        daily_counts = defaultdict(int)
        for log in logs:
            day = log.timestamp.strftime('%A')
            daily_counts[day] += 1
        
        return {
            'hourly_distribution': dict(hourly_counts),
            'daily_distribution': dict(daily_counts),
            'peak_hour': max(hourly_counts.items(), key=lambda x: x[1])[0] if hourly_counts else None,
            'peak_day': max(daily_counts.items(), key=lambda x: x[1])[0] if daily_counts else None
        }
    
    def _detect_anomalies(self, logs: List[LogEntry]) -> List[Dict[str, Any]]:
        """Detect anomalies in log patterns"""
        anomalies = []
        
        # Calculate statistics for anomaly detection
        stats = {
            'total_logs': len(logs),
            'error_rate': len([l for l in logs if l.level in ['ERROR', 'CRITICAL']]) / len(logs) * 100 if logs else 0,
            'security_events': len([l for l in logs if l.event_type == EventType.SECURITY_EVENT.value]),
            'top_errors': [log.message for log in logs if log.level in ['ERROR', 'CRITICAL']][:10]
        }
        
        # Check each anomaly detector
        for detector in self.anomaly_detectors:
            try:
                if detector['condition'](stats):
                    anomalies.append({
                        'name': detector['name'],
                        'message': detector['message'],
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                        'severity': 'high'
                    })
            except Exception as e:
                self.log_error("ANOMALY_DETECTION_ERROR", 
                              f"Error in anomaly detector {detector['name']}: {e}")
        
        return anomalies


class LogAggregator(EnhancedLoggerMixin):
    """Aggregate logs into time-series data"""
    
    def __init__(self, storage: LogStorage):
        self.storage = storage
    
    def aggregate_logs(
        self, 
        start_time: datetime, 
        end_time: datetime, 
        period: AggregationPeriod
    ) -> List[LogAggregation]:
        """Aggregate logs for time period"""
        logs = self.storage.query_logs(start_time, end_time, limit=100000)
        
        if not logs:
            return []
        
        # Group logs by time periods
        time_groups = defaultdict(list)
        
        for log in logs:
            period_key = self._get_period_key(log.timestamp, period)
            time_groups[period_key].append(log)
        
        # Create aggregations
        aggregations = []
        for period_key, period_logs in time_groups.items():
            aggregation = self._create_aggregation(period_key, period_logs, period)
            aggregations.append(aggregation)
            self.storage.store_aggregation(aggregation)
        
        return sorted(aggregations, key=lambda x: x.timestamp)
    
    def _get_period_key(self, timestamp: datetime, period: AggregationPeriod) -> datetime:
        """Get period key for timestamp"""
        if period == AggregationPeriod.MINUTE:
            return timestamp.replace(second=0, microsecond=0)
        elif period == AggregationPeriod.HOUR:
            return timestamp.replace(minute=0, second=0, microsecond=0)
        elif period == AggregationPeriod.DAY:
            return timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == AggregationPeriod.WEEK:
            days_since_monday = timestamp.weekday()
            week_start = timestamp - timedelta(days=days_since_monday)
            return week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    
    def _create_aggregation(
        self, 
        period_key: datetime, 
        logs: List[LogEntry], 
        period: AggregationPeriod
    ) -> LogAggregation:
        """Create aggregation from logs"""
        count_by_level = Counter(log.level for log in logs)
        count_by_service = Counter(log.service or 'unknown' for log in logs)
        count_by_logger = Counter(log.logger for log in logs)
        
        # Error pattern analysis
        error_logs = [log for log in logs if log.level in ['ERROR', 'CRITICAL']]
        error_patterns = Counter(log.error_code for log in error_logs if log.error_code)
        
        # Unique counts
        unique_users = len(set(log.user_id for log in logs if log.user_id))
        unique_traces = len(set(log.trace_id for log in logs if log.trace_id))
        
        # Calculate average response time from metrics
        response_times = []
        for log in logs:
            if 'response_time' in log.metrics:
                response_times.append(log.metrics['response_time'])
        
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0.0
        
        return LogAggregation(
            period=period,
            timestamp=period_key,
            count_by_level=dict(count_by_level),
            count_by_service=dict(count_by_service),
            count_by_logger=dict(count_by_logger),
            error_patterns=dict(error_patterns),
            unique_users=unique_users,
            unique_traces=unique_traces,
            avg_response_time=avg_response_time,
            total_events=len(logs)
        )


class LogCollector(EnhancedLoggerMixin):
    """Collect logs from various sources"""
    
    def __init__(self, parser: LogParser, storage: LogStorage):
        self.parser = parser
        self.storage = storage
        self.file_watchers = {}
        self.processing_queue = Queue(maxsize=10000)
        self.running = False
        self.worker_threads = []
    
    def start_collection(self, num_workers: int = 4):
        """Start log collection with worker threads"""
        if self.running:
            return
        
        self.running = True
        
        # Start worker threads
        for i in range(num_workers):
            worker = threading.Thread(target=self._process_logs_worker, daemon=True)
            worker.start()
            self.worker_threads.append(worker)
        
        self.log_with_trace('info', f"Started log collection with {num_workers} workers")
    
    def stop_collection(self):
        """Stop log collection"""
        self.running = False
        
        # Wait for workers to finish
        for worker in self.worker_threads:
            worker.join(timeout=5)
        
        self.log_with_trace('info', "Stopped log collection")
    
    def add_log_file(self, file_path: str):
        """Add log file to watch"""
        path = Path(file_path)
        if path.exists():
            self._tail_file(path)
            self.log_with_trace('info', f"Started watching log file: {file_path}")
        else:
            self.log_error("LOG_FILE_NOT_FOUND", f"Log file not found: {file_path}")
    
    def add_log_directory(self, directory_path: str, pattern: str = "*.log"):
        """Add directory of log files to watch"""
        directory = Path(directory_path)
        if directory.exists():
            for log_file in directory.glob(pattern):
                self.add_log_file(str(log_file))
        else:
            self.log_error("LOG_DIR_NOT_FOUND", f"Log directory not found: {directory_path}")
    
    def _tail_file(self, file_path: Path):
        """Tail a log file for new entries"""
        def tail_worker():
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    # Seek to end
                    f.seek(0, 2)
                    
                    while self.running:
                        line = f.readline()
                        if line:
                            try:
                                self.processing_queue.put(line.strip(), timeout=1)
                            except:
                                pass  # Queue full, skip line
                        else:
                            time.sleep(0.1)
            except Exception as e:
                self.log_error("LOG_TAIL_ERROR", f"Error tailing {file_path}: {e}")
        
        thread = threading.Thread(target=tail_worker, daemon=True)
        thread.start()
        self.file_watchers[str(file_path)] = thread
    
    def _process_logs_worker(self):
        """Worker thread to process log lines"""
        while self.running:
            try:
                line = self.processing_queue.get(timeout=1)
                if line:
                    log_entry = self.parser.parse_log_line(line)
                    if log_entry:
                        self.storage.store_log_entry(log_entry)
                        
                        # Check for patterns
                        patterns = self.parser.detect_patterns(log_entry)
                        if patterns:
                            self._handle_pattern_detection(log_entry, patterns)
                
                self.processing_queue.task_done()
                
            except Empty:
                continue
            except Exception as e:
                self.log_error("LOG_PROCESSING_ERROR", f"Error processing log: {e}")
    
    def _handle_pattern_detection(self, log_entry: LogEntry, patterns: List[LogPattern]):
        """Handle detected patterns"""
        for pattern in patterns:
            self.log_with_trace(
                'warning',
                f"Pattern detected: {pattern.description} in log entry",
                pattern=pattern.description,
                severity=pattern.severity,
                log_message=log_entry.message[:200]
            )
            
            # Trigger webhook if monitoring API is available
            api = get_monitoring_api()
            if api:
                asyncio.create_task(api.service.trigger_webhook(
                    'pattern_detected',
                    {
                        'pattern': pattern.description,
                        'severity': pattern.severity,
                        'log_entry': log_entry.to_dict()
                    }
                ))


class CentralizedLoggingService(EnhancedLoggerMixin):
    """Main service for centralized logging"""
    
    def __init__(self, storage_path: str = "logs/aggregation.db"):
        self.storage = LogStorage(storage_path)
        self.parser = LogParser()
        self.analyzer = LogAnalyzer(self.storage)
        self.aggregator = LogAggregator(self.storage)
        self.collector = LogCollector(self.parser, self.storage)
        
        self.running = False
        self.cleanup_task = None
    
    async def start_service(self):
        """Start the centralized logging service"""
        if self.running:
            return
        
        self.running = True
        
        # Start log collector
        self.collector.start_collection()
        
        # Add default log files
        self._setup_default_log_sources()
        
        # Start cleanup task
        self.cleanup_task = asyncio.create_task(self._periodic_cleanup())
        
        self.log_with_trace('info', "Centralized logging service started")
    
    async def stop_service(self):
        """Stop the centralized logging service"""
        self.running = False
        
        # Stop collector
        self.collector.stop_collection()
        
        # Cancel cleanup task
        if self.cleanup_task:
            self.cleanup_task.cancel()
        
        self.log_with_trace('info', "Centralized logging service stopped")
    
    def _setup_default_log_sources(self):
        """Setup default log sources"""
        log_directories = [
            "logs",
            "logs/application",
            "logs/errors",
            "logs/users",
            "logs/ai",
            "logs/metrics"
        ]
        
        for log_dir in log_directories:
            if Path(log_dir).exists():
                self.collector.add_log_directory(log_dir)
    
    async def _periodic_cleanup(self):
        """Periodic cleanup of old logs"""
        while self.running:
            try:
                # Run cleanup every 24 hours
                await asyncio.sleep(86400)
                
                # Clean up logs older than 30 days
                self.storage.cleanup_old_logs(30)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.log_error("LOG_CLEANUP_ERROR", f"Periodic cleanup failed: {e}")
                await asyncio.sleep(3600)  # Retry in 1 hour
    
    async def get_log_analysis(
        self, 
        hours: int = 24,
        service: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get log analysis for time period"""
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours)
        
        analysis = self.analyzer.analyze_logs(start_time, end_time)
        
        return analysis
    
    async def get_aggregated_logs(
        self, 
        hours: int = 24, 
        period: AggregationPeriod = AggregationPeriod.HOUR
    ) -> List[LogAggregation]:
        """Get aggregated log data"""
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours)
        
        aggregations = self.aggregator.aggregate_logs(start_time, end_time, period)
        
        return aggregations
    
    def get_storage(self) -> LogStorage:
        """Get storage instance for direct queries"""
        return self.storage


# Global logging service instance
logging_service = None

def initialize_centralized_logging(storage_path: str = "logs/aggregation.db") -> CentralizedLoggingService:
    """Initialize centralized logging service"""
    global logging_service
    logging_service = CentralizedLoggingService(storage_path)
    return logging_service

def get_logging_service() -> Optional[CentralizedLoggingService]:
    """Get global logging service instance"""
    return logging_service
