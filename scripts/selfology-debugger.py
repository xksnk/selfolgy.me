#!/usr/bin/env python3
"""
🎯 Selfology-Debugger - Саб-агент отладки с точностью швейцарских часов
Единый интерфейс для всех компонентов агильной отладки Selfology.
"""

import asyncio
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.agile_debug_system import AgileDebugSystem
from scripts.agile_debug.question_approval_workflow import QuestionApprovalWorkflow
from scripts.agile_debug.debug_learning_engine import DebugLearningEngine
from scripts.agile_debug.system_feedback_collector import SystemFeedbackCollector
from scripts.agile_debug.surgical_debugger import SurgicalDebugger
from scripts.agile_debug.refactoring_agent import RefactoringAgent
from scripts.agile_debug.monitoring_integration import MonitoringIntegration


class SelfologyDebugger:
    """
    🎯 Мастер агильной отладки Selfology
    
    Управление всеми компонентами агильной системы отладки:
    - Question Approval Workflow (одобрение вопросов)
    - Debug Learning Engine (обучающаяся отладка)
    - System Feedback Collector (сбор обратной связи)
    - Surgical Debugger (хирургическая отладка)
    - Refactoring Agent (саб-агент рефакторинга) 
    - Monitoring Integration (интеграция мониторинга)
    """
    
    def __init__(self):
        self.debugger_start = datetime.now()
        
        # Инициализация всех компонентов
        self.agile_debug_system = AgileDebugSystem()
        self.question_workflow = QuestionApprovalWorkflow()
        self.learning_engine = DebugLearningEngine()
        self.feedback_collector = SystemFeedbackCollector()
        self.surgical_debugger = SurgicalDebugger()
        self.refactoring_agent = RefactoringAgent()
        self.monitoring_integration = MonitoringIntegration()
        
        print("🚀 Selfology-Debugger initialized")
        print("🔗 All components connected and ready")
    
    async def show_system_overview(self):
        """Показ обзора всей системы"""
        print("\n" + "="*80)
        print("🎯 SELFOLOGY AGILE DEBUG SYSTEM OVERVIEW")
        print("="*80)
        
        # Статус компонентов
        print("\n📊 COMPONENT STATUS:")
        print("-" * 40)
        
        # Question Approval
        pending_stats = await self.question_workflow.check_pending_approvals()
        print(f"✅ Question Approval:     {pending_stats['total_pending']} pending | {pending_stats['urgent_approvals']} urgent")
        
        # Learning Engine  
        learning_stats = await self.learning_engine.get_learning_statistics()
        print(f"🧠 Learning Engine:       {learning_stats.get('total_patterns', 0)} patterns | {learning_stats.get('recent_learning_activity', {}).get('new_patterns_last_week', 0)} new this week")
        
        # Feedback Collector
        feedback_summary = await self.feedback_collector.get_feedback_summary(1)  # Last 1 day
        print(f"📊 Feedback Collector:    {feedback_summary.get('total_feedback_items', 0)} items today")
        
        # Monitoring Integration
        health_overview = await self.monitoring_integration.get_comprehensive_health_overview()
        print(f"📈 Monitoring:            {health_overview['overall_health_score']:.1f}% health | {len(health_overview['active_alerts'])} alerts")
        
        # System Health Summary
        print(f"\n🎯 SYSTEM HEALTH SUMMARY:")
        print("-" * 30)
        if health_overview['overall_health_score'] > 80:
            print("✅ System Status: HEALTHY")
        elif health_overview['overall_health_score'] > 60:
            print("⚠️ System Status: DEGRADED") 
        else:
            print("❌ System Status: CRITICAL")
        
        print(f"📊 Overall Score: {health_overview['overall_health_score']:.1f}%")
        print(f"🚨 Active Alerts: {len(health_overview['active_alerts'])}")
        print(f"⏰ Uptime: {health_overview.get('uptime_percentage', 100):.1f}%")
        
        # Quick Actions
        print(f"\n🚀 QUICK ACTIONS:")
        print("-" * 20)
        print("📋 Review questions:      python scripts/selfology_agile_debugger.py review-questions")
        print("🔄 Run agile cycle:       python scripts/selfology_agile_debugger.py agile-cycle")
        print("🔧 Surgical debug:        python scripts/selfology_agile_debugger.py surgical-fix --component X --issue Y")
        print("📈 Monitor system:        python scripts/selfology_agile_debugger.py monitor --duration 24")
        print("⚙️ Refactor code:         python scripts/selfology_agile_debugger.py refactor --target X")


async def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(
        description="🎯 Selfology Agile Master - Швейцарские часы отладки",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # System overview
  python scripts/selfology_agile_debugger.py overview

  # Run full agile debug cycle  
  python scripts/selfology_agile_debugger.py agile-cycle

  # Review pending questions
  python scripts/selfology_agile_debugger.py review-questions

  # Surgical fix for specific issue
  python scripts/selfology_agile_debugger.py surgical-fix --component ai_router --issue "slow response times"

  # Start continuous monitoring
  python scripts/selfology_agile_debugger.py monitor --duration 24

  # Get learning insights
  python scripts/selfology_agile_debugger.py learn --action insights

  # Collect system feedback
  python scripts/selfology_agile_debugger.py feedback --collect

  # Run refactoring on component
  python scripts/selfology_agile_debugger.py refactor --target selfology_bot/ai
        """
    )
    
    parser.add_argument('command', choices=[
        'overview', 'agile-cycle', 'review-questions', 'surgical-fix', 
        'monitor', 'learn', 'feedback', 'refactor', 'telegram-reviewer'
    ], help='Command to execute')
    
    # Common options
    parser.add_argument('--duration', type=int, default=24, help='Duration for monitoring (hours)')
    parser.add_argument('--component', help='Component for surgical fix')
    parser.add_argument('--issue', help='Issue description for surgical fix') 
    parser.add_argument('--target', help='Target for refactoring')
    parser.add_argument('--action', help='Specific action to perform')
    parser.add_argument('--lightweight', action='store_true', help='Run lightweight version')
    parser.add_argument('--deep', action='store_true', help='Enable deep analysis')
    
    args = parser.parse_args()
    
    debugger = SelfologyDebugger()
    
    try:
        if args.command == 'overview':
            await debugger.show_system_overview()
            
        elif args.command == 'agile-cycle':
            print("🚀 Starting Full Agile Debug Cycle...")
            if args.lightweight:
                results = await debugger.agile_debug_system.run_lightweight_cycle()
                print(f"✅ Lightweight cycle completed: {results.get('cycle_type')} at {results.get('timestamp')}")
            else:
                results = await debugger.agile_debug_system.run_full_agile_cycle()
                print(f"✅ Full agile cycle completed with {results.get('performance_metrics', {}).get('fix_success_rate', 0):.1f}% success rate")
        
        elif args.command == 'review-questions':
            print("📋 Running Question Approval Cycle...")
            results = await debugger.question_workflow.run_approval_cycle()
            
            auto_approved = results.get('auto_approval_results', {}).get('auto_approved_count', 0)
            pending_count = len(results.get('pending_questions', []))
            
            print(f"✅ Questions processed:")
            print(f"  🤖 Auto-approved: {auto_approved}")
            print(f"  ⏳ Still pending: {pending_count}")
            
            if pending_count > 0:
                print(f"\n💡 Start Telegram reviewer: python scripts/telegram_question_reviewer.py")
        
        elif args.command == 'surgical-fix':
            if not args.component or not args.issue:
                print("❌ --component and --issue required for surgical fix")
                return
            
            print(f"🔧 Performing surgical fix on {args.component}...")
            results = await debugger.surgical_debugger.perform_targeted_fix(
                args.component, args.issue, {}
            )
            
            if results['success']:
                print(f"✅ Surgical fix successful in {results['execution_time']:.1f}s")
                if results['backup_created']:
                    print(f"💾 Backup created: {results.get('backup_path', 'Unknown')}")
            else:
                print(f"❌ Surgical fix failed: {results.get('error', 'Unknown error')}")
        
        elif args.command == 'monitor':
            print(f"📈 Starting continuous monitoring for {args.duration} hours...")
            await debugger.agile_debug_system.continuous_agile_monitoring(args.duration)
        
        elif args.command == 'learn':
            if args.action == 'stats':
                stats = await debugger.learning_engine.get_learning_statistics()
                print(f"🧠 Learning Statistics:")
                print(f"  Total patterns: {stats.get('total_patterns', 0)}")
                print(f"  Confidence levels: {stats.get('confidence_distribution', {})}")
                print(f"  Recent activity: {stats.get('recent_learning_activity', {})}")
                
            elif args.action == 'insights':
                # Generate and show learning insights
                feedback = await debugger.feedback_collector.collect_comprehensive_feedback()
                insights = await debugger.learning_engine.process_feedback_and_learn(feedback)
                
                print(f"💡 Learning Insights:")
                print(f"  New patterns: {len(insights.get('new_patterns_discovered', []))}")
                print(f"  Updated patterns: {len(insights.get('updated_patterns', []))}")
                print(f"  New insights: {len(insights.get('new_insights', []))}")
                
                # Show predictive alerts
                predictions = insights.get('predictive_alerts', [])
                if predictions:
                    print(f"\n🔮 Predictive Alerts:")
                    for pred in predictions[:3]:
                        print(f"  ⚠️ {pred.get('description', 'Unknown prediction')}")
                        print(f"     Confidence: {pred.get('confidence', 0):.1%}")
            
            else:
                print("❌ Use --action stats or --action insights")
        
        elif args.command == 'feedback':
            print("📊 Collecting comprehensive system feedback...")
            feedback = await debugger.feedback_collector.collect_comprehensive_feedback()
            
            print(f"✅ Feedback collected:")
            print(f"  Systems checked: {feedback['summary']['total_systems_checked']}")
            print(f"  Critical issues: {feedback['summary']['critical_issues_count']}")
            print(f"  Health indicator: {feedback['summary']['overall_health_indicator']}")
            print(f"  Collection time: {feedback['collection_duration']:.1f}s")
            
            # Show top concerns
            top_concerns = feedback['summary'].get('top_concerns', [])
            if top_concerns:
                print(f"\n🚨 Top Concerns:")
                for concern in top_concerns[:3]:
                    print(f"  {concern.get('severity', 'unknown').upper()}: {concern.get('description', 'Unknown')}")
        
        elif args.command == 'refactor':
            if not args.target:
                print("❌ --target required for refactoring")
                return
            
            print(f"⚙️ Running intelligent refactoring on {args.target}...")
            
            # Create mock debug results for refactoring
            debug_results = {
                'fixes_applied': [
                    {'component': args.target, 'fix_type': 'code_fix'}
                ],
                'unresolved_issues': []
            }
            
            results = await debugger.refactoring_agent.perform_intelligent_refactoring(debug_results)
            
            applied_count = len(results.get('refactorings_applied', []))
            opportunities = len(results.get('refactoring_opportunities', []))
            
            print(f"✅ Refactoring completed:")
            print(f"  Applied: {applied_count} refactorings")
            print(f"  Opportunities found: {opportunities}")
            
            if results.get('quality_improvements'):
                print(f"  Quality improvements detected")
        
        elif args.command == 'telegram-reviewer':
            print("📱 Starting Telegram Question Reviewer...")
            print("💡 Make sure TELEGRAM_BOT_TOKEN and DEVELOPER_CHAT_ID are set in .env")
            
            # Import and run Telegram reviewer
            try:
                from scripts.telegram_question_reviewer import main as telegram_main
                await telegram_main()
            except ImportError as e:
                print(f"❌ Telegram reviewer import failed: {str(e)}")
                print("💡 Install aiogram: pip install aiogram")
        
        else:
            print(f"❌ Unknown command: {args.command}")
            return
    
    except Exception as e:
        print(f"❌ Error executing command: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("🎯 Selfology Agile Master - Швейцарские часы отладки")
    print("=" * 60)
    
    asyncio.run(main())