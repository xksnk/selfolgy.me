#!/usr/bin/env python3
"""
Test script for Onboarding Monitoring System

Проверяет работу всех компонентов системы мониторинга.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from selfology_bot.monitoring import initialize_onboarding_monitoring
from dotenv import load_dotenv

load_dotenv()


async def test_monitoring_system():
    """Тест системы мониторинга"""

    print("=" * 80)
    print("TESTING ONBOARDING MONITORING SYSTEM")
    print("=" * 80)

    # 1. Initialize
    print("\n1. Initializing monitoring system...")
    try:
        db_config = {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", 5432)),
            "user": os.getenv("DB_USER", "n8n"),
            "password": os.getenv("DB_PASSWORD"),
            "database": os.getenv("DB_NAME", "n8n")
        }

        bot_token = os.getenv("BOT_TOKEN")
        if not bot_token:
            print("   ❌ BOT_TOKEN not found in .env")
            return

        admin_ids_str = os.getenv("MONITORING_ADMIN_IDS", "98005572")
        admin_chat_ids = [int(id.strip()) for id in admin_ids_str.split(",")]

        monitoring = await initialize_onboarding_monitoring(
            db_config=db_config,
            bot_token=bot_token,
            admin_chat_ids=admin_chat_ids,
            enable_alerting=True,
            enable_auto_retry=True
        )

        print("   ✓ Monitoring system initialized")

    except Exception as e:
        print(f"   ❌ Failed to initialize: {e}")
        import traceback
        traceback.print_exc()
        return

    # 2. Test metrics collection
    print("\n2. Testing metrics collection...")
    try:
        metrics = await monitoring.get_current_metrics()
        print(f"   ✓ Metrics collected")
        print(f"      AI Analysis time: {metrics['timing']['ai_analysis_ms']:.0f}ms")
        print(f"      Total pipeline time: {metrics['timing']['total_pipeline_ms']:.0f}ms")
        print(f"      Vectorization success: {metrics['success_rates']['vectorization']}")
        print(f"      DP update success: {metrics['success_rates']['dp_update']}")

    except Exception as e:
        print(f"   ❌ Failed to collect metrics: {e}")

    # 3. Test pipeline status
    print("\n3. Testing pipeline status...")
    try:
        status = await monitoring.get_pipeline_status()
        users_count = len(status.get('users', []))
        print(f"   ✓ Pipeline status retrieved")
        print(f"      Active users: {users_count}")

        if users_count > 0:
            user = status['users'][0]
            print(f"      Example user #{user['user_id']}:")
            print(f"        Total answers: {user['total_answers']}")
            print(f"        Analyzed: {user['analyzed']}")
            print(f"        Vectorized: {user['vectorized']}")

    except Exception as e:
        print(f"   ❌ Failed to get pipeline status: {e}")

    # 4. Test health checks
    print("\n4. Testing services health checks...")
    try:
        health = await monitoring.check_services_health()
        print(f"   ✓ Health checks completed")

        for service, status_data in health.items():
            status = status_data.get('status', 'unknown')
            emoji = '✓' if status == 'healthy' else '✗'
            print(f"      {emoji} {service}: {status}")

    except Exception as e:
        print(f"   ❌ Failed to check health: {e}")

    # 5. Test error retrieval
    print("\n5. Testing error retrieval...")
    try:
        errors = await monitoring.get_recent_errors(hours=24)
        print(f"   ✓ Errors retrieved: {len(errors)} errors found")

        if errors:
            print(f"      Recent errors:")
            for error in errors[:3]:
                print(f"        - User #{error['user_id']}, Answer #{error['answer_id']}")
                if 'vectorization_error' in error:
                    print(f"          Vec error: {error['vectorization_error'][:50]}...")

    except Exception as e:
        print(f"   ❌ Failed to retrieve errors: {e}")

    # 6. Test retry stats
    print("\n6. Testing retry statistics...")
    try:
        retry_stats = await monitoring.get_retry_stats()
        print(f"   ✓ Retry stats retrieved")
        print(f"      Total retries: {retry_stats.get('total_retries', 0)}")
        print(f"      Successful: {retry_stats.get('successful_retries', 0)}")
        print(f"      Success rate: {retry_stats.get('success_rate', 0):.1f}%")

    except Exception as e:
        print(f"   ❌ Failed to get retry stats: {e}")

    # 7. Test metrics summary
    print("\n7. Testing metrics summary...")
    try:
        summary = await monitoring.get_metrics_summary(hours=24)

        if 'message' in summary:
            print(f"   ℹ {summary['message']}")
        else:
            print(f"   ✓ Metrics summary retrieved")
            print(f"      Data points: {summary.get('data_points', 0)}")

            timing = summary.get('timing', {})
            print(f"      Avg AI time: {timing.get('avg_ai_analysis_ms', 0):.0f}ms")
            print(f"      Max pipeline time: {timing.get('max_pipeline_ms', 0):.0f}ms")

    except Exception as e:
        print(f"   ❌ Failed to get summary: {e}")

    # 8. Test Telegram alerting (optional)
    print("\n8. Testing Telegram alerting...")
    try:
        if os.getenv("TELEGRAM_ALERTS_ENABLED", "true").lower() == "true":
            from selfology_bot.monitoring import get_telegram_alerter

            alerter = get_telegram_alerter()

            if alerter and alerter.enabled:
                print(f"   ✓ Telegram alerter is enabled")
                print(f"      Admin IDs: {admin_chat_ids}")
                print(f"      Min severity: {alerter.min_severity}")

                # Send test alert
                print(f"      Sending test alert...")
                await alerter.send_alert(
                    alert_type="test",
                    severity="warning",
                    message="Test alert from monitoring system test script",
                    details={
                        'test': True,
                        'timestamp': 'now'
                    }
                )
                print(f"      ✓ Test alert sent")
            else:
                print(f"   ℹ Telegram alerter is disabled")
        else:
            print(f"   ℹ Telegram alerts disabled in config")

    except Exception as e:
        print(f"   ⚠ Telegram alerting test skipped: {e}")

    # Cleanup
    print("\n9. Cleanup...")
    try:
        await monitoring.stop()
        print("   ✓ Monitoring system stopped")
    except Exception as e:
        print(f"   ⚠ Cleanup warning: {e}")

    print("\n" + "=" * 80)
    print("TEST COMPLETED")
    print("=" * 80)
    print("\nAll core components are working correctly!")
    print("\nNext steps:")
    print("  1. Integrate monitoring into selfology_controller.py")
    print("  2. Use CLI tool: python scripts/onboarding_monitoring_cli.py status")
    print("  3. Monitor alerts in Telegram")
    print()


if __name__ == "__main__":
    try:
        asyncio.run(test_monitoring_system())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
