#!/usr/bin/env python3
"""
Real-time monitoring dashboard for Selfology bot.
Displays live metrics, logs, and system health.
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any
import argparse

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from selfology_bot.core.logging import get_logger
from scripts.log_viewer import LogAnalyzer


class DashboardDisplay:
    """
    Real-time dashboard display for monitoring bot health and metrics.
    """
    
    def __init__(self, refresh_interval: int = 5):
        self.refresh_interval = refresh_interval
        self.log_analyzer = LogAnalyzer()
        self.start_time = datetime.now()
        
    def clear_screen(self):
        """Clear terminal screen"""
        os.system('clear' if os.name == 'posix' else 'cls')
    
    def format_uptime(self, start_time: datetime) -> str:
        """Format uptime duration"""
        uptime = datetime.now() - start_time
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        else:
            return f"{minutes}m {seconds}s"
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status"""
        
        # Analyze recent errors (last hour)
        error_analysis = self.log_analyzer.analyze_errors(hours=1)
        
        # Analyze performance (last hour)  
        perf_analysis = self.log_analyzer.analyze_performance(hours=1)
        
        # Check if bot is running (simple file check)
        bot_running = self.check_bot_status()
        
        return {
            'bot_running': bot_running,
            'uptime': self.format_uptime(self.start_time),
            'errors_last_hour': error_analysis['total_errors'],
            'users_affected': error_analysis['users_affected'],
            'top_errors': error_analysis['top_errors'][:3],
            'total_metrics': perf_analysis['total_metrics'],
            'avg_response_time': perf_analysis['performance_summary'].get('avg_response_time', 0),
            'total_ai_cost': perf_analysis['performance_summary'].get('total_ai_cost', 0)
        }
    
    def check_bot_status(self) -> bool:
        """Check if bot is currently running"""
        # Simple check - look for recent log entries
        try:
            logs = self.log_analyzer.read_logs('bot', lines=10)
            if logs:
                # Check if last log is within last 5 minutes
                last_log = logs[-1]
                last_time = datetime.fromisoformat(last_log.get('timestamp', '').replace('Z', '+00:00'))
                return (datetime.now() - last_time.replace(tzinfo=None)).seconds < 300
        except:
            pass
        return False
    
    def get_recent_activity(self) -> Dict[str, Any]:
        """Get recent user activity"""
        
        try:
            # Get recent user logs
            user_logs = self.log_analyzer.read_logs('users', lines=50)
            
            activity = {
                'recent_actions': [],
                'active_users': set(),
                'action_counts': {}
            }
            
            for log in user_logs[-10:]:  # Last 10 actions
                timestamp = log.get('timestamp', '').split('T')[1][:8]  # HH:MM:SS
                message = log.get('message', '')
                user_id = log.get('user_id', 'Unknown')
                
                activity['recent_actions'].append({
                    'time': timestamp,
                    'action': message,
                    'user': str(user_id)[-4:] if user_id != 'Unknown' else 'Unknown'  # Last 4 digits
                })
                
                if user_id != 'Unknown':
                    activity['active_users'].add(user_id)
                
                # Count actions
                action_type = message.split(':')[0] if ':' in message else message
                activity['action_counts'][action_type] = activity['action_counts'].get(action_type, 0) + 1
            
            activity['total_active_users'] = len(activity['active_users'])
            
            return activity
            
        except Exception as e:
            return {
                'recent_actions': [{'time': 'ERROR', 'action': f'Failed to load: {e}', 'user': 'SYS'}],
                'active_users': set(),
                'action_counts': {},
                'total_active_users': 0
            }
    
    def display_dashboard(self):
        """Display the monitoring dashboard"""
        
        self.clear_screen()
        
        # Header
        print("=" * 80)
        print("🤖 SELFOLOGY BOT - REAL-TIME MONITORING DASHBOARD")
        print("=" * 80)
        print(f"⏰ Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # System Status
        status = self.get_system_status()
        
        print("📊 SYSTEM STATUS")
        print("-" * 40)
        
        bot_status = "🟢 RUNNING" if status['bot_running'] else "🔴 STOPPED"
        print(f"Bot Status:        {bot_status}")
        print(f"Uptime:            {status['uptime']}")
        print(f"Errors (1h):       {status['errors_last_hour']}")
        print(f"Users Affected:    {status['users_affected']}")
        
        if status['avg_response_time'] > 0:
            print(f"Avg Response:      {status['avg_response_time']:.2f}s")
        
        if status['total_ai_cost'] > 0:
            print(f"AI Cost (1h):      ${status['total_ai_cost']:.4f}")
        
        print()
        
        # Recent Errors
        if status['top_errors']:
            print("🚨 TOP ERRORS (Last Hour)")
            print("-" * 40)
            for error_code, count in status['top_errors']:
                print(f"{error_code:<20} {count:>3} times")
            print()
        
        # Recent Activity
        activity = self.get_recent_activity()
        
        print("👥 USER ACTIVITY")
        print("-" * 40)
        print(f"Active Users:      {activity['total_active_users']}")
        print()
        
        print("📝 RECENT ACTIONS (Last 10)")
        print("-" * 40)
        for action in activity['recent_actions']:
            print(f"{action['time']} | User {action['user']} | {action['action']}")
        print()
        
        # Action Statistics
        if activity['action_counts']:
            print("📈 ACTION COUNTS")
            print("-" * 40)
            for action, count in sorted(activity['action_counts'].items(), key=lambda x: x[1], reverse=True):
                print(f"{action:<25} {count:>3}")
            print()
        
        # Quick Stats
        print("⚡ QUICK STATS")
        print("-" * 40)
        
        # Check log file sizes
        logs_dir = Path("logs")
        if logs_dir.exists():
            total_size = sum(f.stat().st_size for f in logs_dir.rglob('*.log'))
            print(f"Total Log Size:    {total_size / 1024 / 1024:.1f} MB")
        
        # Footer
        print("-" * 80)
        print(f"🔄 Auto-refresh every {self.refresh_interval}s | Press Ctrl+C to stop")
        print("=" * 80)
    
    def display_live_logs(self, log_type: str = 'main'):
        """Display live log stream"""
        
        print(f"📊 LIVE LOGS - {log_type.upper()}")
        print("=" * 80)
        print("Press Ctrl+C to stop")
        print("-" * 80)
        
        try:
            self.log_analyzer.read_logs(log_type, follow=True)
        except KeyboardInterrupt:
            print("\n🛑 Stopped following logs")
    
    async def run_dashboard(self):
        """Run the interactive dashboard"""
        
        try:
            while True:
                self.display_dashboard()
                await asyncio.sleep(self.refresh_interval)
        except KeyboardInterrupt:
            self.clear_screen()
            print("🛑 Dashboard stopped by user")
    
    def show_error_report(self, hours: int = 24):
        """Show detailed error report"""
        
        print(f"🚨 ERROR ANALYSIS REPORT - Last {hours} hours")
        print("=" * 80)
        
        report = self.log_analyzer.generate_report(hours)
        print(report)
        
        print("=" * 80)
        print("💡 For live error monitoring, use: python scripts/monitor_dashboard.py --live-errors")


def main():
    """Command-line interface for monitoring dashboard"""
    
    parser = argparse.ArgumentParser(description='Selfology Bot Monitoring Dashboard')
    
    parser.add_argument('--mode', choices=['dashboard', 'live-logs', 'error-report'], 
                       default='dashboard', help='Display mode')
    parser.add_argument('--log-type', choices=['main', 'errors', 'bot', 'users', 'ai', 'metrics'],
                       default='main', help='Log type for live mode')
    parser.add_argument('--refresh', type=int, default=5, help='Dashboard refresh interval (seconds)')
    parser.add_argument('--hours', type=int, default=24, help='Hours to analyze for error report')
    
    args = parser.parse_args()
    
    dashboard = DashboardDisplay(refresh_interval=args.refresh)
    
    try:
        if args.mode == 'dashboard':
            print("🚀 Starting Selfology Monitoring Dashboard...")
            asyncio.run(dashboard.run_dashboard())
        
        elif args.mode == 'live-logs':
            dashboard.display_live_logs(args.log_type)
        
        elif args.mode == 'error-report':
            dashboard.show_error_report(args.hours)
    
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Dashboard error: {e}")


if __name__ == '__main__':
    main()