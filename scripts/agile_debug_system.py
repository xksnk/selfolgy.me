#!/usr/bin/env python3
"""
🚀 Agile Debug System - Швейцарские часы отладки Selfology
Система агильной отладки с хирургической точностью и полной интеграцией.
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import argparse

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.agile_debug.question_approval_workflow import QuestionApprovalWorkflow
from scripts.agile_debug.debug_learning_engine import DebugLearningEngine
from scripts.agile_debug.system_feedback_collector import SystemFeedbackCollector
from scripts.agile_debug.surgical_debugger import SurgicalDebugger
from scripts.agile_debug.refactoring_agent import RefactoringAgent
from scripts.agile_debug.monitoring_integration import MonitoringIntegration


class AgileDebugSystem:
    """
    🎯 Агильная система отладки с хирургической точностью
    
    Основные принципы:
    - Швейцарская точность: каждый компонент выполняет свою функцию
    - Агильность: быстрая итерация и обучение на ошибках
    - Хирургическая точность: локальные исправления без поломки системы
    - Полная интеграция: все компоненты работают как единое целое
    """
    
    def __init__(self):
        self.system_start = datetime.now()
        
        # Инициализация всех подсистем
        self.question_workflow = QuestionApprovalWorkflow()
        self.learning_engine = DebugLearningEngine()
        self.feedback_collector = SystemFeedbackCollector()
        self.surgical_debugger = SurgicalDebugger()
        self.refactoring_agent = RefactoringAgent()
        self.monitoring_integration = MonitoringIntegration()
        
        # Система обратной связи между компонентами
        self._setup_component_feedback()
    
    def _setup_component_feedback(self):
        """Настройка системы обратной связи между компонентами"""
        # Подключение мониторинга к обучающей системе
        self.monitoring_integration.connect_to_learning(self.learning_engine)
        
        # Подключение сборщика отзывов ко всем системам
        self.feedback_collector.register_system('questions', self.question_workflow)
        self.feedback_collector.register_system('debugging', self.surgical_debugger)
        self.feedback_collector.register_system('refactoring', self.refactoring_agent)
        self.feedback_collector.register_system('monitoring', self.monitoring_integration)
        
        # Подключение обучающей системы к отладчику
        self.learning_engine.connect_debugger(self.surgical_debugger)
    
    async def run_full_agile_cycle(self) -> Dict[str, Any]:
        """
        Запуск полного агильного цикла отладки
        """
        print("🚀 STARTING AGILE DEBUG CYCLE - Швейцарская точность")
        print("=" * 80)
        
        cycle_results = {
            'timestamp': datetime.now().isoformat(),
            'cycle_id': f"agile_cycle_{int(self.system_start.timestamp())}",
            'phases': {},
            'learning_insights': {},
            'surgical_fixes': [],
            'system_improvements': [],
            'feedback_integration': {},
            'performance_metrics': {},
            'next_actions': []
        }
        
        # Фаза 1: Сбор системной обратной связи
        print("\n📊 Phase 1/6: System Feedback Collection")
        cycle_results['phases']['feedback_collection'] = await self._collect_system_feedback()
        
        # Фаза 2: Обучение на обратной связи
        print("\n🧠 Phase 2/6: Debug Learning Engine")
        cycle_results['phases']['learning'] = await self._run_learning_cycle(
            cycle_results['phases']['feedback_collection']
        )
        
        # Фаза 3: Валидация и одобрение вопросов
        print("\n✅ Phase 3/6: Question Approval Workflow") 
        cycle_results['phases']['question_approval'] = await self._run_question_approval_cycle()
        
        # Фаза 4: Хирургическая отладка проблем
        print("\n🔧 Phase 4/6: Surgical Debugging")
        cycle_results['phases']['surgical_debugging'] = await self._run_surgical_debugging(
            cycle_results['phases']['learning']
        )
        
        # Фаза 5: Рефакторинг по необходимости
        print("\n⚙️ Phase 5/6: Intelligent Refactoring")
        cycle_results['phases']['refactoring'] = await self._run_intelligent_refactoring(
            cycle_results['phases']['surgical_debugging']
        )
        
        # Фаза 6: Интеграция с мониторингом
        print("\n📈 Phase 6/6: Monitoring Integration")
        cycle_results['phases']['monitoring_integration'] = await self._integrate_monitoring_feedback()
        
        # Генерация итогового отчета и рекомендаций
        cycle_results = await self._generate_cycle_summary(cycle_results)
        
        # Сохранение результатов для следующего цикла
        await self._save_cycle_results(cycle_results)
        
        return cycle_results
    
    async def _collect_system_feedback(self) -> Dict[str, Any]:
        """Сбор обратной связи от всех систем"""
        return await self.feedback_collector.collect_comprehensive_feedback()
    
    async def _run_learning_cycle(self, feedback_data: Dict[str, Any]) -> Dict[str, Any]:
        """Запуск цикла обучения на собранной обратной связи"""
        return await self.learning_engine.process_feedback_and_learn(feedback_data)
    
    async def _run_question_approval_cycle(self) -> Dict[str, Any]:
        """Запуск цикла одобрения вопросов"""
        return await self.question_workflow.run_approval_cycle()
    
    async def _run_surgical_debugging(self, learning_insights: Dict[str, Any]) -> Dict[str, Any]:
        """Запуск хирургической отладки на основе обучения"""
        return await self.surgical_debugger.perform_surgical_fixes(learning_insights)
    
    async def _run_intelligent_refactoring(self, debug_results: Dict[str, Any]) -> Dict[str, Any]:
        """Запуск интеллектуального рефакторинга"""
        return await self.refactoring_agent.perform_intelligent_refactoring(debug_results)
    
    async def _integrate_monitoring_feedback(self) -> Dict[str, Any]:
        """Интеграция с системой мониторинга"""
        return await self.monitoring_integration.integrate_feedback_loop()
    
    async def _generate_cycle_summary(self, cycle_results: Dict[str, Any]) -> Dict[str, Any]:
        """Генерация итогового отчета цикла"""
        
        # Анализ эффективности цикла
        total_issues_found = sum(
            len(phase.get('issues', [])) for phase in cycle_results['phases'].values()
        )
        
        total_fixes_applied = sum(
            len(phase.get('fixes', [])) for phase in cycle_results['phases'].values()
        )
        
        cycle_results['performance_metrics'] = {
            'cycle_duration_minutes': (datetime.now() - self.system_start).total_seconds() / 60,
            'total_issues_identified': total_issues_found,
            'total_fixes_applied': total_fixes_applied,
            'fix_success_rate': (total_fixes_applied / max(total_issues_found, 1)) * 100,
            'system_components_analyzed': len(cycle_results['phases']),
            'learning_improvements': len(cycle_results['phases'].get('learning', {}).get('new_patterns', [])),
            'surgical_precision_score': cycle_results['phases'].get('surgical_debugging', {}).get('precision_score', 0)
        }
        
        # Генерация следующих действий
        cycle_results['next_actions'] = await self._generate_next_actions(cycle_results)
        
        return cycle_results
    
    async def _generate_next_actions(self, cycle_results: Dict[str, Any]) -> List[Dict[str, str]]:
        """Генерация рекомендаций для следующего цикла"""
        next_actions = []
        
        # На основе результатов обучения
        learning_phase = cycle_results['phases'].get('learning', {})
        if learning_phase.get('new_patterns'):
            next_actions.append({
                'priority': 'high',
                'action': 'Apply learned patterns to similar components',
                'component': 'learning_engine',
                'estimated_effort': '2-4 hours'
            })
        
        # На основе результатов отладки
        debug_phase = cycle_results['phases'].get('surgical_debugging', {})
        unresolved_issues = debug_phase.get('unresolved_issues', [])
        if unresolved_issues:
            next_actions.append({
                'priority': 'critical',
                'action': f'Address {len(unresolved_issues)} unresolved issues',
                'component': 'surgical_debugger', 
                'estimated_effort': '4-8 hours'
            })
        
        # На основе результатов рефакторинга
        refactoring_phase = cycle_results['phases'].get('refactoring', {})
        if refactoring_phase.get('refactoring_opportunities'):
            next_actions.append({
                'priority': 'medium',
                'action': 'Continue code quality improvements',
                'component': 'refactoring_agent',
                'estimated_effort': '3-6 hours'
            })
        
        return next_actions
    
    async def _save_cycle_results(self, cycle_results: Dict[str, Any]):
        """Сохранение результатов цикла для анализа"""
        results_dir = Path('logs/agile_debug_cycles')
        results_dir.mkdir(parents=True, exist_ok=True)
        
        cycle_file = results_dir / f"cycle_{cycle_results['cycle_id']}.json"
        
        with open(cycle_file, 'w') as f:
            json.dump(cycle_results, f, indent=2, default=str)
        
        print(f"\n💾 Cycle results saved: {cycle_file}")
    
    async def handle_telegram_question_feedback(self, user_id: int, question_id: str, action: str, 
                                              feedback: Optional[str] = None) -> Dict[str, Any]:
        """
        Обработка обратной связи по вопросам из Telegram
        
        Args:
            user_id: ID пользователя (разработчика)
            question_id: ID вопроса
            action: 'approve', 'needs_work', 'reject'
            feedback: Дополнительные комментарии
        """
        return await self.question_workflow.process_telegram_feedback(
            user_id, question_id, action, feedback
        )
    
    async def handle_chat_interaction_feedback(self, user_id: int, session_id: str, 
                                            feedback_type: str, feedback_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обработка обратной связи от взаимодействия с чатом
        
        Args:
            user_id: ID пользователя
            session_id: ID сессии чата
            feedback_type: Тип обратной связи
            feedback_data: Данные обратной связи
        """
        return await self.feedback_collector.process_chat_feedback(
            user_id, session_id, feedback_type, feedback_data
        )
    
    async def request_surgical_fix(self, component: str, issue_description: str, 
                                 context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Запрос хирургического исправления конкретной проблемы
        
        Args:
            component: Компонент системы
            issue_description: Описание проблемы
            context: Контекст проблемы
        """
        return await self.surgical_debugger.perform_targeted_fix(
            component, issue_description, context
        )
    
    async def get_system_health_overview(self) -> Dict[str, Any]:
        """Получение обзора здоровья всей системы"""
        return await self.monitoring_integration.get_comprehensive_health_overview()
    
    async def continuous_agile_monitoring(self, duration_hours: int = 24):
        """Непрерывный агильный мониторинг с автоматическими циклами"""
        print(f"🔄 Starting continuous agile monitoring for {duration_hours} hours...")
        
        cycle_interval_minutes = 60  # Цикл каждый час
        cycles_completed = 0
        
        try:
            while cycles_completed < duration_hours:
                print(f"\n⏰ Starting agile cycle #{cycles_completed + 1}")
                
                # Запуск сокращенного агильного цикла
                cycle_results = await self.run_lightweight_cycle()
                
                # Обработка критических проблем немедленно
                await self._handle_critical_issues(cycle_results)
                
                cycles_completed += 1
                
                if cycles_completed < duration_hours:
                    print(f"⏳ Waiting {cycle_interval_minutes} minutes until next cycle...")
                    await asyncio.sleep(cycle_interval_minutes * 60)
        
        except KeyboardInterrupt:
            print("\n🛑 Continuous monitoring stopped by user")
        except Exception as e:
            print(f"❌ Monitoring error: {str(e)}")
            # Система должна быть устойчива к ошибкам
            await self.surgical_debugger.handle_system_error(str(e))
    
    async def run_lightweight_cycle(self) -> Dict[str, Any]:
        """Облегченный цикл для непрерывного мониторинга"""
        lightweight_results = {
            'timestamp': datetime.now().isoformat(),
            'cycle_type': 'lightweight',
            'monitoring_check': await self.monitoring_integration.quick_health_check(),
            'question_status': await self.question_workflow.check_pending_approvals(),
            'system_feedback': await self.feedback_collector.collect_recent_feedback(hours=1),
            'critical_issues': []
        }
        
        # Быстрый анализ критических проблем
        critical_issues = await self._identify_critical_issues(lightweight_results)
        lightweight_results['critical_issues'] = critical_issues
        
        return lightweight_results
    
    async def _identify_critical_issues(self, cycle_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Выявление критических проблем требующих немедленного внимания"""
        critical_issues = []
        
        # Проверка мониторинга
        monitoring = cycle_data.get('monitoring_check', {})
        if monitoring.get('system_health_score', 100) < 50:
            critical_issues.append({
                'type': 'system_health',
                'severity': 'critical',
                'description': f"System health critically low: {monitoring.get('system_health_score')}%",
                'component': 'system_monitoring',
                'action_required': True
            })
        
        # Проверка вопросов требующих одобрения
        questions = cycle_data.get('question_status', {})
        urgent_questions = questions.get('urgent_approvals', 0)
        if urgent_questions > 10:
            critical_issues.append({
                'type': 'question_approval',
                'severity': 'high',
                'description': f"{urgent_questions} questions require urgent approval",
                'component': 'question_workflow',
                'action_required': True
            })
        
        return critical_issues
    
    async def _handle_critical_issues(self, cycle_results: Dict[str, Any]):
        """Обработка критических проблем"""
        critical_issues = cycle_results.get('critical_issues', [])
        
        for issue in critical_issues:
            if issue.get('action_required'):
                print(f"🚨 CRITICAL: {issue['description']}")
                
                # Автоматическое исправление если возможно
                await self.surgical_debugger.handle_critical_issue(issue)


async def main():
    """Main CLI interface for Agile Debug System"""
    parser = argparse.ArgumentParser(
        description="Agile Debug System - Швейцарские часы отладки Selfology"
    )
    
    parser.add_argument('command', choices=[
        'cycle', 'monitor', 'approve-questions', 'surgical-fix', 'health', 'feedback'
    ], help='Agile debug command to execute')
    
    parser.add_argument('--duration', type=int, default=24, help='Duration for monitoring (hours)')
    parser.add_argument('--component', help='Specific component for surgical fix')
    parser.add_argument('--issue', help='Issue description for surgical fix')
    parser.add_argument('--question-id', help='Question ID for approval')
    parser.add_argument('--action', choices=['approve', 'needs_work', 'reject'], help='Action for question')
    parser.add_argument('--feedback', help='Feedback text')
    parser.add_argument('--lightweight', action='store_true', help='Run lightweight cycle')
    
    args = parser.parse_args()
    
    agile_system = AgileDebugSystem()
    
    if args.command == 'cycle':
        if args.lightweight:
            results = await agile_system.run_lightweight_cycle()
        else:
            results = await agile_system.run_full_agile_cycle()
        
        print(f"\n🎯 AGILE CYCLE COMPLETED")
        print(f"📊 Performance Score: {results.get('performance_metrics', {}).get('fix_success_rate', 0):.1f}%")
        print(f"🔧 Issues Fixed: {results.get('performance_metrics', {}).get('total_fixes_applied', 0)}")
        
    elif args.command == 'monitor':
        await agile_system.continuous_agile_monitoring(args.duration)
        
    elif args.command == 'approve-questions':
        results = await agile_system.question_workflow.run_approval_cycle()
        print(f"✅ Questions processed: {len(results.get('processed_questions', []))}")
        
    elif args.command == 'surgical-fix':
        if not args.component or not args.issue:
            print("❌ --component and --issue required for surgical fix")
            return
        
        results = await agile_system.request_surgical_fix(
            args.component, args.issue, {}
        )
        print(f"🔧 Surgical fix completed: {results.get('fix_status')}")
        
    elif args.command == 'health':
        health = await agile_system.get_system_health_overview()
        print(f"💊 System Health: {health.get('overall_health_score', 0):.1f}%")
        
    elif args.command == 'feedback':
        feedback_summary = await agile_system.feedback_collector.get_feedback_summary()
        print(f"📝 Recent Feedback: {len(feedback_summary.get('recent_feedback', []))} items")


if __name__ == "__main__":
    asyncio.run(main())