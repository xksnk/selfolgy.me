#!/usr/bin/env python3
"""
Selfology Bot Management Script
Unified interface for managing the bot, monitoring, and troubleshooting.
"""

import argparse
import asyncio
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

def run_command(command, description=""):
    """Run shell command and return result"""
    print(f"🔧 {description}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"✅ {description} - Success")
        if result.stdout:
            print(f"   Output: {result.stdout.strip()}")
    else:
        print(f"❌ {description} - Failed")
        if result.stderr:
            print(f"   Error: {result.stderr.strip()}")
    
    return result.returncode == 0

def start_bot(mode="development"):
    """Start the Selfology bot"""
    
    print("🚀 STARTING SELFOLOGY BOT")
    print("=" * 50)
    
    if mode == "development":
        print("📋 Starting in development mode (polling)")
        command = "source venv/bin/activate && python monitored_bot.py"
    else:
        print("📋 Starting in production mode (docker)")
        command = "docker-compose -f docker-compose.selfology.yml up -d"
    
    try:
        if mode == "development":
            # Start bot directly
            subprocess.run(command, shell=True)
        else:
            # Use docker
            if run_command(command, "Starting Docker containers"):
                print("🎉 Bot started successfully!")
                print("📊 Check status: python scripts/selfology_manager.py status")
                print("📝 View logs: python scripts/selfology_manager.py logs")
    
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")

def stop_bot():
    """Stop the Selfology bot"""
    
    print("🛑 STOPPING SELFOLOGY BOT")
    print("=" * 50)
    
    # Stop Python processes
    run_command("pkill -f monitored_bot.py", "Stopping bot process")
    
    # Stop Docker containers
    run_command("docker-compose -f docker-compose.selfology.yml down", "Stopping Docker containers")
    
    print("✅ Bot stopped")

def show_status():
    """Show bot status and health"""
    
    print("📊 SELFOLOGY BOT STATUS")
    print("=" * 50)
    
    # Check if bot process is running
    result = subprocess.run("pgrep -f monitored_bot.py", shell=True, capture_output=True)
    bot_running = result.returncode == 0
    
    status_icon = "🟢" if bot_running else "🔴"
    print(f"Bot Process: {status_icon} {'RUNNING' if bot_running else 'STOPPED'}")
    
    # Check Docker containers
    docker_result = subprocess.run("docker ps --format 'table {{.Names}}\t{{.Status}}' --filter name=selfology", 
                                 shell=True, capture_output=True, text=True)
    if docker_result.stdout.strip():
        print("Docker Status:")
        print(docker_result.stdout)
    
    # Check log files
    logs_dir = Path("logs")
    if logs_dir.exists():
        print(f"\n📝 Log Files:")
        for log_file in logs_dir.rglob('*.log'):
            size_mb = log_file.stat().st_size / 1024 / 1024
            mod_time = datetime.fromtimestamp(log_file.stat().st_mtime)
            print(f"  {log_file.name:<25} {size_mb:>6.1f}MB  {mod_time.strftime('%H:%M:%S')}")
    
    # Check recent activity
    if (logs_dir / "selfology.log").exists():
        print(f"\n📈 Recent Activity:")
        result = subprocess.run("tail -3 logs/selfology.log | jq -r '.timestamp + \" - \" + .level + \" - \" + .message'", 
                               shell=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)

def view_logs(log_type="main", lines=50, follow=False):
    """View logs using the log viewer"""
    
    print(f"📝 VIEWING {log_type.upper()} LOGS")
    print("=" * 50)
    
    command = f"source venv/bin/activate && python scripts/log_viewer.py {'follow' if follow else 'view'} --type {log_type} --lines {lines}"
    
    try:
        subprocess.run(command, shell=True)
    except KeyboardInterrupt:
        print("\n🛑 Stopped viewing logs")

def show_dashboard():
    """Show monitoring dashboard"""
    
    print("📊 STARTING MONITORING DASHBOARD")
    print("=" * 50)
    
    command = "source venv/bin/activate && python scripts/monitor_dashboard.py --mode dashboard"
    
    try:
        subprocess.run(command, shell=True)
    except KeyboardInterrupt:
        print("\n🛑 Dashboard stopped")

def analyze_errors(hours=24):
    """Analyze errors in logs"""
    
    print(f"🚨 ERROR ANALYSIS - Last {hours} hours")
    print("=" * 50)
    
    command = f"source venv/bin/activate && python scripts/monitor_dashboard.py --mode error-report --hours {hours}"
    subprocess.run(command, shell=True)

def backup_logs():
    """Backup current logs"""
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path(f"logs/backup_{timestamp}")
    
    print(f"💾 CREATING LOG BACKUP")
    print("=" * 50)
    
    if run_command(f"mkdir -p {backup_dir}", "Creating backup directory"):
        if run_command(f"cp -r logs/*.log logs/*/  {backup_dir}/", "Copying log files"):
            print(f"✅ Logs backed up to: {backup_dir}")
        else:
            print(f"❌ Backup failed")

def setup_environment():
    """Setup development environment"""
    
    print("⚙️ SETTING UP SELFOLOGY ENVIRONMENT")
    print("=" * 50)
    
    steps = [
        ("python3 -m venv venv", "Creating virtual environment"),
        ("source venv/bin/activate && pip install -r requirements.txt", "Installing dependencies"),
        ("mkdir -p logs/{bot,errors,users,ai,metrics,dashboard}", "Creating log directories"),
        ("python scripts/setup_database.py", "Setting up database")
    ]
    
    for command, description in steps:
        if not run_command(command, description):
            print(f"💥 Setup failed at: {description}")
            return False
    
    print("🎉 Environment setup completed!")
    print("🚀 Start bot: python scripts/selfology_manager.py start")
    return True

def show_help():
    """Show help information"""
    
    help_text = """
🤖 SELFOLOGY BOT MANAGER
========================

COMMANDS:
  start [dev|prod]     Start the bot (development or production mode)
  stop                 Stop the bot
  restart [dev|prod]   Restart the bot
  status               Show bot status and health
  logs [type] [lines]  View logs (main|errors|bot|users|ai|metrics)
  follow [type]        Follow logs in real-time
  dashboard            Show monitoring dashboard
  errors [hours]       Analyze errors for specified hours
  backup               Backup current logs
  setup                Setup development environment
  test                 Run basic functionality tests

LOG TYPES:
  main      - Main application log
  errors    - Error and exception log  
  bot       - Bot activity and events
  users     - User interactions and analytics
  ai        - AI service interactions and costs
  metrics   - Performance and system metrics

EXAMPLES:
  python scripts/selfology_manager.py start dev
  python scripts/selfology_manager.py logs errors 100
  python scripts/selfology_manager.py follow bot
  python scripts/selfology_manager.py errors 6
  python scripts/selfology_manager.py dashboard

MONITORING:
  📊 Real-time dashboard with system health
  📝 Structured JSON logging for all events
  🚨 Error tracking and alerting
  📈 Performance metrics and analytics
  👥 User behavior tracking

For more help: https://github.com/your-repo/selfology
    """
    
    print(help_text)

def main():
    """Main CLI interface"""
    
    parser = argparse.ArgumentParser(description='Selfology Bot Management Tool')
    parser.add_argument('command', nargs='?', default='help',
                       help='Command to execute')
    parser.add_argument('args', nargs='*', help='Command arguments')
    
    args = parser.parse_args()
    
    try:
        if args.command == 'start':
            mode = args.args[0] if args.args else 'dev'
            start_bot('development' if mode == 'dev' else 'production')
        
        elif args.command == 'stop':
            stop_bot()
        
        elif args.command == 'restart':
            mode = args.args[0] if args.args else 'dev'
            stop_bot()
            time.sleep(2)
            start_bot('development' if mode == 'dev' else 'production')
        
        elif args.command == 'status':
            show_status()
        
        elif args.command == 'logs':
            log_type = args.args[0] if args.args else 'main'
            lines = int(args.args[1]) if len(args.args) > 1 else 50
            view_logs(log_type, lines)
        
        elif args.command == 'follow':
            log_type = args.args[0] if args.args else 'main'
            view_logs(log_type, follow=True)
        
        elif args.command == 'dashboard':
            show_dashboard()
        
        elif args.command == 'errors':
            hours = int(args.args[0]) if args.args else 24
            analyze_errors(hours)
        
        elif args.command == 'backup':
            backup_logs()
        
        elif args.command == 'setup':
            setup_environment()
        
        elif args.command == 'test':
            print("🧪 Running basic tests...")
            run_command("source venv/bin/activate && python -c 'from selfology_bot.core.config import settings; print(\"✅ Config OK\")'", "Testing configuration")
            run_command("source venv/bin/activate && python -c 'from selfology_bot.core.logging import get_logger; print(\"✅ Logging OK\")'", "Testing logging")
        
        elif args.command == 'help' or args.command == '--help':
            show_help()
        
        else:
            print(f"❌ Unknown command: {args.command}")
            show_help()
    
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    except Exception as e:
        print(f"💥 Error executing command: {e}")

if __name__ == '__main__':
    main()