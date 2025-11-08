#!/usr/bin/env python3
"""
Advanced log viewer and analyzer for Selfology bot.
Provides real-time log monitoring, filtering, and analysis capabilities.
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import argparse
from collections import defaultdict, Counter
import re


class LogAnalyzer:
    """
    Analyze and display Selfology bot logs with filtering and search capabilities.
    """
    
    def __init__(self, logs_dir: str = "logs"):
        self.logs_dir = Path(logs_dir)
        self.log_files = {
            'main': self.logs_dir / 'selfology.log',
            'errors': self.logs_dir / 'errors' / 'errors.log',
            'bot': self.logs_dir / 'bot' / 'bot_activity.log',
            'users': self.logs_dir / 'users' / 'user_activity.log',
            'ai': self.logs_dir / 'ai' / 'ai_interactions.log',
            'metrics': self.logs_dir / 'metrics' / 'metrics.log'
        }
    
    def parse_log_line(self, line: str) -> Optional[Dict]:
        """Parse JSON log line into dictionary"""
        try:
            return json.loads(line.strip())
        except json.JSONDecodeError:
            return None
    
    def read_logs(
        self, 
        log_type: str = 'main',
        lines: int = 100,
        follow: bool = False,
        filter_level: Optional[str] = None,
        filter_user: Optional[int] = None,
        search: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> List[Dict]:
        """
        Read and filter logs based on criteria.
        
        Args:
            log_type: Type of log to read ('main', 'errors', 'bot', 'users', 'ai', 'metrics')
            lines: Number of lines to read (from end)
            follow: Follow log file (tail -f behavior)
            filter_level: Filter by log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            filter_user: Filter by user ID
            search: Search term in log messages
            since: Filter logs since this datetime
        """
        
        log_file = self.log_files.get(log_type)
        if not log_file or not log_file.exists():
            print(f"❌ Log file not found: {log_file}")
            return []
        
        logs = []
        
        if follow:
            # Follow mode - tail -f behavior
            self._follow_logs(log_file, filter_level, filter_user, search, since)
        else:
            # Read last N lines
            with open(log_file, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
                recent_lines = all_lines[-lines:] if lines else all_lines
                
                for line in recent_lines:
                    log_entry = self.parse_log_line(line)
                    if log_entry and self._matches_filters(
                        log_entry, filter_level, filter_user, search, since
                    ):
                        logs.append(log_entry)
        
        return logs
    
    def _follow_logs(
        self,
        log_file: Path,
        filter_level: Optional[str],
        filter_user: Optional[int],
        search: Optional[str],
        since: Optional[datetime]
    ):
        """Follow log file in real-time"""
        print(f"📊 Following {log_file} (press Ctrl+C to stop)")
        
        with open(log_file, 'r', encoding='utf-8') as f:
            # Go to end of file
            f.seek(0, 2)
            
            try:
                while True:
                    line = f.readline()
                    if line:
                        log_entry = self.parse_log_line(line)
                        if log_entry and self._matches_filters(
                            log_entry, filter_level, filter_user, search, since
                        ):
                            self.print_log_entry(log_entry)
                    else:
                        time.sleep(0.1)
            except KeyboardInterrupt:
                print("\n🛑 Stopped following logs")
    
    def _matches_filters(
        self,
        log_entry: Dict,
        filter_level: Optional[str],
        filter_user: Optional[int],
        search: Optional[str],
        since: Optional[datetime]
    ) -> bool:
        """Check if log entry matches all filters"""
        
        # Level filter
        if filter_level and log_entry.get('level') != filter_level:
            return False
        
        # User filter
        if filter_user and log_entry.get('user_id') != filter_user:
            return False
        
        # Search filter
        if search:
            search_text = f"{log_entry.get('message', '')} {log_entry.get('context', {})}"
            if search.lower() not in search_text.lower():
                return False
        
        # Time filter
        if since:
            try:
                log_time = datetime.fromisoformat(log_entry.get('timestamp', '').replace('Z', '+00:00'))
                if log_time < since:
                    return False
            except (ValueError, TypeError):
                pass
        
        return True
    
    def print_log_entry(self, log_entry: Dict):
        """Pretty print a log entry"""
        timestamp = log_entry.get('timestamp', 'Unknown')
        level = log_entry.get('level', 'INFO')
        message = log_entry.get('message', '')
        user_id = log_entry.get('user_id')
        
        # Color coding for levels
        level_colors = {
            'DEBUG': '\033[36m',    # Cyan
            'INFO': '\033[32m',     # Green
            'WARNING': '\033[33m',  # Yellow
            'ERROR': '\033[31m',    # Red
            'CRITICAL': '\033[35m', # Magenta
        }
        reset_color = '\033[0m'
        
        color = level_colors.get(level, '')
        
        # Format timestamp
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            formatted_time = dt.strftime('%H:%M:%S')
        except:
            formatted_time = timestamp[:8]
        
        # Build output line
        output_parts = [
            f"{color}{formatted_time}{reset_color}",
            f"{color}[{level:8}]{reset_color}",
            message
        ]
        
        if user_id:
            output_parts.append(f"(user:{user_id})")
        
        print(' '.join(output_parts))
        
        # Print additional context if exists
        context = log_entry.get('context')
        if context and isinstance(context, dict):
            for key, value in context.items():
                if key not in ['user_id', 'timestamp']:
                    print(f"    {key}: {value}")
        
        # Print exception info if exists
        if 'exception' in log_entry:
            exc = log_entry['exception']
            print(f"    🔥 Exception: {exc.get('type', 'Unknown')}: {exc.get('message', '')}")
    
    def analyze_errors(self, hours: int = 24) -> Dict:
        """Analyze error patterns in the logs"""
        since = datetime.now() - timedelta(hours=hours)
        errors = self.read_logs('errors', lines=0, since=since)
        
        analysis = {
            'total_errors': len(errors),
            'error_types': Counter(),
            'error_codes': Counter(),
            'users_affected': set(),
            'error_timeline': defaultdict(int),
            'top_errors': []
        }
        
        for error in errors:
            # Count error types
            if 'exception' in error:
                exc_type = error['exception'].get('type', 'Unknown')
                analysis['error_types'][exc_type] += 1
            
            # Count error codes
            error_code = error.get('error_code', 'UNKNOWN')
            analysis['error_codes'][error_code] += 1
            
            # Track affected users
            if error.get('user_id'):
                analysis['users_affected'].add(error['user_id'])
            
            # Timeline (hourly buckets)
            try:
                dt = datetime.fromisoformat(error.get('timestamp', '').replace('Z', '+00:00'))
                hour_key = dt.strftime('%Y-%m-%d %H:00')
                analysis['error_timeline'][hour_key] += 1
            except:
                pass
        
        # Get most common errors
        analysis['top_errors'] = analysis['error_codes'].most_common(10)
        analysis['users_affected'] = len(analysis['users_affected'])
        
        return analysis
    
    def analyze_performance(self, hours: int = 24) -> Dict:
        """Analyze performance metrics"""
        since = datetime.now() - timedelta(hours=hours)
        metrics = self.read_logs('metrics', lines=0, since=since)
        
        analysis = {
            'total_metrics': len(metrics),
            'response_times': [],
            'ai_costs': [],
            'user_actions': Counter(),
            'performance_summary': {}
        }
        
        for metric in metrics:
            context = metric.get('context', {})
            
            # Collect response times
            if 'response_time' in context:
                analysis['response_times'].append(context['response_time'])
            
            # Collect AI costs
            if 'cost' in context:
                analysis['ai_costs'].append(context['cost'])
            
            # Count user actions
            if 'user_actions' in metric.get('message', ''):
                analysis['user_actions']['total'] += 1
        
        # Calculate performance summary
        if analysis['response_times']:
            response_times = analysis['response_times']
            analysis['performance_summary']['avg_response_time'] = sum(response_times) / len(response_times)
            analysis['performance_summary']['max_response_time'] = max(response_times)
            analysis['performance_summary']['min_response_time'] = min(response_times)
        
        if analysis['ai_costs']:
            analysis['performance_summary']['total_ai_cost'] = sum(analysis['ai_costs'])
        
        return analysis
    
    def generate_report(self, hours: int = 24) -> str:
        """Generate comprehensive log analysis report"""
        error_analysis = self.analyze_errors(hours)
        performance_analysis = self.analyze_performance(hours)
        
        report = f"""
🔍 SELFOLOGY BOT LOG ANALYSIS REPORT
{'=' * 50}
📅 Period: Last {hours} hours
📊 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🚨 ERROR ANALYSIS:
  Total Errors: {error_analysis['total_errors']}
  Users Affected: {error_analysis['users_affected']}
  
  Top Error Codes:
{self._format_counter(error_analysis['error_codes'], '    ')}
  
  Top Error Types:
{self._format_counter(error_analysis['error_types'], '    ')}

⚡ PERFORMANCE ANALYSIS:
  Total Metrics: {performance_analysis['total_metrics']}
  
"""
        
        perf_summary = performance_analysis['performance_summary']
        if perf_summary:
            if 'avg_response_time' in perf_summary:
                report += f"  Avg Response Time: {perf_summary['avg_response_time']:.2f}s\n"
                report += f"  Max Response Time: {perf_summary['max_response_time']:.2f}s\n"
            
            if 'total_ai_cost' in perf_summary:
                report += f"  Total AI Cost: ${perf_summary['total_ai_cost']:.4f}\n"
        
        return report
    
    def _format_counter(self, counter: Counter, indent: str = '') -> str:
        """Format counter data for report"""
        if not counter:
            return f"{indent}None"
        
        lines = []
        for item, count in counter.most_common(5):
            lines.append(f"{indent}{item}: {count}")
        return '\n'.join(lines)


def main():
    """Command-line interface for log analysis"""
    parser = argparse.ArgumentParser(description='Selfology Bot Log Analyzer')
    
    parser.add_argument('command', choices=['view', 'follow', 'analyze', 'report'],
                       help='Command to execute')
    parser.add_argument('--type', choices=['main', 'errors', 'bot', 'users', 'ai', 'metrics'],
                       default='main', help='Type of logs to analyze')
    parser.add_argument('--lines', type=int, default=100, help='Number of lines to display')
    parser.add_argument('--level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                       help='Filter by log level')
    parser.add_argument('--user', type=int, help='Filter by user ID')
    parser.add_argument('--search', help='Search term in log messages')
    parser.add_argument('--since', help='Filter logs since datetime (YYYY-MM-DD HH:MM:SS)')
    parser.add_argument('--hours', type=int, default=24, help='Hours to analyze (for analyze/report commands)')
    
    args = parser.parse_args()
    
    # Parse since datetime
    since = None
    if args.since:
        try:
            since = datetime.strptime(args.since, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            print(f"❌ Invalid datetime format: {args.since}")
            return
    
    analyzer = LogAnalyzer()
    
    try:
        if args.command == 'view':
            logs = analyzer.read_logs(
                log_type=args.type,
                lines=args.lines,
                filter_level=args.level,
                filter_user=args.user,
                search=args.search,
                since=since
            )
            
            for log_entry in logs:
                analyzer.print_log_entry(log_entry)
        
        elif args.command == 'follow':
            analyzer.read_logs(
                log_type=args.type,
                follow=True,
                filter_level=args.level,
                filter_user=args.user,
                search=args.search,
                since=since
            )
        
        elif args.command == 'analyze':
            if args.type == 'errors':
                analysis = analyzer.analyze_errors(args.hours)
                print(json.dumps(analysis, indent=2, default=str))
            elif args.type == 'metrics':
                analysis = analyzer.analyze_performance(args.hours)
                print(json.dumps(analysis, indent=2, default=str))
            else:
                print(f"❌ Analysis not available for log type: {args.type}")
        
        elif args.command == 'report':
            report = analyzer.generate_report(args.hours)
            print(report)
    
    except FileNotFoundError:
        print(f"❌ Log files not found in logs/ directory")
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == '__main__':
    main()