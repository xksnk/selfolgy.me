#!/usr/bin/env python3
"""
🔧 Selfology Debug Agent - Comprehensive Development & Debugging System
Complete lifecycle management for AI Psychology Coach development.
"""

import asyncio
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import subprocess

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.debug.system_diagnostics import SystemDiagnostics
from scripts.debug.ai_system_analyzer import AISystemAnalyzer
from scripts.debug.question_core_validator import QuestionCoreValidator
from scripts.debug.chat_manager_debugger import ChatManagerDebugger
from scripts.debug.integration_tester import IntegrationTester
from scripts.debug.performance_profiler import PerformanceProfiler
from scripts.debug.workflow_optimizer import WorkflowOptimizer
from scripts.debug.production_guardian import ProductionGuardian


class SelfologyDebugAgent:
    """
    Master Debug Agent for comprehensive Selfology development lifecycle.
    
    Handles:
    - System-wide diagnostics and health monitoring
    - AI routing and model performance analysis
    - Intelligent question core validation
    - Chat management system debugging
    - Cross-system integration testing
    - Performance profiling and optimization
    - Development workflow automation
    - Production monitoring and alerts
    """
    
    def __init__(self):
        self.components = {
            'diagnostics': SystemDiagnostics(),
            'ai_analyzer': AISystemAnalyzer(),
            'question_validator': QuestionCoreValidator(),
            'chat_debugger': ChatManagerDebugger(),
            'integration_tester': IntegrationTester(),
            'performance_profiler': PerformanceProfiler(),
            'workflow_optimizer': WorkflowOptimizer(),
            'production_guardian': ProductionGuardian()
        }
        
        self.session_log = []
        self.start_time = datetime.now()
    
    async def run_full_diagnostic(self, deep: bool = False) -> Dict[str, Any]:
        """
        Complete system diagnostic covering all components.
        
        Args:
            deep: Enable deep analysis (slower but comprehensive)
        
        Returns:
            Comprehensive diagnostic report
        """
        print("🔍 RUNNING FULL SELFOLOGY DIAGNOSTIC")
        print("=" * 60)
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'session_id': f"debug_{int(self.start_time.timestamp())}",
            'components': {},
            'summary': {},
            'recommendations': []
        }
        
        # 1. System Health Check
        print("\n📊 1/8 System Health & Infrastructure")
        results['components']['system'] = await self.components['diagnostics'].full_health_check(deep)
        
        # 2. AI System Analysis
        print("\n🤖 2/8 AI Routing & Model Performance")
        results['components']['ai'] = await self.components['ai_analyzer'].analyze_ai_performance()
        
        # 3. Question Core Validation
        print("\n🧠 3/8 Intelligent Question Core (693 questions)")
        results['components']['questions'] = await self.components['question_validator'].validate_question_system()
        
        # 4. Chat Management Debug
        print("\n💬 4/8 Chat Management Systems")
        results['components']['chat'] = await self.components['chat_debugger'].debug_chat_systems()
        
        # 5. Integration Testing
        print("\n🔗 5/8 Cross-System Integration")
        results['components']['integration'] = await self.components['integration_tester'].test_all_integrations()
        
        # 6. Performance Profiling
        print("\n⚡ 6/8 Performance Analysis")
        results['components']['performance'] = await self.components['performance_profiler'].profile_system()
        
        # 7. Workflow Optimization
        print("\n🔧 7/8 Development Workflow")
        results['components']['workflow'] = await self.components['workflow_optimizer'].analyze_workflow()
        
        # 8. Production Guardian
        print("\n🛡️ 8/8 Production Readiness")
        results['components']['production'] = await self.components['production_guardian'].production_check()
        
        # Generate Summary and Recommendations
        results['summary'] = self._generate_summary(results['components'])
        results['recommendations'] = self._generate_recommendations(results['components'])
        
        self._save_diagnostic_report(results)
        self._display_summary(results)
        
        return results
    
    async def debug_specific_issue(self, issue_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Debug specific issue with intelligent routing to appropriate component.
        
        Args:
            issue_type: Type of issue (ai_routing, chat_flow, question_logic, etc.)
            context: Additional context for debugging
        """
        print(f"🎯 DEBUGGING SPECIFIC ISSUE: {issue_type}")
        print("=" * 50)
        
        if issue_type.startswith('ai_'):
            return await self.components['ai_analyzer'].debug_specific_issue(issue_type, context)
        elif issue_type.startswith('chat_'):
            return await self.components['chat_debugger'].debug_specific_issue(issue_type, context)
        elif issue_type.startswith('question_'):
            return await self.components['question_validator'].debug_specific_issue(issue_type, context)
        elif issue_type.startswith('integration_'):
            return await self.components['integration_tester'].debug_specific_issue(issue_type, context)
        elif issue_type.startswith('performance_'):
            return await self.components['performance_profiler'].debug_specific_issue(issue_type, context)
        else:
            return await self.components['diagnostics'].debug_general_issue(issue_type, context)
    
    async def run_continuous_monitoring(self, duration_hours: int = 24):
        """
        Run continuous monitoring and alerting for specified duration.
        """
        print(f"📡 STARTING CONTINUOUS MONITORING ({duration_hours}h)")
        print("=" * 50)
        
        await self.components['production_guardian'].start_continuous_monitoring(duration_hours)
    
    def _generate_summary(self, components: Dict[str, Any]) -> Dict[str, Any]:
        """Generate executive summary of diagnostic results."""
        total_issues = 0
        critical_issues = 0
        system_health = 100.0
        
        for component, results in components.items():
            if 'issues' in results:
                total_issues += len(results['issues'])
                critical_issues += len([i for i in results['issues'] if i.get('severity') == 'critical'])
            
            if 'health_score' in results:
                system_health = min(system_health, results['health_score'])
        
        return {
            'total_issues': total_issues,
            'critical_issues': critical_issues,
            'system_health_score': system_health,
            'overall_status': 'healthy' if system_health > 80 else 'degraded' if system_health > 60 else 'critical'
        }
    
    def _generate_recommendations(self, components: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate prioritized recommendations based on diagnostic results."""
        recommendations = []
        
        for component, results in components.items():
            if 'recommendations' in results:
                for rec in results['recommendations']:
                    recommendations.append({
                        'component': component,
                        'priority': rec.get('priority', 'medium'),
                        'action': rec['action'],
                        'description': rec.get('description', ''),
                        'estimated_effort': rec.get('effort', 'unknown')
                    })
        
        # Sort by priority: critical -> high -> medium -> low
        priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        recommendations.sort(key=lambda x: priority_order.get(x['priority'], 4))
        
        return recommendations
    
    def _save_diagnostic_report(self, results: Dict[str, Any]):
        """Save diagnostic report to logs."""
        reports_dir = Path('logs/debug_reports')
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = reports_dir / f'diagnostic_report_{timestamp}.json'
        
        with open(report_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n📄 Diagnostic report saved: {report_file}")
    
    def _display_summary(self, results: Dict[str, Any]):
        """Display executive summary of diagnostic results."""
        summary = results['summary']
        recommendations = results['recommendations']
        
        print("\n" + "="*60)
        print("🎯 EXECUTIVE SUMMARY")
        print("="*60)
        
        # Health Score
        health_score = summary['system_health_score']
        status = summary['overall_status']
        status_emoji = "✅" if status == 'healthy' else "⚠️" if status == 'degraded' else "❌"
        
        print(f"{status_emoji} System Health: {health_score:.1f}% ({status.upper()})")
        print(f"📊 Total Issues: {summary['total_issues']}")
        print(f"🔴 Critical Issues: {summary['critical_issues']}")
        
        # Top Recommendations
        print(f"\n🎯 TOP RECOMMENDATIONS:")
        for i, rec in enumerate(recommendations[:5], 1):
            priority_emoji = "🔴" if rec['priority'] == 'critical' else "🟡" if rec['priority'] == 'high' else "🟢"
            print(f"{i}. {priority_emoji} [{rec['component'].upper()}] {rec['action']}")
            if rec['description']:
                print(f"   └── {rec['description']}")
        
        if len(recommendations) > 5:
            print(f"   ... and {len(recommendations) - 5} more recommendations")


async def main():
    """Main CLI interface for Debug Agent."""
    parser = argparse.ArgumentParser(
        description="Selfology Debug Agent - Comprehensive Development & Debugging System"
    )
    
    parser.add_argument('command', choices=[
        'diagnose', 'debug', 'monitor', 'optimize', 'test', 'profile', 'workflow'
    ], help='Debug command to execute')
    
    parser.add_argument('--deep', action='store_true', help='Enable deep analysis')
    parser.add_argument('--component', help='Specific component to analyze')
    parser.add_argument('--issue-type', help='Specific issue type to debug')
    parser.add_argument('--duration', type=int, default=1, help='Duration for monitoring (hours)')
    parser.add_argument('--output', help='Output file for results')
    
    args = parser.parse_args()
    
    agent = SelfologyDebugAgent()
    
    if args.command == 'diagnose':
        results = await agent.run_full_diagnostic(deep=args.deep)
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"Results saved to {args.output}")
    
    elif args.command == 'debug':
        if not args.issue_type:
            print("❌ --issue-type required for debug command")
            return
        
        context = {'component': args.component} if args.component else {}
        results = await agent.debug_specific_issue(args.issue_type, context)
        
        print("\n🎯 DEBUG RESULTS:")
        print(json.dumps(results, indent=2, default=str))
    
    elif args.command == 'monitor':
        await agent.run_continuous_monitoring(args.duration)
    
    else:
        print(f"Command '{args.command}' not yet implemented")


if __name__ == "__main__":
    asyncio.run(main())