"""
📊 System Feedback Collector - Сборщик системной обратной связи
Собирает, анализирует и интегрирует обратную связь от всех систем Selfology.
"""

import asyncio
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from collections import defaultdict, deque
from dataclasses import dataclass
from enum import Enum
import logging


class FeedbackType(Enum):
    """Типы обратной связи"""
    USER_INTERACTION = "user_interaction"
    SYSTEM_PERFORMANCE = "system_performance" 
    ERROR_REPORT = "error_report"
    AI_BEHAVIOR = "ai_behavior"
    QUESTION_QUALITY = "question_quality"
    CHAT_FLOW = "chat_flow"
    INTEGRATION_STATUS = "integration_status"
    DEVELOPER_FEEDBACK = "developer_feedback"


class FeedbackPriority(Enum):
    """Приоритеты обратной связи"""
    CRITICAL = "critical"     # Критическая - требует немедленного внимания
    HIGH = "high"            # Высокая - важная для работы системы
    MEDIUM = "medium"        # Средняя - улучшения и оптимизации
    LOW = "low"             # Низкая - информационная


@dataclass
class FeedbackEntry:
    """Запись обратной связи"""
    feedback_id: str
    feedback_type: FeedbackType
    priority: FeedbackPriority
    source_component: str
    timestamp: datetime
    data: Dict[str, Any]
    processed: bool = False
    action_taken: Optional[str] = None


class SystemFeedbackCollector:
    """
    🎯 Центральный сборщик обратной связи системы
    
    Функции:
    - Сбор обратной связи от всех компонентов системы
    - Приоритизация и категоризация обратной связи
    - Интеграция с системой обучения отладки
    - Триггеры для автоматического реагирования
    - Аналитика паттернов обратной связи
    """
    
    def __init__(self):
        self.feedback_db_path = Path('data/system_feedback.db')
        self.feedback_db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Очередь обратной связи в памяти для быстрого доступа
        self.feedback_queue = deque(maxlen=1000)
        
        # Зарегистрированные системы
        self.registered_systems = {}
        
        # Обработчики обратной связи
        self.feedback_handlers = defaultdict(list)
        
        # Настройка базы данных
        self._setup_feedback_database()
        
        # Статистика обратной связи
        self.feedback_stats = defaultdict(int)
        
        self.logger = logging.getLogger(__name__)
    
    def _setup_feedback_database(self):
        """Настройка базы данных обратной связи"""
        conn = sqlite3.connect(self.feedback_db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                feedback_id TEXT UNIQUE NOT NULL,
                feedback_type TEXT NOT NULL,
                priority TEXT NOT NULL,
                source_component TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT NOT NULL,  -- JSON данные
                processed BOOLEAN DEFAULT FALSE,
                action_taken TEXT,
                processed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedback_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_id TEXT UNIQUE NOT NULL,
                pattern_type TEXT NOT NULL,
                pattern_data TEXT NOT NULL,  -- JSON описание паттерна
                first_detected TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                occurrence_count INTEGER DEFAULT 1,
                confidence_score REAL DEFAULT 0.5
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedback_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                feedback_id TEXT NOT NULL,
                action_type TEXT NOT NULL,
                action_description TEXT NOT NULL,
                action_result TEXT,
                triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                success BOOLEAN,
                FOREIGN KEY (feedback_id) REFERENCES system_feedback (feedback_id)
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedback_type ON system_feedback(feedback_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_priority ON system_feedback(priority)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_source_component ON system_feedback(source_component)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON system_feedback(timestamp)")
        
        conn.commit()
        conn.close()
    
    def register_system(self, system_name: str, system_instance: Any):
        """Регистрация системы для сбора обратной связи"""
        self.registered_systems[system_name] = system_instance
        self.logger.info(f"Registered system for feedback collection: {system_name}")
    
    def add_feedback_handler(self, feedback_type: FeedbackType, handler: Callable):
        """Добавление обработчика для определенного типа обратной связи"""
        self.feedback_handlers[feedback_type].append(handler)
        self.logger.info(f"Added handler for feedback type: {feedback_type.value}")
    
    async def collect_feedback(self, feedback_type: FeedbackType, source_component: str, 
                             data: Dict[str, Any], priority: FeedbackPriority = FeedbackPriority.MEDIUM) -> str:
        """
        Сбор единичной записи обратной связи
        
        Args:
            feedback_type: Тип обратной связи
            source_component: Компонент-источник
            data: Данные обратной связи
            priority: Приоритет
        
        Returns:
            ID созданной записи обратной связи
        """
        try:
            feedback_id = f"fb_{int(datetime.now().timestamp() * 1000)}_{source_component}"
            
            feedback_entry = FeedbackEntry(
                feedback_id=feedback_id,
                feedback_type=feedback_type,
                priority=priority,
                source_component=source_component,
                timestamp=datetime.now(),
                data=data
            )
            
            # Добавление в очередь в памяти
            self.feedback_queue.append(feedback_entry)
            
            # Сохранение в базу данных
            await self._save_feedback_to_db(feedback_entry)
            
            # Обновление статистики
            self.feedback_stats[feedback_type] += 1
            self.feedback_stats[f"{source_component}_total"] += 1
            
            # Триггер обработчиков
            await self._trigger_feedback_handlers(feedback_entry)
            
            # Анализ паттернов
            await self._analyze_feedback_patterns(feedback_entry)
            
            self.logger.debug(f"Collected feedback: {feedback_id} from {source_component}")
            return feedback_id
            
        except Exception as e:
            self.logger.error(f"Failed to collect feedback: {str(e)}")
            return ""
    
    async def collect_comprehensive_feedback(self) -> Dict[str, Any]:
        """
        Сбор комплексной обратной связи от всех зарегистрированных систем
        
        Returns:
            Полная обратная связь от всех систем
        """
        comprehensive_feedback = {
            'timestamp': datetime.now().isoformat(),
            'collection_duration': 0,
            'system_feedback': {},
            'summary': {},
            'critical_issues': [],
            'patterns_detected': []
        }
        
        start_time = datetime.now()
        
        try:
            # Сбор от всех зарегистрированных систем
            for system_name, system_instance in self.registered_systems.items():
                system_feedback = await self._collect_system_feedback(system_name, system_instance)
                comprehensive_feedback['system_feedback'][system_name] = system_feedback
                
                # Выявление критических проблем
                critical_issues = self._extract_critical_issues(system_feedback)
                comprehensive_feedback['critical_issues'].extend(critical_issues)
            
            # Сбор дополнительной информации из логов
            log_feedback = await self._collect_log_feedback()
            comprehensive_feedback['system_feedback']['logs'] = log_feedback
            
            # Сбор метрик производительности
            performance_feedback = await self._collect_performance_feedback()
            comprehensive_feedback['system_feedback']['performance'] = performance_feedback
            
            # Анализ пользовательских взаимодействий
            user_feedback = await self._collect_user_interaction_feedback()
            comprehensive_feedback['system_feedback']['user_interactions'] = user_feedback
            
            # Генерация сводки
            comprehensive_feedback['summary'] = self._generate_feedback_summary(comprehensive_feedback)
            
            # Обнаружение паттернов
            patterns = await self._detect_feedback_patterns(comprehensive_feedback)
            comprehensive_feedback['patterns_detected'] = patterns
            
            # Расчет времени сбора
            end_time = datetime.now()
            comprehensive_feedback['collection_duration'] = (end_time - start_time).total_seconds()
            
            self.logger.info(f"Comprehensive feedback collected in {comprehensive_feedback['collection_duration']:.2f}s")
            
        except Exception as e:
            self.logger.error(f"Failed to collect comprehensive feedback: {str(e)}")
            comprehensive_feedback['error'] = str(e)
        
        return comprehensive_feedback
    
    async def _collect_system_feedback(self, system_name: str, system_instance: Any) -> Dict[str, Any]:
        """Сбор обратной связи от конкретной системы"""
        system_feedback = {
            'system_name': system_name,
            'status': 'unknown',
            'metrics': {},
            'issues': [],
            'recommendations': []
        }
        
        try:
            # Определение типа системы и соответствующий сбор данных
            if system_name == 'questions':
                system_feedback = await self._collect_questions_feedback(system_instance)
            elif system_name == 'debugging':
                system_feedback = await self._collect_debugging_feedback(system_instance)
            elif system_name == 'refactoring':
                system_feedback = await self._collect_refactoring_feedback(system_instance)
            elif system_name == 'monitoring':
                system_feedback = await self._collect_monitoring_feedback(system_instance)
            else:
                # Общий подход для неизвестных систем
                system_feedback = await self._collect_generic_system_feedback(system_name, system_instance)
        
        except Exception as e:
            system_feedback['status'] = 'error'
            system_feedback['error'] = str(e)
            self.logger.error(f"Failed to collect feedback from {system_name}: {str(e)}")
        
        return system_feedback
    
    async def _collect_questions_feedback(self, questions_system) -> Dict[str, Any]:
        """Сбор обратной связи от системы вопросов"""
        try:
            # Получение статистики одобрения
            stats = await questions_system.get_approval_statistics()
            pending = await questions_system.check_pending_approvals()
            
            feedback = {
                'system_name': 'questions',
                'status': 'operational',
                'metrics': {
                    'pending_approvals': pending.get('total_pending', 0),
                    'urgent_approvals': pending.get('urgent_approvals', 0),
                    'approval_rate': stats.get('approved_count', 0) / max(stats.get('pending_count', 1), 1),
                    'avg_review_time_hours': stats.get('average_review_time_hours', 0)
                },
                'issues': [],
                'recommendations': []
            }
            
            # Выявление проблем
            if pending.get('urgent_approvals', 0) > 5:
                feedback['issues'].append({
                    'severity': 'high',
                    'description': f"{pending['urgent_approvals']} questions need urgent approval",
                    'component': 'question_approval'
                })
            
            if stats.get('average_review_time_hours', 0) > 48:
                feedback['issues'].append({
                    'severity': 'medium',
                    'description': f"Average review time is {stats['average_review_time_hours']:.1f}h",
                    'component': 'review_process'
                })
            
            # Рекомендации
            if feedback['metrics']['approval_rate'] < 0.7:
                feedback['recommendations'].append({
                    'priority': 'medium',
                    'action': 'Improve question quality before submission',
                    'component': 'question_creation'
                })
            
            return feedback
            
        except Exception as e:
            return {
                'system_name': 'questions',
                'status': 'error',
                'error': str(e)
            }
    
    async def _collect_debugging_feedback(self, debugging_system) -> Dict[str, Any]:
        """Сбор обратной связи от системы отладки"""
        try:
            # Анализ эффективности отладки
            feedback = {
                'system_name': 'debugging',
                'status': 'operational',
                'metrics': {
                    'recent_fixes': 0,
                    'success_rate': 0.0,
                    'avg_resolution_time': 0.0,
                    'recurring_issues': 0
                },
                'issues': [],
                'recommendations': []
            }
            
            # Здесь будет интеграция с реальной системой отладки
            # Пока что базовые метрики
            
            return feedback
            
        except Exception as e:
            return {
                'system_name': 'debugging',
                'status': 'error',
                'error': str(e)
            }
    
    async def _collect_refactoring_feedback(self, refactoring_system) -> Dict[str, Any]:
        """Сбор обратной связи от системы рефакторинга"""
        try:
            feedback = {
                'system_name': 'refactoring',
                'status': 'operational',
                'metrics': {
                    'code_quality_score': 0.0,
                    'technical_debt_level': 'unknown',
                    'recent_refactorings': 0,
                    'performance_improvements': []
                },
                'issues': [],
                'recommendations': []
            }
            
            # Интеграция с системой рефакторинга будет добавлена
            
            return feedback
            
        except Exception as e:
            return {
                'system_name': 'refactoring', 
                'status': 'error',
                'error': str(e)
            }
    
    async def _collect_monitoring_feedback(self, monitoring_system) -> Dict[str, Any]:
        """Сбор обратной связи от системы мониторинга"""
        try:
            # Получение данных о здоровье системы
            health_overview = await monitoring_system.get_comprehensive_health_overview()
            
            feedback = {
                'system_name': 'monitoring',
                'status': 'operational',
                'metrics': {
                    'system_health_score': health_overview.get('overall_health_score', 0),
                    'active_alerts': len(health_overview.get('active_alerts', [])),
                    'components_monitored': len(health_overview.get('component_status', {})),
                    'uptime_percentage': health_overview.get('uptime_percentage', 100)
                },
                'issues': [],
                'recommendations': []
            }
            
            # Анализ проблем
            if health_overview.get('overall_health_score', 100) < 80:
                feedback['issues'].append({
                    'severity': 'high',
                    'description': f"System health score: {health_overview['overall_health_score']:.1f}%",
                    'component': 'system_health'
                })
            
            active_alerts = health_overview.get('active_alerts', [])
            for alert in active_alerts:
                if alert.get('severity') == 'critical':
                    feedback['issues'].append({
                        'severity': 'critical',
                        'description': alert.get('message', 'Critical alert active'),
                        'component': alert.get('component', 'unknown')
                    })
            
            return feedback
            
        except Exception as e:
            return {
                'system_name': 'monitoring',
                'status': 'error', 
                'error': str(e)
            }
    
    async def _collect_generic_system_feedback(self, system_name: str, system_instance: Any) -> Dict[str, Any]:
        """Общий сбор обратной связи от неопределенной системы"""
        feedback = {
            'system_name': system_name,
            'status': 'unknown',
            'metrics': {},
            'issues': [],
            'recommendations': []
        }
        
        try:
            # Попытка получить базовую информацию
            if hasattr(system_instance, 'get_status'):
                feedback['status'] = await system_instance.get_status()
            
            if hasattr(system_instance, 'get_metrics'):
                feedback['metrics'] = await system_instance.get_metrics()
            
            if hasattr(system_instance, 'get_health'):
                health = await system_instance.get_health()
                if health:
                    feedback['health'] = health
        
        except Exception as e:
            feedback['error'] = str(e)
        
        return feedback
    
    async def _collect_log_feedback(self) -> Dict[str, Any]:
        """Сбор обратной связи из логов"""
        log_feedback = {
            'recent_errors': [],
            'error_frequency': {},
            'warning_patterns': [],
            'performance_issues': []
        }
        
        try:
            # Анализ логов ошибок
            error_log_path = Path('logs/errors/errors.log')
            if error_log_path.exists():
                recent_errors = await self._analyze_recent_errors(error_log_path)
                log_feedback['recent_errors'] = recent_errors
                
                # Частота ошибок по типам
                error_freq = defaultdict(int)
                for error in recent_errors:
                    error_type = error.get('error_code', 'unknown')
                    error_freq[error_type] += 1
                
                log_feedback['error_frequency'] = dict(error_freq)
            
            # Анализ основного лога
            main_log_path = Path('logs/selfology.log')
            if main_log_path.exists():
                performance_issues = await self._analyze_performance_logs(main_log_path)
                log_feedback['performance_issues'] = performance_issues
        
        except Exception as e:
            log_feedback['error'] = str(e)
        
        return log_feedback
    
    async def _collect_performance_feedback(self) -> Dict[str, Any]:
        """Сбор обратной связи о производительности"""
        performance_feedback = {
            'current_metrics': {},
            'trends': {},
            'bottlenecks': [],
            'improvements': []
        }
        
        try:
            # Текущие метрики производительности
            import psutil
            
            performance_feedback['current_metrics'] = {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': (psutil.disk_usage('/').used / psutil.disk_usage('/').total) * 100,
                'process_count': len(psutil.pids())
            }
            
            # Анализ узких мест
            if performance_feedback['current_metrics']['cpu_percent'] > 80:
                performance_feedback['bottlenecks'].append({
                    'type': 'cpu',
                    'severity': 'high',
                    'value': performance_feedback['current_metrics']['cpu_percent'],
                    'description': 'High CPU usage detected'
                })
            
            if performance_feedback['current_metrics']['memory_percent'] > 85:
                performance_feedback['bottlenecks'].append({
                    'type': 'memory',
                    'severity': 'high',
                    'value': performance_feedback['current_metrics']['memory_percent'],
                    'description': 'High memory usage detected'
                })
        
        except Exception as e:
            performance_feedback['error'] = str(e)
        
        return performance_feedback
    
    async def _collect_user_interaction_feedback(self) -> Dict[str, Any]:
        """Сбор обратной связи о пользовательских взаимодействиях"""
        user_feedback = {
            'recent_sessions': [],
            'success_rates': {},
            'drop_off_points': {},
            'user_satisfaction_indicators': {}
        }
        
        try:
            # Анализ логов пользовательской активности
            user_log_path = Path('logs/users/user_activity.log')
            if user_log_path.exists():
                recent_sessions = await self._analyze_user_sessions(user_log_path)
                user_feedback['recent_sessions'] = recent_sessions
                
                # Расчет показателей успешности
                if recent_sessions:
                    completed_sessions = [s for s in recent_sessions if s.get('completed', False)]
                    user_feedback['success_rates'] = {
                        'completion_rate': len(completed_sessions) / len(recent_sessions),
                        'avg_session_duration': sum(s.get('duration_minutes', 0) for s in recent_sessions) / len(recent_sessions)
                    }
        
        except Exception as e:
            user_feedback['error'] = str(e)
        
        return user_feedback
    
    async def _analyze_recent_errors(self, error_log_path: Path, hours: int = 24) -> List[Dict[str, Any]]:
        """Анализ недавних ошибок из логов"""
        errors = []
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        try:
            with open(error_log_path, 'r') as f:
                lines = f.readlines()[-200:]  # Последние 200 строк
            
            for line in lines:
                try:
                    if line.strip():
                        # Простой парсинг строки лога
                        parts = line.strip().split(' ', 3)
                        if len(parts) >= 4:
                            timestamp_str = f"{parts[0]} {parts[1]}"
                            level = parts[2]
                            message = parts[3]
                            
                            # Попытка парсинга времени
                            try:
                                log_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                                if log_time > cutoff_time:
                                    errors.append({
                                        'timestamp': timestamp_str,
                                        'level': level,
                                        'message': message,
                                        'error_code': self._extract_error_code(message)
                                    })
                            except:
                                pass
                except:
                    continue
        
        except Exception as e:
            self.logger.error(f"Failed to analyze recent errors: {str(e)}")
        
        return errors[-50:]  # Последние 50 ошибок
    
    def _extract_error_code(self, message: str) -> str:
        """Извлечение кода ошибки из сообщения"""
        import re
        
        # Поиск паттернов кодов ошибок
        patterns = [
            r'(BOT_\d{3})', r'(USER_\d{3})', r'(AI_\d{3})',
            r'(DB_\d{3})', r'(VDB_\d{3})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message)
            if match:
                return match.group(1)
        
        return 'UNKNOWN'
    
    async def _analyze_performance_logs(self, log_path: Path) -> List[Dict[str, Any]]:
        """Анализ проблем производительности из логов"""
        performance_issues = []
        
        try:
            with open(log_path, 'r') as f:
                lines = f.readlines()[-100:]  # Последние 100 строк
            
            for line in lines:
                if 'slow' in line.lower() or 'timeout' in line.lower():
                    performance_issues.append({
                        'type': 'performance',
                        'description': line.strip()[:200],  # Первые 200 символов
                        'severity': 'medium'
                    })
        
        except Exception as e:
            self.logger.error(f"Failed to analyze performance logs: {str(e)}")
        
        return performance_issues[-10:]  # Последние 10 проблем
    
    async def _analyze_user_sessions(self, user_log_path: Path) -> List[Dict[str, Any]]:
        """Анализ пользовательских сессий"""
        sessions = []
        
        try:
            with open(user_log_path, 'r') as f:
                lines = f.readlines()[-500:]  # Последние 500 строк
            
            # Группировка по пользователям/сессиям
            user_activities = defaultdict(list)
            
            for line in lines:
                try:
                    # Попытка извлечь данные пользователя из лога
                    if 'user' in line.lower():
                        # Простое извлечение ID пользователя
                        import re
                        user_match = re.search(r'user[_\s]*(\d+)', line, re.IGNORECASE)
                        if user_match:
                            user_id = user_match.group(1)
                            user_activities[user_id].append(line.strip())
                except:
                    continue
            
            # Анализ сессий по пользователям
            for user_id, activities in user_activities.items():
                if activities:
                    sessions.append({
                        'user_id': user_id,
                        'activity_count': len(activities),
                        'completed': 'completion' in ' '.join(activities).lower(),
                        'duration_minutes': len(activities) * 2  # Примерная оценка
                    })
        
        except Exception as e:
            self.logger.error(f"Failed to analyze user sessions: {str(e)}")
        
        return sessions[-20:]  # Последние 20 сессий
    
    def _extract_critical_issues(self, system_feedback: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Извлечение критических проблем из обратной связи"""
        critical_issues = []
        
        # Проблемы с высокой серьезностью
        for issue in system_feedback.get('issues', []):
            if issue.get('severity') in ['critical', 'high']:
                critical_issues.append({
                    'source': system_feedback.get('system_name', 'unknown'),
                    'severity': issue.get('severity'),
                    'description': issue.get('description'),
                    'component': issue.get('component'),
                    'timestamp': datetime.now().isoformat()
                })
        
        return critical_issues
    
    def _generate_feedback_summary(self, comprehensive_feedback: Dict[str, Any]) -> Dict[str, Any]:
        """Генерация сводки обратной связи"""
        summary = {
            'total_systems_checked': len(comprehensive_feedback.get('system_feedback', {})),
            'critical_issues_count': len(comprehensive_feedback.get('critical_issues', [])),
            'systems_with_errors': 0,
            'overall_health_indicator': 'unknown',
            'top_concerns': []
        }
        
        # Подсчет систем с ошибками
        for system_name, system_data in comprehensive_feedback.get('system_feedback', {}).items():
            if system_data.get('status') == 'error':
                summary['systems_with_errors'] += 1
        
        # Определение общего состояния здоровья
        if summary['critical_issues_count'] == 0 and summary['systems_with_errors'] == 0:
            summary['overall_health_indicator'] = 'healthy'
        elif summary['critical_issues_count'] <= 2 and summary['systems_with_errors'] <= 1:
            summary['overall_health_indicator'] = 'warning'
        else:
            summary['overall_health_indicator'] = 'critical'
        
        # Топ проблем
        all_issues = comprehensive_feedback.get('critical_issues', [])
        severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        
        sorted_issues = sorted(all_issues, key=lambda x: severity_order.get(x.get('severity', 'low'), 4))
        summary['top_concerns'] = sorted_issues[:5]  # Топ 5 проблем
        
        return summary
    
    async def _detect_feedback_patterns(self, comprehensive_feedback: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Обнаружение паттернов в обратной связи"""
        patterns = []
        
        try:
            # Анализ повторяющихся ошибок
            error_feedback = comprehensive_feedback.get('system_feedback', {}).get('logs', {})
            error_frequency = error_feedback.get('error_frequency', {})
            
            for error_code, frequency in error_frequency.items():
                if frequency >= 3:  # 3+ одинаковых ошибки
                    patterns.append({
                        'pattern_type': 'recurring_error',
                        'description': f'Recurring {error_code} error ({frequency} times)',
                        'frequency': frequency,
                        'confidence': min(0.9, frequency / 10),
                        'suggested_action': f'Investigate root cause of {error_code}'
                    })
            
            # Анализ производительности
            perf_feedback = comprehensive_feedback.get('system_feedback', {}).get('performance', {})
            bottlenecks = perf_feedback.get('bottlenecks', [])
            
            if len(bottlenecks) >= 2:
                patterns.append({
                    'pattern_type': 'performance_degradation',
                    'description': f'Multiple performance bottlenecks detected ({len(bottlenecks)})',
                    'bottlenecks': bottlenecks,
                    'confidence': 0.8,
                    'suggested_action': 'Performance optimization needed'
                })
            
            # Анализ пользовательского поведения
            user_feedback = comprehensive_feedback.get('system_feedback', {}).get('user_interactions', {})
            success_rates = user_feedback.get('success_rates', {})
            completion_rate = success_rates.get('completion_rate', 1.0)
            
            if completion_rate < 0.7:  # Менее 70% завершений
                patterns.append({
                    'pattern_type': 'user_experience_issue',
                    'description': f'Low completion rate: {completion_rate:.1%}',
                    'completion_rate': completion_rate,
                    'confidence': 0.7,
                    'suggested_action': 'Investigate user flow bottlenecks'
                })
        
        except Exception as e:
            self.logger.error(f"Failed to detect feedback patterns: {str(e)}")
        
        return patterns
    
    async def _save_feedback_to_db(self, feedback_entry: FeedbackEntry):
        """Сохранение обратной связи в базу данных"""
        try:
            conn = sqlite3.connect(self.feedback_db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO system_feedback 
                (feedback_id, feedback_type, priority, source_component, data)
                VALUES (?, ?, ?, ?, ?)
            """, (
                feedback_entry.feedback_id,
                feedback_entry.feedback_type.value,
                feedback_entry.priority.value,
                feedback_entry.source_component,
                json.dumps(feedback_entry.data, default=str)
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Failed to save feedback to DB: {str(e)}")
    
    async def _trigger_feedback_handlers(self, feedback_entry: FeedbackEntry):
        """Запуск обработчиков для обратной связи"""
        handlers = self.feedback_handlers.get(feedback_entry.feedback_type, [])
        
        for handler in handlers:
            try:
                await handler(feedback_entry)
            except Exception as e:
                self.logger.error(f"Feedback handler failed: {str(e)}")
    
    async def _analyze_feedback_patterns(self, feedback_entry: FeedbackEntry):
        """Анализ паттернов в поступающей обратной связи"""
        try:
            # Поиск похожих записей обратной связи
            similar_feedback = await self._find_similar_feedback(feedback_entry)
            
            if len(similar_feedback) >= 3:  # Паттерн из 3+ похожих записей
                pattern_id = f"pattern_{feedback_entry.feedback_type.value}_{feedback_entry.source_component}"
                await self._update_or_create_pattern(pattern_id, feedback_entry, similar_feedback)
        
        except Exception as e:
            self.logger.error(f"Failed to analyze feedback patterns: {str(e)}")
    
    async def _find_similar_feedback(self, target_feedback: FeedbackEntry, 
                                   similarity_threshold: float = 0.6) -> List[FeedbackEntry]:
        """Поиск похожей обратной связи"""
        similar = []
        
        try:
            # Поиск в недавней обратной связи
            for feedback in self.feedback_queue:
                if (feedback.feedback_type == target_feedback.feedback_type and
                    feedback.source_component == target_feedback.source_component):
                    
                    # Простая проверка схожести данных
                    similarity = self._calculate_data_similarity(
                        target_feedback.data, feedback.data
                    )
                    
                    if similarity >= similarity_threshold:
                        similar.append(feedback)
        
        except Exception as e:
            self.logger.error(f"Failed to find similar feedback: {str(e)}")
        
        return similar
    
    def _calculate_data_similarity(self, data1: Dict[str, Any], data2: Dict[str, Any]) -> float:
        """Вычисление схожести данных обратной связи"""
        try:
            # Простая метрика схожести на основе общих ключей
            keys1 = set(data1.keys())
            keys2 = set(data2.keys())
            
            if not keys1 and not keys2:
                return 1.0
            
            common_keys = keys1 & keys2
            all_keys = keys1 | keys2
            
            if not all_keys:
                return 0.0
            
            key_similarity = len(common_keys) / len(all_keys)
            
            # Схожесть значений для общих ключей
            value_similarity = 0.0
            if common_keys:
                matching_values = 0
                for key in common_keys:
                    if data1[key] == data2[key]:
                        matching_values += 1
                value_similarity = matching_values / len(common_keys)
            
            # Общая схожесть
            return (key_similarity + value_similarity) / 2
        
        except Exception:
            return 0.0
    
    async def _update_or_create_pattern(self, pattern_id: str, feedback_entry: FeedbackEntry, 
                                      similar_feedback: List[FeedbackEntry]):
        """Обновление или создание паттерна обратной связи"""
        try:
            conn = sqlite3.connect(self.feedback_db_path)
            cursor = conn.cursor()
            
            # Проверка существования паттерна
            cursor.execute("""
                SELECT occurrence_count, confidence_score FROM feedback_patterns 
                WHERE pattern_id = ?
            """, (pattern_id,))
            
            result = cursor.fetchone()
            
            if result:
                # Обновление существующего паттерна
                new_count = result[0] + 1
                new_confidence = min(0.95, result[1] + 0.1)  # Увеличение уверенности
                
                cursor.execute("""
                    UPDATE feedback_patterns 
                    SET occurrence_count = ?, confidence_score = ?, last_seen = CURRENT_TIMESTAMP
                    WHERE pattern_id = ?
                """, (new_count, new_confidence, pattern_id))
                
            else:
                # Создание нового паттерна
                pattern_data = {
                    'feedback_type': feedback_entry.feedback_type.value,
                    'source_component': feedback_entry.source_component,
                    'common_elements': self._extract_common_elements(similar_feedback),
                    'frequency': len(similar_feedback) + 1
                }
                
                cursor.execute("""
                    INSERT INTO feedback_patterns 
                    (pattern_id, pattern_type, pattern_data, occurrence_count)
                    VALUES (?, ?, ?, ?)
                """, (
                    pattern_id,
                    feedback_entry.feedback_type.value,
                    json.dumps(pattern_data, default=str),
                    len(similar_feedback) + 1
                ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Failed to update/create pattern: {str(e)}")
    
    def _extract_common_elements(self, feedback_list: List[FeedbackEntry]) -> Dict[str, Any]:
        """Извлечение общих элементов из списка обратной связи"""
        common_elements = {}
        
        if not feedback_list:
            return common_elements
        
        # Анализ общих ключей в данных
        all_keys = set()
        for feedback in feedback_list:
            all_keys.update(feedback.data.keys())
        
        for key in all_keys:
            values = [feedback.data.get(key) for feedback in feedback_list if key in feedback.data]
            
            # Если все значения одинаковые, это общий элемент
            if len(set(str(v) for v in values)) == 1:
                common_elements[key] = values[0]
        
        return common_elements
    
    async def process_chat_feedback(self, user_id: int, session_id: str, 
                                  feedback_type: str, feedback_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обработка обратной связи от взаимодействия с чатом
        
        Args:
            user_id: ID пользователя
            session_id: ID сессии чата  
            feedback_type: Тип обратной связи
            feedback_data: Данные обратной связи
        
        Returns:
            Результат обработки обратной связи
        """
        try:
            # Определение типа обратной связи
            fb_type = FeedbackType.USER_INTERACTION
            if feedback_type == 'error':
                fb_type = FeedbackType.ERROR_REPORT
            elif feedback_type == 'performance':
                fb_type = FeedbackType.SYSTEM_PERFORMANCE
            elif feedback_type == 'ai_behavior':
                fb_type = FeedbackType.AI_BEHAVIOR
            
            # Определение приоритета
            priority = FeedbackPriority.MEDIUM
            if feedback_data.get('severity') == 'critical':
                priority = FeedbackPriority.CRITICAL
            elif feedback_data.get('severity') == 'high':
                priority = FeedbackPriority.HIGH
            
            # Добавление контекста
            enhanced_data = {
                **feedback_data,
                'user_id': user_id,
                'session_id': session_id,
                'chat_context': True,
                'timestamp': datetime.now().isoformat()
            }
            
            # Сбор обратной связи
            feedback_id = await self.collect_feedback(
                fb_type, 'chat_interface', enhanced_data, priority
            )
            
            return {
                'success': True,
                'feedback_id': feedback_id,
                'processed_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to process chat feedback: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_recent_feedback(self, hours: int = 24, 
                                feedback_types: List[FeedbackType] = None) -> List[Dict[str, Any]]:
        """Получение недавней обратной связи"""
        try:
            conn = sqlite3.connect(self.feedback_db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = """
                SELECT * FROM system_feedback 
                WHERE timestamp > datetime('now', '-{} hours')
            """.format(hours)
            
            params = []
            
            if feedback_types:
                placeholders = ','.join(['?' for _ in feedback_types])
                query += f" AND feedback_type IN ({placeholders})"
                params.extend([ft.value for ft in feedback_types])
            
            query += " ORDER BY timestamp DESC LIMIT 100"
            
            cursor.execute(query, params)
            
            feedback_records = []
            for row in cursor.fetchall():
                record = dict(row)
                record['data'] = json.loads(record['data'])
                feedback_records.append(record)
            
            conn.close()
            return feedback_records
            
        except Exception as e:
            self.logger.error(f"Failed to get recent feedback: {str(e)}")
            return []
    
    async def get_feedback_summary(self, days: int = 7) -> Dict[str, Any]:
        """Получение сводки обратной связи за период"""
        try:
            conn = sqlite3.connect(self.feedback_db_path)
            cursor = conn.cursor()
            
            # Статистика по типам
            cursor.execute("""
                SELECT feedback_type, COUNT(*) as count
                FROM system_feedback 
                WHERE timestamp > datetime('now', '-{} days')
                GROUP BY feedback_type
            """.format(days))
            
            type_stats = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Статистика по приоритетам
            cursor.execute("""
                SELECT priority, COUNT(*) as count
                FROM system_feedback 
                WHERE timestamp > datetime('now', '-{} days')
                GROUP BY priority
            """.format(days))
            
            priority_stats = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Статистика по источникам
            cursor.execute("""
                SELECT source_component, COUNT(*) as count
                FROM system_feedback 
                WHERE timestamp > datetime('now', '-{} days')
                GROUP BY source_component
            """.format(days))
            
            source_stats = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Недавняя обратная связь
            recent_feedback = await self.get_recent_feedback(24)
            
            conn.close()
            
            return {
                'period_days': days,
                'type_distribution': type_stats,
                'priority_distribution': priority_stats,
                'source_distribution': source_stats,
                'total_feedback_items': sum(type_stats.values()),
                'recent_feedback': recent_feedback[:10],  # Последние 10
                'summary_generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get feedback summary: {str(e)}")
            return {}


# CLI для управления системой обратной связи
async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="System Feedback Collector CLI")
    parser.add_argument('action', choices=['collect', 'summary', 'recent', 'patterns'])
    parser.add_argument('--hours', type=int, default=24, help='Hours for recent feedback')
    parser.add_argument('--days', type=int, default=7, help='Days for summary')
    
    args = parser.parse_args()
    
    collector = SystemFeedbackCollector()
    
    if args.action == 'collect':
        feedback = await collector.collect_comprehensive_feedback()
        print(f"\n📊 COMPREHENSIVE FEEDBACK COLLECTED:")
        print(f"Systems checked: {feedback['summary']['total_systems_checked']}")
        print(f"Critical issues: {feedback['summary']['critical_issues_count']}")
        print(f"Overall health: {feedback['summary']['overall_health_indicator']}")
        
    elif args.action == 'summary':
        summary = await collector.get_feedback_summary(args.days)
        print(f"\n📈 FEEDBACK SUMMARY ({args.days} days):")
        print(f"Total items: {summary.get('total_feedback_items', 0)}")
        print(f"By priority: {summary.get('priority_distribution', {})}")
        print(f"By type: {summary.get('type_distribution', {})}")
        
    elif args.action == 'recent':
        recent = await collector.get_recent_feedback(args.hours)
        print(f"\n🕒 RECENT FEEDBACK ({args.hours}h):")
        for item in recent[:10]:
            print(f"[{item['priority'].upper()}] {item['source_component']}: {item['feedback_type']}")
            
    elif args.action == 'patterns':
        # Показать обнаруженные паттерны
        conn = sqlite3.connect(collector.feedback_db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT pattern_id, pattern_type, occurrence_count, confidence_score
            FROM feedback_patterns 
            ORDER BY occurrence_count DESC, confidence_score DESC
            LIMIT 10
        """)
        
        patterns = cursor.fetchall()
        conn.close()
        
        print(f"\n🔍 DETECTED PATTERNS:")
        for pattern in patterns:
            print(f"Pattern: {pattern[0]}")
            print(f"  Type: {pattern[1]}")  
            print(f"  Occurrences: {pattern[2]}")
            print(f"  Confidence: {pattern[3]:.2f}")
            print()


if __name__ == "__main__":
    asyncio.run(main())