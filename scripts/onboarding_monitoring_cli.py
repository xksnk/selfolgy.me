#!/usr/bin/env python3
"""
Onboarding Monitoring CLI

Command-line interface для мониторинга системы онбординга.

Usage:
    python scripts/onboarding_monitoring_cli.py status              # Текущий статус
    python scripts/onboarding_monitoring_cli.py metrics             # Текущие метрики
    python scripts/onboarding_monitoring_cli.py errors --hours 6    # Ошибки за последние 6 часов
    python scripts/onboarding_monitoring_cli.py health              # Проверка здоровья сервисов
    python scripts/onboarding_monitoring_cli.py retry-stats         # Статистика ретраев
    python scripts/onboarding_monitoring_cli.py summary --hours 24  # Сводка за 24 часа
    python scripts/onboarding_monitoring_cli.py start               # Запустить мониторинг
"""

import asyncio
import sys
import os
import argparse
from pathlib import Path
from typing import Dict, Any
import json
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from selfology_bot.monitoring import (
    initialize_onboarding_monitoring,
    get_monitoring_system
)
from dotenv import load_dotenv

# Load environment
load_dotenv()


def print_section(title: str):
    """Print section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_metrics(metrics: Dict[str, Any]):
    """Pretty print metrics"""
    print_section("CURRENT METRICS")

    timing = metrics.get('timing', {})
    print("\nTiming (milliseconds):")
    print(f"  SQL Save:           {timing.get('sql_save_ms', 0):.0f}ms")
    print(f"  AI Analysis:        {timing.get('ai_analysis_ms', 0):.0f}ms")
    print(f"  Vectorization:      {timing.get('vectorization_ms', 0):.0f}ms")
    print(f"  DP Update:          {timing.get('dp_update_ms', 0):.0f}ms")
    print(f"  Total Pipeline:     {timing.get('total_pipeline_ms', 0):.0f}ms")

    success_rates = metrics.get('success_rates', {})
    print("\nSuccess Rates:")
    print(f"  AI Analysis:        {success_rates.get('ai_analysis', '100%')}")
    print(f"  Vectorization:      {success_rates.get('vectorization', '100%')}")
    print(f"  DP Update:          {success_rates.get('dp_update', '100%')}")

    queue = metrics.get('queue_depth', {})
    print("\nQueue Depth:")
    print(f"  Pending Analyses:        {queue.get('pending_analyses', 0)}")
    print(f"  Pending Vectorizations:  {queue.get('pending_vectorizations', 0)}")
    print(f"  Pending DP Updates:      {queue.get('pending_dp_updates', 0)}")

    errors = metrics.get('errors', {})
    print("\nErrors:")
    print(f"  AI Errors:               {errors.get('ai_errors', 0)}")
    print(f"  Vectorization Errors:    {errors.get('vectorization_errors', 0)}")
    print(f"  DP Update Errors:        {errors.get('dp_update_errors', 0)}")

    retries = metrics.get('retries', {})
    print("\nRetries:")
    print(f"  Total:              {retries.get('total', 0)}")
    print(f"  Success Rate:       {retries.get('success_rate', '0%')}")


def print_pipeline_status(status: Dict[str, Any]):
    """Pretty print pipeline status"""
    print_section("PIPELINE STATUS")

    users = status.get('users', [])

    if not users:
        print("\n  No active users found")
        return

    print(f"\n  Active Users: {len(users)}\n")

    for user_data in users:
        user_id = user_data['user_id']
        total = user_data['total_answers']
        analyzed = user_data['analyzed']
        vectorized = user_data['vectorized']
        dp_updated = user_data['dp_updated']
        avg_time = user_data['avg_processing_time_ms']

        # Calculate completion percentages
        analyze_pct = (analyzed / total * 100) if total > 0 else 0
        vec_pct = (vectorized / total * 100) if total > 0 else 0
        dp_pct = (dp_updated / total * 100) if total > 0 else 0

        print(f"  User #{user_id}:")
        print(f"    Total Answers:     {total}")
        print(f"    Analyzed:          {analyzed}/{total} ({analyze_pct:.0f}%)")
        print(f"    Vectorized:        {vectorized}/{total} ({vec_pct:.0f}%)")
        print(f"    DP Updated:        {dp_updated}/{total} ({dp_pct:.0f}%)")
        print(f"    Avg Process Time:  {avg_time:.0f}ms")
        print()


def print_errors(errors: list):
    """Pretty print errors"""
    print_section(f"RECENT ERRORS ({len(errors)})")

    if not errors:
        print("\n  No errors found")
        return

    for i, error in enumerate(errors, 1):
        print(f"\n  {i}. Error #{error.get('analysis_id')}")
        print(f"     User:       #{error.get('user_id')}")
        print(f"     Answer:     #{error.get('answer_id')}")
        print(f"     Question:   {error.get('question_id')}")
        print(f"     Timestamp:  {error.get('timestamp')}")
        print(f"     Retries:    {error.get('retry_count')}")

        if 'vectorization_error' in error:
            print(f"     Vec Error:  {error['vectorization_error'][:80]}...")

        if 'dp_update_error' in error:
            print(f"     DP Error:   {error['dp_update_error'][:80]}...")


def print_health(health: Dict[str, Any]):
    """Pretty print health status"""
    print_section("SERVICES HEALTH")

    for service, status_data in health.items():
        status = status_data.get('status', 'unknown')
        emoji = {
            'healthy': '✓',
            'degraded': '⚠',
            'unhealthy': '✗',
            'unknown': '?'
        }.get(status, '?')

        print(f"\n  {emoji} {service.upper()}: {status}")

        if 'response_time_ms' in status_data:
            print(f"     Response Time: {status_data['response_time_ms']:.0f}ms")

        if 'error' in status_data:
            print(f"     Error: {status_data['error']}")

        if 'status_code' in status_data:
            print(f"     Status Code: {status_data['status_code']}")


def print_summary(summary: Dict[str, Any]):
    """Pretty print metrics summary"""
    print_section(f"METRICS SUMMARY ({summary.get('period_hours', 0)} hours)")

    print(f"\n  Data Points: {summary.get('data_points', 0)}")

    timing = summary.get('timing', {})
    print("\n  Average Timing:")
    print(f"    AI Analysis:    {timing.get('avg_ai_analysis_ms', 0):.0f}ms")
    print(f"    Total Pipeline: {timing.get('avg_total_pipeline_ms', 0):.0f}ms")
    print(f"    Max Pipeline:   {timing.get('max_pipeline_ms', 0):.0f}ms")

    success_rates = summary.get('success_rates', {})
    print("\n  Average Success Rates:")
    print(f"    AI Analysis:    {success_rates.get('ai_analysis', 0):.1f}%")
    print(f"    Vectorization:  {success_rates.get('vectorization', 0):.1f}%")
    print(f"    DP Update:      {success_rates.get('dp_update', 0):.1f}%")

    totals = summary.get('totals', {})
    print("\n  Totals:")
    print(f"    Retries:        {totals.get('retries', 0)}")
    print(f"    Errors:         {totals.get('errors', 0)}")


def print_retry_stats(stats: Dict[str, Any]):
    """Pretty print retry stats"""
    print_section("AUTO-RETRY STATISTICS")

    print(f"\n  Total Retries:       {stats.get('total_retries', 0)}")
    print(f"  Successful Retries:  {stats.get('successful_retries', 0)}")
    print(f"  Failed Retries:      {stats.get('failed_retries', 0)}")
    print(f"  Success Rate:        {stats.get('success_rate', 0):.1f}%")


async def get_or_initialize_system():
    """Get or initialize monitoring system"""
    system = get_monitoring_system()

    if not system:
        # Initialize
        db_config = {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", 5432)),
            "user": os.getenv("DB_USER", "n8n"),
            "password": os.getenv("DB_PASSWORD"),
            "database": os.getenv("DB_NAME", "n8n")
        }

        bot_token = os.getenv("BOT_TOKEN")
        admin_ids_str = os.getenv("MONITORING_ADMIN_IDS", os.getenv("ADMIN_USER_ID", "98005572"))
        admin_chat_ids = [int(id.strip()) for id in admin_ids_str.split(",")]

        enable_alerting = os.getenv("TELEGRAM_ALERTS_ENABLED", "true").lower() == "true"
        enable_retry = os.getenv("AUTO_RETRY_ENABLED", "true").lower() == "true"

        system = await initialize_onboarding_monitoring(
            db_config=db_config,
            bot_token=bot_token,
            admin_chat_ids=admin_chat_ids,
            enable_alerting=enable_alerting,
            enable_auto_retry=enable_retry
        )

    return system


async def cmd_status(args):
    """Show pipeline status"""
    system = await get_or_initialize_system()
    user_id = args.user if hasattr(args, 'user') else None

    status = await system.get_pipeline_status(user_id)
    print_pipeline_status(status)

    # Also show current metrics
    metrics = await system.get_current_metrics()
    print_metrics(metrics)


async def cmd_metrics(args):
    """Show current metrics"""
    system = await get_or_initialize_system()
    metrics = await system.get_current_metrics()
    print_metrics(metrics)


async def cmd_errors(args):
    """Show recent errors"""
    system = await get_or_initialize_system()
    hours = args.hours if hasattr(args, 'hours') else 1

    errors = await system.get_recent_errors(hours)
    print_errors(errors)


async def cmd_health(args):
    """Check services health"""
    system = await get_or_initialize_system()
    health = await system.check_services_health()
    print_health(health)


async def cmd_retry_stats(args):
    """Show retry statistics"""
    system = await get_or_initialize_system()
    stats = await system.get_retry_stats()
    print_retry_stats(stats)


async def cmd_summary(args):
    """Show metrics summary"""
    system = await get_or_initialize_system()
    hours = args.hours if hasattr(args, 'hours') else 24

    summary = await system.get_metrics_summary(hours)
    print_summary(summary)


async def cmd_start(args):
    """Start monitoring system"""
    print_section("STARTING ONBOARDING MONITORING SYSTEM")

    system = await get_or_initialize_system()

    print("\n  Components:")
    print(f"    ✓ Pipeline Monitor")
    if system.enable_alerting:
        print(f"    ✓ Telegram Alerter (admins: {', '.join(map(str, system.admin_chat_ids))})")
    if system.enable_auto_retry:
        print(f"    ✓ Auto-Retry Manager")

    print("\n  Starting monitoring...\n")

    try:
        await system.start()
    except KeyboardInterrupt:
        print("\n\n  Stopping monitoring...\n")
        await system.stop()
        print("  Monitoring stopped\n")


async def cmd_json(args):
    """Output as JSON"""
    system = await get_or_initialize_system()

    data = {
        'timestamp': datetime.now().isoformat(),
        'metrics': await system.get_current_metrics(),
        'status': await system.get_pipeline_status(),
        'health': await system.check_services_health()
    }

    print(json.dumps(data, indent=2, ensure_ascii=False))


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Onboarding Monitoring CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Status command
    status_parser = subparsers.add_parser('status', help='Show pipeline status')
    status_parser.add_argument('--user', type=int, help='Filter by user ID')

    # Metrics command
    subparsers.add_parser('metrics', help='Show current metrics')

    # Errors command
    errors_parser = subparsers.add_parser('errors', help='Show recent errors')
    errors_parser.add_argument('--hours', type=int, default=1, help='Hours to look back (default: 1)')

    # Health command
    subparsers.add_parser('health', help='Check services health')

    # Retry stats command
    subparsers.add_parser('retry-stats', help='Show retry statistics')

    # Summary command
    summary_parser = subparsers.add_parser('summary', help='Show metrics summary')
    summary_parser.add_argument('--hours', type=int, default=24, help='Hours to summarize (default: 24)')

    # Start command
    subparsers.add_parser('start', help='Start monitoring system')

    # JSON command
    subparsers.add_parser('json', help='Output all data as JSON')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Command mapping
    commands = {
        'status': cmd_status,
        'metrics': cmd_metrics,
        'errors': cmd_errors,
        'health': cmd_health,
        'retry-stats': cmd_retry_stats,
        'summary': cmd_summary,
        'start': cmd_start,
        'json': cmd_json
    }

    cmd_func = commands.get(args.command)
    if cmd_func:
        try:
            asyncio.run(cmd_func(args))
        except Exception as e:
            print(f"\n❌ Error: {e}\n")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
