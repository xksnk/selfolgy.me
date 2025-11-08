"""
🧠 Debug Learning Engine - Обучающаяся система отладки
Анализирует паттерны проблем, обучается на ошибках и улучшает процессы отладки.
"""

import asyncio
import json
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict, Counter
import sqlite3
import logging
from dataclasses import dataclass
from enum import Enum
import statistics


class ProblemType(Enum):
    """Типы проблем в системе"""
    SYSTEM_CRASH = "system_crash"
    PERFORMANCE = "performance"
    AI_ROUTING = "ai_routing"
    DATABASE = "database"
    USER_FLOW = "user_flow"
    QUESTION_LOGIC = "question_logic"
    INTEGRATION = "integration"
    SECURITY = "security"


class LearningConfidence(Enum):
    """Уровни уверенности в обучении"""
    LOW = "low"           # < 3 похожих случая
    MEDIUM = "medium"     # 3-10 случаев
    HIGH = "high"         # 10+ случаев
    EXPERT = "expert"     # 50+ случаев с высокой точностью


@dataclass
class ProblemPattern:
    """Паттерн проблемы для обучения"""
    pattern_id: str
    problem_type: ProblemType
    symptoms: List[str]
    root_causes: List[str]
    solutions: List[str]
    success_rate: float
    confidence: LearningConfidence
    seen_count: int
    last_seen: datetime
    context_fingerprint: str  # Хеш контекста для похожих проблем


@dataclass
class LearningInsight:
    """Инсайт полученный в результате обучения"""
    insight_id: str
    insight_type: str
    description: str
    pattern_ids: List[str]
    confidence_score: float
    actionable_recommendations: List[str]
    learned_from_cases: int


class DebugLearningEngine:
    """
    🎯 Обучающаяся система отладки
    
    Основные функции:
    - Анализ паттернов проблем и решений
    - Обучение на исторических данных
    - Предсказание проблем до их возникновения  
    - Генерация умных рекомендаций
    - Адаптация к специфике Selfology системы
    """
    
    def __init__(self):
        self.learning_db_path = Path('data/debug_learning.db')
        self.learning_db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.patterns_file = Path('data/learned_patterns.pkl')
        self.insights_file = Path('data/learning_insights.pkl')
        
        # Инициализация базы данных обучения
        self._setup_learning_database()
        
        # Загрузка обученных паттернов
        self.learned_patterns: Dict[str, ProblemPattern] = {}
        self.learning_insights: List[LearningInsight] = []
        
        # Загрузка будет выполнена при первом использовании
        self._data_loaded = False
        
        # Подключенный отладчик для применения знаний
        self.connected_debugger = None
        
        # Настройки обучения
        self.min_pattern_threshold = 3  # Минимум случаев для паттерна
        self.confidence_threshold = 0.7  # Минимум уверенности для применения
        
        self.logger = logging.getLogger(__name__)
    
    def _setup_learning_database(self):
        """Настройка базы данных для хранения данных обучения"""
        conn = sqlite3.connect(self.learning_db_path)
        cursor = conn.cursor()
        
        # Таблица инцидентов для обучения
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS debug_incidents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                incident_id TEXT UNIQUE NOT NULL,
                problem_type TEXT NOT NULL,
                symptoms TEXT NOT NULL,  -- JSON список симптомов
                root_cause TEXT,
                solution_applied TEXT,
                success BOOLEAN,
                context_data TEXT,  -- JSON с контекстом проблемы
                system_state TEXT,  -- JSON состояния системы
                resolution_time_minutes INTEGER,
                occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP,
                learned_from BOOLEAN DEFAULT FALSE
            )
        """)
        
        # Таблица обученных паттернов
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learned_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_id TEXT UNIQUE NOT NULL,
                problem_type TEXT NOT NULL,
                pattern_data TEXT NOT NULL,  -- JSON сериализованный паттерн
                confidence_score REAL,
                success_rate REAL,
                times_applied INTEGER DEFAULT 0,
                successful_applications INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблица применения паттернов (для обратной связи)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pattern_applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_id TEXT NOT NULL,
                incident_id TEXT NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                success BOOLEAN,
                feedback TEXT,
                improvement_suggestions TEXT,
                FOREIGN KEY (pattern_id) REFERENCES learned_patterns (pattern_id),
                FOREIGN KEY (incident_id) REFERENCES debug_incidents (incident_id)
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_problem_type ON debug_incidents(problem_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_occurred_at ON debug_incidents(occurred_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_pattern_type ON learned_patterns(problem_type)")
        
        conn.commit()
        conn.close()
    
    def connect_debugger(self, debugger):
        """Подключение отладчика для применения обученных знаний"""
        self.connected_debugger = debugger
        self.logger.info("Debug learning engine connected to surgical debugger")
    
    async def record_debug_incident(self, incident_data: Dict[str, Any]) -> str:
        """
        Запись инцидента для обучения
        
        Args:
            incident_data: Данные об инциденте (симптомы, решение, результат)
        
        Returns:
            ID записанного инцидента
        """
        try:
            incident_id = f"incident_{int(datetime.now().timestamp())}_{incident_data.get('problem_type', 'unknown')}"
            
            conn = sqlite3.connect(self.learning_db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO debug_incidents 
                (incident_id, problem_type, symptoms, root_cause, solution_applied, 
                 success, context_data, system_state, resolution_time_minutes, resolved_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                incident_id,
                incident_data.get('problem_type'),
                json.dumps(incident_data.get('symptoms', [])),
                incident_data.get('root_cause'),
                incident_data.get('solution_applied'),
                incident_data.get('success', False),
                json.dumps(incident_data.get('context_data', {})),
                json.dumps(incident_data.get('system_state', {})),
                incident_data.get('resolution_time_minutes'),
                datetime.now().isoformat() if incident_data.get('success') else None
            ))
            
            conn.commit()
            conn.close()
            
            # Запуск обучения на новом инциденте
            await self._trigger_incremental_learning(incident_id)
            
            self.logger.info(f"Recorded debug incident: {incident_id}")
            return incident_id
            
        except Exception as e:
            self.logger.error(f"Failed to record debug incident: {str(e)}")
            return ""
    
    async def process_feedback_and_learn(self, feedback_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обработка обратной связи и обучение на ней
        
        Args:
            feedback_data: Собранная обратная связь от всех систем
        
        Returns:
            Результаты обучения и новые инсайты
        """
        learning_results = {
            'timestamp': datetime.now().isoformat(),
            'feedback_processed': len(feedback_data.get('system_feedback', {})),
            'new_patterns_discovered': [],
            'updated_patterns': [],
            'new_insights': [],
            'confidence_improvements': [],
            'predictive_alerts': []
        }
        
        try:
            # Обработка системной обратной связи
            system_feedback = feedback_data.get('system_feedback', {})
            
            # Анализ мониторинга
            monitoring_data = system_feedback.get('monitoring', {})
            if monitoring_data:
                patterns = await self._analyze_monitoring_patterns(monitoring_data)
                learning_results['new_patterns_discovered'].extend(patterns)
            
            # Анализ ошибок
            error_data = system_feedback.get('errors', {})
            if error_data:
                error_patterns = await self._analyze_error_patterns(error_data)
                learning_results['new_patterns_discovered'].extend(error_patterns)
            
            # Анализ пользовательского поведения
            user_data = system_feedback.get('user_interactions', {})
            if user_data:
                user_patterns = await self._analyze_user_patterns(user_data)
                learning_results['new_patterns_discovered'].extend(user_patterns)
            
            # Обучение на исторических данных
            historical_learning = await self._learn_from_historical_incidents()
            learning_results['updated_patterns'].extend(historical_learning.get('updated_patterns', []))
            
            # Генерация новых инсайтов
            new_insights = await self._generate_learning_insights()
            learning_results['new_insights'] = new_insights
            
            # Обновление уверенности в существующих паттернах
            confidence_updates = await self._update_pattern_confidence()
            learning_results['confidence_improvements'] = confidence_updates
            
            # Предсказательная аналитика
            predictions = await self._generate_predictive_alerts()
            learning_results['predictive_alerts'] = predictions
            
            # Сохранение обученных данных
            await self._save_learned_data()
            
            self.logger.info(f"Learning cycle completed: {len(learning_results['new_patterns_discovered'])} new patterns")
            
        except Exception as e:
            self.logger.error(f"Failed to process feedback and learn: {str(e)}")
            learning_results['error'] = str(e)
        
        return learning_results
    
    async def _analyze_monitoring_patterns(self, monitoring_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Анализ паттернов в данных мониторинга"""
        patterns = []
        
        try:
            # Анализ паттернов производительности
            performance_metrics = monitoring_data.get('performance_metrics', {})
            
            # Паттерн: высокая нагрузка на CPU перед сбоями
            cpu_usage = performance_metrics.get('cpu_usage_history', [])
            if len(cpu_usage) > 5:
                high_cpu_before_issues = []
                for i in range(len(cpu_usage) - 1):
                    if cpu_usage[i] > 80 and monitoring_data.get('issues_reported', 0) > 0:
                        high_cpu_before_issues.append(cpu_usage[i])
                
                if len(high_cpu_before_issues) >= 3:
                    patterns.append({
                        'pattern_type': 'performance_degradation',
                        'symptoms': ['high_cpu_usage', 'system_slowdown'],
                        'confidence': 0.8,
                        'description': 'High CPU usage typically precedes system issues'
                    })
            
            # Паттерн: ошибки в определенное время дня
            error_times = monitoring_data.get('error_timestamps', [])
            if error_times:
                hour_distribution = defaultdict(int)
                for timestamp in error_times:
                    try:
                        dt = datetime.fromisoformat(timestamp)
                        hour_distribution[dt.hour] += 1
                    except:
                        continue
                
                if hour_distribution:
                    peak_hour = max(hour_distribution.items(), key=lambda x: x[1])
                    if peak_hour[1] > 3:  # Более 3 ошибок в один час
                        patterns.append({
                            'pattern_type': 'temporal_error_pattern',
                            'symptoms': ['recurring_errors', f'peak_at_hour_{peak_hour[0]}'],
                            'confidence': 0.7,
                            'description': f'Errors spike at hour {peak_hour[0]} - likely resource contention'
                        })
        
        except Exception as e:
            self.logger.error(f"Failed to analyze monitoring patterns: {str(e)}")
        
        return patterns
    
    async def _analyze_error_patterns(self, error_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Анализ паттернов в ошибках"""
        patterns = []
        
        try:
            recent_errors = error_data.get('recent_errors', [])
            
            # Группировка ошибок по типам
            error_types = defaultdict(list)
            for error in recent_errors:
                error_type = error.get('error_code', 'unknown')
                error_types[error_type].append(error)
            
            # Поиск повторяющихся паттернов
            for error_type, errors in error_types.items():
                if len(errors) >= 3:  # Минимум 3 похожих ошибки
                    # Анализ контекста ошибок
                    contexts = [error.get('context', {}) for error in errors]
                    
                    # Поиск общих элементов в контексте
                    common_context = {}
                    if contexts:
                        first_context = contexts[0]
                        for key, value in first_context.items():
                            if all(ctx.get(key) == value for ctx in contexts[1:]):
                                common_context[key] = value
                    
                    patterns.append({
                        'pattern_type': 'recurring_error',
                        'error_code': error_type,
                        'symptoms': [f'error_code_{error_type}', 'multiple_occurrences'],
                        'frequency': len(errors),
                        'common_context': common_context,
                        'confidence': min(0.9, len(errors) / 10),
                        'description': f'Recurring {error_type} error with similar context'
                    })
        
        except Exception as e:
            self.logger.error(f"Failed to analyze error patterns: {str(e)}")
        
        return patterns
    
    async def _analyze_user_patterns(self, user_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Анализ паттернов пользовательского поведения"""
        patterns = []
        
        try:
            user_sessions = user_data.get('sessions', [])
            
            # Анализ точек отказа в пользовательском потоке
            drop_off_points = defaultdict(int)
            successful_completions = 0
            
            for session in user_sessions:
                user_flow = session.get('flow_steps', [])
                if user_flow:
                    last_step = user_flow[-1]
                    if last_step == 'completion':
                        successful_completions += 1
                    else:
                        drop_off_points[last_step] += 1
            
            # Выявление критических точек отказа
            total_sessions = len(user_sessions)
            if total_sessions > 10:  # Достаточно данных для анализа
                for step, drop_offs in drop_off_points.items():
                    drop_off_rate = drop_offs / total_sessions
                    if drop_off_rate > 0.3:  # >30% отказов на этом шаге
                        patterns.append({
                            'pattern_type': 'user_flow_bottleneck',
                            'symptoms': [f'high_dropoff_at_{step}', 'user_abandonment'],
                            'drop_off_rate': drop_off_rate,
                            'affected_step': step,
                            'confidence': 0.8,
                            'description': f'High user drop-off at step: {step} ({drop_off_rate:.1%})'
                        })
        
        except Exception as e:
            self.logger.error(f"Failed to analyze user patterns: {str(e)}")
        
        return patterns
    
    async def _learn_from_historical_incidents(self) -> Dict[str, Any]:
        """Обучение на исторических инцидентах"""
        learning_results = {
            'updated_patterns': [],
            'new_correlations': []
        }
        
        try:
            conn = sqlite3.connect(self.learning_db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Получение неизученных инцидентов
            cursor.execute("""
                SELECT * FROM debug_incidents 
                WHERE learned_from = FALSE AND success IS NOT NULL
                ORDER BY occurred_at DESC
                LIMIT 50
            """)
            
            unlearned_incidents = cursor.fetchall()
            
            for incident in unlearned_incidents:
                incident_dict = dict(incident)
                
                # Попытка найти похожие инциденты
                similar_incidents = await self._find_similar_incidents(incident_dict)
                
                if len(similar_incidents) >= self.min_pattern_threshold:
                    # Создание или обновление паттерна
                    pattern = await self._create_or_update_pattern(incident_dict, similar_incidents)
                    if pattern:
                        learning_results['updated_patterns'].append(pattern)
                
                # Отметка как изученный
                cursor.execute("""
                    UPDATE debug_incidents SET learned_from = TRUE WHERE id = ?
                """, (incident['id'],))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Failed to learn from historical incidents: {str(e)}")
        
        return learning_results
    
    async def _find_similar_incidents(self, target_incident: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Поиск похожих инцидентов для создания паттернов"""
        similar_incidents = []
        
        try:
            conn = sqlite3.connect(self.learning_db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Поиск инцидентов того же типа
            cursor.execute("""
                SELECT * FROM debug_incidents 
                WHERE problem_type = ? AND id != ?
                ORDER BY occurred_at DESC
                LIMIT 20
            """, (target_incident['problem_type'], target_incident.get('id', -1)))
            
            candidates = cursor.fetchall()
            
            # Анализ схожести по симптомам
            target_symptoms = set(json.loads(target_incident.get('symptoms', '[]')))
            
            for candidate in candidates:
                candidate_dict = dict(candidate)
                candidate_symptoms = set(json.loads(candidate_dict.get('symptoms', '[]')))
                
                # Вычисление схожести (коэффициент Жаккара)
                intersection = len(target_symptoms & candidate_symptoms)
                union = len(target_symptoms | candidate_symptoms)
                
                if union > 0:
                    similarity = intersection / union
                    if similarity > 0.5:  # 50% схожести
                        candidate_dict['similarity_score'] = similarity
                        similar_incidents.append(candidate_dict)
            
            conn.close()
            
            # Сортировка по схожести
            similar_incidents.sort(key=lambda x: x.get('similarity_score', 0), reverse=True)
            
        except Exception as e:
            self.logger.error(f"Failed to find similar incidents: {str(e)}")
        
        return similar_incidents
    
    async def _create_or_update_pattern(self, incident: Dict[str, Any], 
                                      similar_incidents: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Создание или обновление паттерна на основе инцидентов"""
        try:
            # Извлечение общих характеристик
            all_incidents = [incident] + similar_incidents
            
            # Общие симптомы
            all_symptoms = []
            for inc in all_incidents:
                symptoms = json.loads(inc.get('symptoms', '[]'))
                all_symptoms.extend(symptoms)
            
            common_symptoms = [symptom for symptom, count in Counter(all_symptoms).items() 
                             if count >= len(all_incidents) * 0.5]  # Встречается в >50% случаев
            
            # Анализ решений
            successful_solutions = []
            for inc in all_incidents:
                if inc.get('success'):
                    solution = inc.get('solution_applied')
                    if solution:
                        successful_solutions.append(solution)
            
            # Вычисление успешности
            success_rate = len([inc for inc in all_incidents if inc.get('success')]) / len(all_incidents)
            
            # Определение уверенности
            confidence = LearningConfidence.LOW
            if len(all_incidents) >= 10:
                confidence = LearningConfidence.MEDIUM
            if len(all_incidents) >= 25:
                confidence = LearningConfidence.HIGH
            if len(all_incidents) >= 50 and success_rate > 0.8:
                confidence = LearningConfidence.EXPERT
            
            # Создание паттерна
            pattern_id = f"pattern_{incident['problem_type']}_{int(datetime.now().timestamp())}"
            
            pattern = ProblemPattern(
                pattern_id=pattern_id,
                problem_type=ProblemType(incident['problem_type']),
                symptoms=common_symptoms,
                root_causes=[inc.get('root_cause', '') for inc in all_incidents if inc.get('root_cause')],
                solutions=list(set(successful_solutions)),
                success_rate=success_rate,
                confidence=confidence,
                seen_count=len(all_incidents),
                last_seen=datetime.now(),
                context_fingerprint=self._generate_context_fingerprint(all_incidents)
            )
            
            # Сохранение паттерна
            self.learned_patterns[pattern_id] = pattern
            await self._save_pattern_to_db(pattern)
            
            return {
                'pattern_id': pattern_id,
                'problem_type': incident['problem_type'],
                'confidence': confidence.value,
                'success_rate': success_rate,
                'incident_count': len(all_incidents)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create/update pattern: {str(e)}")
            return None
    
    def _generate_context_fingerprint(self, incidents: List[Dict[str, Any]]) -> str:
        """Генерация отпечатка контекста для группировки похожих проблем"""
        try:
            # Извлечение ключевых элементов контекста
            context_elements = []
            
            for incident in incidents:
                context_data = json.loads(incident.get('context_data', '{}'))
                system_state = json.loads(incident.get('system_state', '{}'))
                
                # Ключевые элементы контекста
                elements = [
                    context_data.get('component', 'unknown'),
                    context_data.get('operation', 'unknown'),
                    str(system_state.get('memory_usage', 0) > 80),  # Высокое использование памяти
                    str(system_state.get('cpu_usage', 0) > 80),    # Высокое использование CPU
                ]
                
                context_elements.extend(elements)
            
            # Создание отпечатка на основе наиболее частых элементов
            element_counts = Counter(context_elements)
            frequent_elements = [elem for elem, count in element_counts.items() 
                               if count >= len(incidents) * 0.3]
            
            return '_'.join(sorted(frequent_elements))
            
        except Exception as e:
            self.logger.error(f"Failed to generate context fingerprint: {str(e)}")
            return 'unknown_context'
    
    async def _save_pattern_to_db(self, pattern: ProblemPattern):
        """Сохранение паттерна в базу данных"""
        try:
            conn = sqlite3.connect(self.learning_db_path)
            cursor = conn.cursor()
            
            pattern_data = {
                'pattern_id': pattern.pattern_id,
                'problem_type': pattern.problem_type.value,
                'symptoms': pattern.symptoms,
                'root_causes': pattern.root_causes,
                'solutions': pattern.solutions,
                'success_rate': pattern.success_rate,
                'confidence': pattern.confidence.value,
                'seen_count': pattern.seen_count,
                'last_seen': pattern.last_seen.isoformat(),
                'context_fingerprint': pattern.context_fingerprint
            }
            
            cursor.execute("""
                INSERT OR REPLACE INTO learned_patterns 
                (pattern_id, problem_type, pattern_data, confidence_score, success_rate)
                VALUES (?, ?, ?, ?, ?)
            """, (
                pattern.pattern_id,
                pattern.problem_type.value,
                json.dumps(pattern_data, default=str),
                float(pattern.confidence.value == 'expert') * 0.9 + 
                float(pattern.confidence.value == 'high') * 0.7 +
                float(pattern.confidence.value == 'medium') * 0.5 + 
                float(pattern.confidence.value == 'low') * 0.3,
                pattern.success_rate
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Failed to save pattern to DB: {str(e)}")
    
    async def _generate_learning_insights(self) -> List[Dict[str, Any]]:
        """Генерация инсайтов на основе обученных паттернов"""
        insights = []
        
        try:
            # Анализ наиболее частых проблем
            problem_frequency = defaultdict(int)
            for pattern in self.learned_patterns.values():
                problem_frequency[pattern.problem_type] += pattern.seen_count
            
            if problem_frequency:
                most_common_problem = max(problem_frequency.items(), key=lambda x: x[1])
                insights.append({
                    'type': 'frequency_insight',
                    'description': f'Most frequent problem type: {most_common_problem[0].value}',
                    'confidence': 0.9,
                    'actionable_recommendations': [
                        f'Focus debugging resources on {most_common_problem[0].value} issues',
                        'Implement preventive monitoring for this problem type'
                    ]
                })
            
            # Анализ паттернов с высокой успешностью решений
            high_success_patterns = [p for p in self.learned_patterns.values() if p.success_rate > 0.8]
            if high_success_patterns:
                insights.append({
                    'type': 'success_pattern_insight',
                    'description': f'Found {len(high_success_patterns)} highly successful debugging patterns',
                    'confidence': 0.8,
                    'actionable_recommendations': [
                        'Apply successful patterns to similar future problems',
                        'Document these patterns for team knowledge base'
                    ]
                })
            
            # Анализ временных паттернов
            recent_patterns = [p for p in self.learned_patterns.values() 
                             if (datetime.now() - p.last_seen).days < 7]
            if len(recent_patterns) > 5:
                insights.append({
                    'type': 'temporal_insight',
                    'description': f'{len(recent_patterns)} new patterns identified in the last week',
                    'confidence': 0.7,
                    'actionable_recommendations': [
                        'Investigate recent changes that may have introduced new problems',
                        'Update monitoring to catch these new patterns early'
                    ]
                })
            
        except Exception as e:
            self.logger.error(f"Failed to generate learning insights: {str(e)}")
        
        return insights
    
    async def _update_pattern_confidence(self) -> List[Dict[str, Any]]:
        """Обновление уверенности в существующих паттернах"""
        confidence_updates = []
        
        try:
            # Анализ применения паттернов за последнее время
            conn = sqlite3.connect(self.learning_db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT pattern_id, COUNT(*) as applications, 
                       SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successes
                FROM pattern_applications 
                WHERE applied_at > datetime('now', '-30 days')
                GROUP BY pattern_id
                HAVING applications > 0
            """)
            
            application_stats = cursor.fetchall()
            conn.close()
            
            for stats in application_stats:
                pattern_id = stats['pattern_id']
                applications = stats['applications']
                successes = stats['successes']
                
                if pattern_id in self.learned_patterns:
                    pattern = self.learned_patterns[pattern_id]
                    
                    # Обновление статистики успешности
                    new_success_rate = successes / applications
                    
                    # Сглаженное обновление с учетом исторических данных
                    alpha = 0.3  # Коэффициент обучения
                    pattern.success_rate = (1 - alpha) * pattern.success_rate + alpha * new_success_rate
                    
                    # Обновление уверенности на основе количества применений
                    if applications >= 10:
                        if pattern.confidence == LearningConfidence.LOW:
                            pattern.confidence = LearningConfidence.MEDIUM
                        elif pattern.confidence == LearningConfidence.MEDIUM and applications >= 25:
                            pattern.confidence = LearningConfidence.HIGH
                    
                    confidence_updates.append({
                        'pattern_id': pattern_id,
                        'old_confidence': pattern.confidence.value,
                        'new_success_rate': pattern.success_rate,
                        'recent_applications': applications
                    })
        
        except Exception as e:
            self.logger.error(f"Failed to update pattern confidence: {str(e)}")
        
        return confidence_updates
    
    async def _generate_predictive_alerts(self) -> List[Dict[str, Any]]:
        """Генерация предсказательных алертов на основе паттернов"""
        predictions = []
        
        try:
            # Анализ текущего состояния системы для предсказания проблем
            from ..debug.system_diagnostics import SystemDiagnostics
            system_diag = SystemDiagnostics()
            current_health = await system_diag.full_health_check()
            
            # Поиск паттернов, которые могут сработать в текущих условиях
            for pattern in self.learned_patterns.values():
                if pattern.confidence in [LearningConfidence.HIGH, LearningConfidence.EXPERT]:
                    
                    # Проверка наличия симптомов паттерна в текущем состоянии
                    current_symptoms = self._extract_current_symptoms(current_health)
                    pattern_symptoms = set(pattern.symptoms)
                    
                    matching_symptoms = pattern_symptoms & current_symptoms
                    symptom_match_ratio = len(matching_symptoms) / len(pattern_symptoms)
                    
                    if symptom_match_ratio > 0.6:  # 60% совпадение симптомов
                        predictions.append({
                            'alert_type': 'predictive_warning',
                            'problem_type': pattern.problem_type.value,
                            'confidence': pattern.confidence.value,
                            'symptom_match_ratio': symptom_match_ratio,
                            'matching_symptoms': list(matching_symptoms),
                            'predicted_solutions': pattern.solutions,
                            'description': f'High probability of {pattern.problem_type.value} based on current symptoms'
                        })
        
        except Exception as e:
            self.logger.error(f"Failed to generate predictive alerts: {str(e)}")
        
        return predictions
    
    def _extract_current_symptoms(self, health_data: Dict[str, Any]) -> set:
        """Извлечение текущих симптомов из данных о здоровье системы"""
        symptoms = set()
        
        try:
            # Анализ использования ресурсов
            system_info = health_data.get('system_info', {})
            
            if system_info.get('cpu_percent', 0) > 80:
                symptoms.add('high_cpu_usage')
            
            memory_percent = system_info.get('memory', {}).get('percent', 0)
            if memory_percent > 85:
                symptoms.add('high_memory_usage')
            
            disk_percent = system_info.get('disk', {}).get('percent', 0)
            if disk_percent > 90:
                symptoms.add('low_disk_space')
            
            # Анализ проблем инфраструктуры
            infrastructure = health_data.get('infrastructure', {})
            if infrastructure.get('docker', {}).get('status') != 'running':
                symptoms.add('docker_issues')
            
            # Анализ баз данных
            databases = health_data.get('databases', {})
            for db_name, db_info in databases.items():
                if db_info.get('status') != 'connected':
                    symptoms.add(f'{db_name}_connectivity_issues')
            
            # Анализ внешних сервисов
            external_services = health_data.get('external_services', {})
            for service_name, service_info in external_services.items():
                if service_info.get('status') != 'connected':
                    symptoms.add(f'{service_name}_api_issues')
        
        except Exception as e:
            self.logger.error(f"Failed to extract current symptoms: {str(e)}")
        
        return symptoms
    
    async def get_recommended_solution(self, problem_symptoms: List[str], 
                                     problem_context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Получение рекомендованного решения на основе симптомов и контекста
        
        Args:
            problem_symptoms: Список симптомов проблемы
            problem_context: Контекст проблемы
        
        Returns:
            Рекомендованное решение или None
        """
        try:
            symptom_set = set(problem_symptoms)
            best_match = None
            best_score = 0
            
            for pattern in self.learned_patterns.values():
                # Вычисление соответствия симптомов
                pattern_symptoms = set(pattern.symptoms)
                intersection = len(symptom_set & pattern_symptoms)
                union = len(symptom_set | pattern_symptoms)
                
                if union > 0:
                    similarity_score = intersection / union
                    
                    # Бонус за высокую уверенность и успешность
                    confidence_bonus = 0
                    if pattern.confidence == LearningConfidence.EXPERT:
                        confidence_bonus = 0.3
                    elif pattern.confidence == LearningConfidence.HIGH:
                        confidence_bonus = 0.2
                    elif pattern.confidence == LearningConfidence.MEDIUM:
                        confidence_bonus = 0.1
                    
                    success_bonus = pattern.success_rate * 0.2
                    
                    total_score = similarity_score + confidence_bonus + success_bonus
                    
                    if total_score > best_score and total_score > self.confidence_threshold:
                        best_score = total_score
                        best_match = pattern
            
            if best_match:
                return {
                    'pattern_id': best_match.pattern_id,
                    'confidence_score': best_score,
                    'success_rate': best_match.success_rate,
                    'recommended_solutions': best_match.solutions,
                    'similar_symptoms': list(set(best_match.symptoms) & symptom_set),
                    'problem_type': best_match.problem_type.value,
                    'based_on_cases': best_match.seen_count
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get recommended solution: {str(e)}")
            return None
    
    async def record_solution_feedback(self, pattern_id: str, incident_id: str, 
                                     success: bool, feedback: str = None) -> bool:
        """Запись обратной связи о применении решения"""
        try:
            conn = sqlite3.connect(self.learning_db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO pattern_applications 
                (pattern_id, incident_id, success, feedback)
                VALUES (?, ?, ?, ?)
            """, (pattern_id, incident_id, success, feedback))
            
            # Обновление статистики паттерна
            cursor.execute("""
                UPDATE learned_patterns 
                SET times_applied = times_applied + 1,
                    successful_applications = successful_applications + ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE pattern_id = ?
            """, (1 if success else 0, pattern_id))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Recorded solution feedback for pattern {pattern_id}: success={success}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to record solution feedback: {str(e)}")
            return False
    
    async def _load_learned_data(self):
        """Загрузка обученных данных из файлов"""
        try:
            if self.patterns_file.exists():
                with open(self.patterns_file, 'rb') as f:
                    self.learned_patterns = pickle.load(f)
            
            if self.insights_file.exists():
                with open(self.insights_file, 'rb') as f:
                    self.learning_insights = pickle.load(f)
                    
            self.logger.info(f"Loaded {len(self.learned_patterns)} patterns and {len(self.learning_insights)} insights")
            
        except Exception as e:
            self.logger.error(f"Failed to load learned data: {str(e)}")
    
    async def _save_learned_data(self):
        """Сохранение обученных данных в файлы"""
        try:
            with open(self.patterns_file, 'wb') as f:
                pickle.dump(self.learned_patterns, f)
            
            with open(self.insights_file, 'wb') as f:
                pickle.dump(self.learning_insights, f)
                
            self.logger.info(f"Saved {len(self.learned_patterns)} patterns and {len(self.learning_insights)} insights")
            
        except Exception as e:
            self.logger.error(f"Failed to save learned data: {str(e)}")
    
    async def _trigger_incremental_learning(self, incident_id: str):
        """Запуск инкрементального обучения на новом инциденте"""
        try:
            # Получение данных инцидента
            conn = sqlite3.connect(self.learning_db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM debug_incidents WHERE incident_id = ?
            """, (incident_id,))
            
            incident = cursor.fetchone()
            conn.close()
            
            if incident:
                incident_dict = dict(incident)
                
                # Поиск похожих инцидентов
                similar_incidents = await self._find_similar_incidents(incident_dict)
                
                # Если найдено достаточно похожих инцидентов, обновляем паттерн
                if len(similar_incidents) >= self.min_pattern_threshold:
                    await self._create_or_update_pattern(incident_dict, similar_incidents)
                    self.logger.info(f"Updated pattern based on incident {incident_id}")
        
        except Exception as e:
            self.logger.error(f"Failed to trigger incremental learning: {str(e)}")
    
    async def _ensure_data_loaded(self):
        """Обеспечение загрузки данных при первом использовании"""
        if not self._data_loaded:
            await self._load_learned_data()
            self._data_loaded = True
    
    async def get_learning_statistics(self) -> Dict[str, Any]:
        """Получение статистики обучения"""
        await self._ensure_data_loaded()
        try:
            stats = {
                'total_patterns': len(self.learned_patterns),
                'confidence_distribution': defaultdict(int),
                'problem_type_distribution': defaultdict(int),
                'success_rate_stats': {},
                'recent_learning_activity': {}
            }
            
            # Распределение по уверенности
            for pattern in self.learned_patterns.values():
                stats['confidence_distribution'][pattern.confidence.value] += 1
                stats['problem_type_distribution'][pattern.problem_type.value] += 1
            
            # Статистика успешности
            success_rates = [p.success_rate for p in self.learned_patterns.values()]
            if success_rates:
                stats['success_rate_stats'] = {
                    'average': statistics.mean(success_rates),
                    'median': statistics.median(success_rates),
                    'min': min(success_rates),
                    'max': max(success_rates)
                }
            
            # Активность обучения за последнюю неделю
            recent_patterns = [
                p for p in self.learned_patterns.values()
                if (datetime.now() - p.last_seen).days <= 7
            ]
            
            stats['recent_learning_activity'] = {
                'new_patterns_last_week': len(recent_patterns),
                'total_insights': len(self.learning_insights),
                'learning_velocity': len(recent_patterns) / 7  # Паттернов в день
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get learning statistics: {str(e)}")
            return {}


# CLI для управления системой обучения
async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Debug Learning Engine CLI")
    parser.add_argument('action', choices=['stats', 'patterns', 'insights', 'recommend'])
    parser.add_argument('--symptoms', nargs='+', help='Symptoms for recommendation')
    parser.add_argument('--context', help='JSON context for recommendation')
    
    args = parser.parse_args()
    
    engine = DebugLearningEngine()
    
    if args.action == 'stats':
        stats = await engine.get_learning_statistics()
        print(f"\n🧠 LEARNING STATISTICS:")
        print(f"Total Patterns: {stats.get('total_patterns', 0)}")
        print(f"New Patterns (7d): {stats.get('recent_learning_activity', {}).get('new_patterns_last_week', 0)}")
        print(f"Avg Success Rate: {stats.get('success_rate_stats', {}).get('average', 0):.1%}")
        
    elif args.action == 'patterns':
        print(f"\n🎯 LEARNED PATTERNS ({len(engine.learned_patterns)}):")
        for pattern_id, pattern in list(engine.learned_patterns.items())[:10]:
            print(f"Pattern: {pattern_id}")
            print(f"  Type: {pattern.problem_type.value}")
            print(f"  Confidence: {pattern.confidence.value}")
            print(f"  Success Rate: {pattern.success_rate:.1%}")
            print(f"  Cases: {pattern.seen_count}")
            print()
    
    elif args.action == 'recommend':
        if not args.symptoms:
            print("❌ --symptoms required for recommendation")
            return
        
        context = {}
        if args.context:
            context = json.loads(args.context)
        
        recommendation = await engine.get_recommended_solution(args.symptoms, context)
        
        if recommendation:
            print(f"\n💡 RECOMMENDATION:")
            print(f"Confidence: {recommendation['confidence_score']:.2f}")
            print(f"Success Rate: {recommendation['success_rate']:.1%}")
            print(f"Solutions: {', '.join(recommendation['recommended_solutions'])}")
        else:
            print("❌ No suitable solution found")


if __name__ == "__main__":
    asyncio.run(main())