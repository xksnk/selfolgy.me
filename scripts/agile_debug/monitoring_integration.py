"""
📈 Monitoring Integration - Интеграция с системой мониторинга
Плотная интеграция между мониторингом и отладкой для реального времени.
"""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict, deque
import logging
import psutil


class MonitoringIntegration:
    """
    🎯 Интеграция мониторинга с агильной отладкой
    
    Функции:
    - Реальное время передачи данных мониторинга в отладчик
    - Автоматические триггеры отладки на основе алертов
    - Обратная связь от отладки в мониторинг
    - Адаптивные пороги на основе результатов отладки
    - Предсказательная аналитика проблем
    """
    
    def __init__(self):
        self.integration_start = datetime.now()
        
        # Очереди для интеграции
        self.monitoring_alerts = deque(maxlen=500)
        self.debug_feedback = deque(maxlen=500)
        
        # Подключенная система обучения
        self.connected_learning_engine = None
        
        # Адаптивные пороги
        self.adaptive_thresholds = {
            'cpu_usage': 80.0,
            'memory_usage': 85.0,
            'response_time': 5000.0,  # ms
            'error_rate': 50.0,       # errors per hour
            'disk_usage': 90.0
        }
        
        # История мониторинга
        self.monitoring_history = deque(maxlen=1000)
        
        self.logger = logging.getLogger(__name__)
    
    def connect_to_learning(self, learning_engine):
        """Подключение к системе обучения"""
        self.connected_learning_engine = learning_engine
        self.logger.info("Monitoring integration connected to learning engine")
    
    async def get_comprehensive_health_overview(self) -> Dict[str, Any]:
        """Получение комплексного обзора здоровья системы"""
        health_overview = {
            'timestamp': datetime.now().isoformat(),
            'overall_health_score': 0.0,
            'component_status': {},
            'active_alerts': [],
            'performance_metrics': {},
            'trend_analysis': {},
            'uptime_percentage': 100.0,
            'debug_integration_status': {},
            'learning_feedback': {}
        }
        
        try:
            # Сбор данных о производительности системы
            health_overview['performance_metrics'] = await self._collect_performance_metrics()
            
            # Статус компонентов
            health_overview['component_status'] = await self._get_component_status()
            
            # Активные алерты
            health_overview['active_alerts'] = await self._get_active_alerts()
            
            # Анализ трендов
            health_overview['trend_analysis'] = await self._analyze_performance_trends()
            
            # Расчет общего счета здоровья
            health_overview['overall_health_score'] = self._calculate_overall_health(health_overview)
            
            # Статус интеграции отладки
            health_overview['debug_integration_status'] = await self._get_debug_integration_status()
            
            # Обратная связь от системы обучения
            if self.connected_learning_engine:
                learning_stats = await self.connected_learning_engine.get_learning_statistics()
                health_overview['learning_feedback'] = learning_stats
            
            # Сохранение в историю
            self.monitoring_history.append({
                'timestamp': datetime.now(),
                'health_score': health_overview['overall_health_score'],
                'alert_count': len(health_overview['active_alerts'])
            })
            
        except Exception as e:
            health_overview['error'] = str(e)
            self.logger.error(f"Failed to get comprehensive health overview: {str(e)}")
        
        return health_overview
    
    async def quick_health_check(self) -> Dict[str, Any]:
        """Быстрая проверка здоровья системы"""
        quick_check = {
            'timestamp': datetime.now().isoformat(),
            'system_health_score': 0.0,
            'critical_alerts': [],
            'resource_status': {},
            'service_status': {}
        }
        
        try:
            # Быстрая проверка ресурсов
            quick_check['resource_status'] = {
                'cpu_percent': psutil.cpu_percent(interval=0.1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': (psutil.disk_usage('/').used / psutil.disk_usage('/').total) * 100
            }
            
            # Быстрая проверка сервисов
            quick_check['service_status'] = await self._quick_service_check()
            
            # Проверка критических алертов
            quick_check['critical_alerts'] = await self._get_critical_alerts()
            
            # Быстрый расчет здоровья
            quick_check['system_health_score'] = self._quick_health_calculation(quick_check)
            
        except Exception as e:
            quick_check['error'] = str(e)
        
        return quick_check
    
    async def _collect_performance_metrics(self) -> Dict[str, Any]:
        """Сбор метрик производительности"""
        metrics = {
            'system_resources': {},
            'response_times': {},
            'throughput': {},
            'error_rates': {}
        }
        
        try:
            # Системные ресурсы
            metrics['system_resources'] = {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': (psutil.disk_usage('/').used / psutil.disk_usage('/').total) * 100,
                'network_io': {
                    'bytes_sent': psutil.net_io_counters().bytes_sent,
                    'bytes_recv': psutil.net_io_counters().bytes_recv
                },
                'disk_io': {
                    'read_bytes': psutil.disk_io_counters().read_bytes if psutil.disk_io_counters() else 0,
                    'write_bytes': psutil.disk_io_counters().write_bytes if psutil.disk_io_counters() else 0
                }
            }
            
            # Времена ответа из логов метрик
            metrics['response_times'] = await self._parse_response_times()
            
            # Пропускная способность
            metrics['throughput'] = await self._calculate_throughput()
            
            # Частота ошибок
            metrics['error_rates'] = await self._calculate_error_rates()
            
        except Exception as e:
            metrics['error'] = str(e)
        
        return metrics
    
    async def _get_component_status(self) -> Dict[str, Any]:
        """Получение статуса всех компонентов"""
        component_status = {}
        
        try:
            # Статус основных компонентов Selfology
            components = [
                'selfology_bot',
                'database',
                'vector_db', 
                'ai_router',
                'question_core',
                'monitoring'
            ]
            
            for component in components:
                component_status[component] = await self._check_component_health(component)
        
        except Exception as e:
            component_status['error'] = str(e)
        
        return component_status
    
    async def _check_component_health(self, component: str) -> Dict[str, str]:
        """Проверка здоровья отдельного компонента"""
        health = {'status': 'unknown', 'details': ''}
        
        try:
            if component == 'selfology_bot':
                # Проверка процесса бота
                bot_running = False
                for proc in psutil.process_iter(['cmdline']):
                    try:
                        cmdline = ' '.join(proc.info['cmdline'] or [])
                        if 'selfology' in cmdline.lower() or 'monitored_bot' in cmdline:
                            bot_running = True
                            break
                    except:
                        continue
                
                health['status'] = 'running' if bot_running else 'stopped'
                health['details'] = 'Bot process detected' if bot_running else 'No bot process found'
            
            elif component == 'database':
                # Проверка PostgreSQL
                try:
                    result = subprocess.run(
                        ['docker', 'exec', 'n8n-postgres', 'pg_isready', '-U', 'postgres'],
                        capture_output=True, text=True, timeout=10
                    )
                    health['status'] = 'healthy' if result.returncode == 0 else 'unhealthy'
                    health['details'] = result.stdout.strip() or result.stderr.strip()
                except Exception as e:
                    health['status'] = 'error'
                    health['details'] = str(e)
            
            elif component == 'vector_db':
                # Проверка Qdrant
                try:
                    import aiohttp
                    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                        async with session.get('http://localhost:6333/health') as resp:
                            health['status'] = 'healthy' if resp.status == 200 else 'unhealthy'
                            health['details'] = f'HTTP {resp.status}'
                except Exception as e:
                    health['status'] = 'error'
                    health['details'] = str(e)
            
            elif component == 'ai_router':
                # Проверка AI роутера через логи
                ai_log_path = Path('logs/ai/ai_interactions.log')
                if ai_log_path.exists():
                    # Проверка недавней активности
                    mtime = datetime.fromtimestamp(ai_log_path.stat().st_mtime)
                    if (datetime.now() - mtime).total_seconds() < 3600:  # Активность в последний час
                        health['status'] = 'active'
                        health['details'] = f'Last activity: {mtime.strftime("%H:%M:%S")}'
                    else:
                        health['status'] = 'inactive'
                        health['details'] = f'No activity since {mtime.strftime("%H:%M:%S")}'
                else:
                    health['status'] = 'unknown'
                    health['details'] = 'No AI interaction logs found'
            
            elif component == 'question_core':
                # Проверка системы вопросов
                core_file = Path('intelligent_question_core/data/selfology_intelligent_core.json')
                if core_file.exists():
                    try:
                        with open(core_file, 'r') as f:
                            core_data = json.load(f)
                        
                        question_count = len(core_data.get('questions', []))
                        health['status'] = 'loaded' if question_count > 600 else 'incomplete'
                        health['details'] = f'{question_count} questions loaded'
                    except Exception as e:
                        health['status'] = 'corrupted'
                        health['details'] = str(e)
                else:
                    health['status'] = 'missing'
                    health['details'] = 'Core data file not found'
            
            elif component == 'monitoring':
                # Проверка самой системы мониторинга
                monitoring_active = Path('logs/metrics/metrics.log').exists()
                health['status'] = 'active' if monitoring_active else 'inactive'
                health['details'] = 'Metrics logging active' if monitoring_active else 'No metrics logs'
        
        except Exception as e:
            health['status'] = 'error'
            health['details'] = str(e)
        
        return health
    
    async def _get_active_alerts(self) -> List[Dict[str, Any]]:
        """Получение активных алертов"""
        alerts = []
        
        try:
            # Проверка критических пороговых значений
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > self.adaptive_thresholds['cpu_usage']:
                alerts.append({
                    'severity': 'critical' if cpu_percent > 95 else 'high',
                    'type': 'resource_usage',
                    'component': 'system',
                    'message': f'High CPU usage: {cpu_percent:.1f}%',
                    'threshold': self.adaptive_thresholds['cpu_usage'],
                    'current_value': cpu_percent
                })
            
            memory_percent = psutil.virtual_memory().percent
            if memory_percent > self.adaptive_thresholds['memory_usage']:
                alerts.append({
                    'severity': 'critical' if memory_percent > 97 else 'high',
                    'type': 'resource_usage',
                    'component': 'system',
                    'message': f'High memory usage: {memory_percent:.1f}%',
                    'threshold': self.adaptive_thresholds['memory_usage'],
                    'current_value': memory_percent
                })
            
            disk_percent = (psutil.disk_usage('/').used / psutil.disk_usage('/').total) * 100
            if disk_percent > self.adaptive_thresholds['disk_usage']:
                alerts.append({
                    'severity': 'critical' if disk_percent > 97 else 'high',
                    'type': 'resource_usage',
                    'component': 'storage',
                    'message': f'Low disk space: {disk_percent:.1f}% used',
                    'threshold': self.adaptive_thresholds['disk_usage'],
                    'current_value': disk_percent
                })
            
            # Проверка ошибок
            error_rate = await self._calculate_current_error_rate()
            if error_rate > self.adaptive_thresholds['error_rate']:
                alerts.append({
                    'severity': 'high',
                    'type': 'error_rate',
                    'component': 'system',
                    'message': f'High error rate: {error_rate:.1f} errors/hour',
                    'threshold': self.adaptive_thresholds['error_rate'],
                    'current_value': error_rate
                })
            
            # Добавление временных меток
            for alert in alerts:
                alert['timestamp'] = datetime.now().isoformat()
                alert['alert_id'] = f"alert_{int(datetime.now().timestamp())}_{alert['component']}"
        
        except Exception as e:
            self.logger.error(f"Failed to get active alerts: {str(e)}")
        
        return alerts
    
    async def _get_critical_alerts(self) -> List[Dict[str, Any]]:
        """Получение только критических алертов"""
        all_alerts = await self._get_active_alerts()
        return [alert for alert in all_alerts if alert.get('severity') == 'critical']
    
    async def integrate_feedback_loop(self) -> Dict[str, Any]:
        """Интеграция цикла обратной связи между мониторингом и отладкой"""
        integration_result = {
            'timestamp': datetime.now().isoformat(),
            'monitoring_data_collected': False,
            'debug_feedback_processed': False,
            'threshold_adjustments': [],
            'automation_triggers': [],
            'predictive_analysis': {},
            'system_learning_applied': False
        }
        
        try:
            # Сбор данных мониторинга
            monitoring_data = await self._collect_monitoring_data()
            integration_result['monitoring_data_collected'] = True
            
            # Обработка обратной связи от отладчика
            debug_feedback = await self._process_debug_feedback()
            integration_result['debug_feedback_processed'] = True
            
            # Адаптация пороговых значений на основе обратной связи
            threshold_adjustments = await self._adapt_thresholds_based_on_feedback(debug_feedback)
            integration_result['threshold_adjustments'] = threshold_adjustments
            
            # Настройка автоматических триггеров
            automation_triggers = await self._setup_automation_triggers(monitoring_data)
            integration_result['automation_triggers'] = automation_triggers
            
            # Предсказательный анализ
            if self.connected_learning_engine:
                predictive_analysis = await self._perform_predictive_analysis(monitoring_data)
                integration_result['predictive_analysis'] = predictive_analysis
                integration_result['system_learning_applied'] = True
            
        except Exception as e:
            integration_result['error'] = str(e)
            self.logger.error(f"Failed to integrate feedback loop: {str(e)}")
        
        return integration_result
    
    async def _collect_monitoring_data(self) -> Dict[str, Any]:
        """Сбор данных мониторинга для интеграции"""
        monitoring_data = {
            'current_metrics': await self._collect_performance_metrics(),
            'recent_alerts': list(self.monitoring_alerts)[-50:],  # Последние 50 алертов
            'system_state': await self._get_current_system_state(),
            'component_health': await self._get_component_status()
        }
        
        return monitoring_data
    
    async def _process_debug_feedback(self) -> List[Dict[str, Any]]:
        """Обработка обратной связи от отладчика"""
        debug_feedback = list(self.debug_feedback)
        
        # Анализ обратной связи для улучшения мониторинга
        processed_feedback = []
        
        for feedback in debug_feedback:
            if feedback.get('type') == 'threshold_adjustment':
                processed_feedback.append({
                    'feedback_type': 'threshold',
                    'component': feedback.get('component'),
                    'suggested_threshold': feedback.get('suggested_value'),
                    'reason': feedback.get('reason')
                })
            
            elif feedback.get('type') == 'false_positive':
                processed_feedback.append({
                    'feedback_type': 'false_positive',
                    'alert_type': feedback.get('alert_type'),
                    'reason': feedback.get('reason')
                })
        
        return processed_feedback
    
    async def _adapt_thresholds_based_on_feedback(self, debug_feedback: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Адаптация пороговых значений на основе обратной связи"""
        adjustments = []
        
        try:
            for feedback in debug_feedback:
                if feedback.get('feedback_type') == 'threshold':
                    component = feedback.get('component')
                    suggested_threshold = feedback.get('suggested_threshold')
                    
                    # Найти соответствующий порог
                    threshold_key = None
                    if 'cpu' in component:
                        threshold_key = 'cpu_usage'
                    elif 'memory' in component:
                        threshold_key = 'memory_usage'
                    elif 'disk' in component:
                        threshold_key = 'disk_usage'
                    elif 'response' in component:
                        threshold_key = 'response_time'
                    elif 'error' in component:
                        threshold_key = 'error_rate'
                    
                    if threshold_key and suggested_threshold:
                        old_threshold = self.adaptive_thresholds[threshold_key]
                        
                        # Консервативная адаптация (изменение не более чем на 20%)
                        max_change = old_threshold * 0.2
                        new_threshold = max(
                            old_threshold - max_change,
                            min(old_threshold + max_change, suggested_threshold)
                        )
                        
                        if new_threshold != old_threshold:
                            self.adaptive_thresholds[threshold_key] = new_threshold
                            adjustments.append({
                                'threshold': threshold_key,
                                'old_value': old_threshold,
                                'new_value': new_threshold,
                                'reason': feedback.get('reason', 'Debug feedback')
                            })
        
        except Exception as e:
            self.logger.error(f"Failed to adapt thresholds: {str(e)}")
        
        return adjustments
    
    async def _setup_automation_triggers(self, monitoring_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Настройка автоматических триггеров отладки"""
        triggers = []
        
        try:
            # Триггер для высокого использования ресурсов
            resources = monitoring_data.get('current_metrics', {}).get('system_resources', {})
            
            if resources.get('cpu_percent', 0) > 90:
                triggers.append({
                    'trigger_type': 'auto_debug',
                    'condition': 'high_cpu',
                    'action': 'investigate_high_cpu_processes',
                    'priority': 'critical'
                })
            
            if resources.get('memory_percent', 0) > 95:
                triggers.append({
                    'trigger_type': 'auto_debug',
                    'condition': 'memory_critical',
                    'action': 'memory_cleanup_and_analysis',
                    'priority': 'critical'
                })
            
            # Триггер для частых ошибок
            error_rates = monitoring_data.get('current_metrics', {}).get('error_rates', {})
            if error_rates.get('total_errors_per_hour', 0) > 100:
                triggers.append({
                    'trigger_type': 'auto_debug',
                    'condition': 'error_spike',
                    'action': 'analyze_error_patterns',
                    'priority': 'high'
                })
            
            # Триггер для проблем компонентов
            component_health = monitoring_data.get('component_health', {})
            for component, health in component_health.items():
                if health.get('status') in ['stopped', 'error', 'unhealthy']:
                    triggers.append({
                        'trigger_type': 'auto_debug',
                        'condition': f'{component}_failure',
                        'action': f'diagnose_and_fix_{component}',
                        'priority': 'high',
                        'component': component
                    })
        
        except Exception as e:
            self.logger.error(f"Failed to setup automation triggers: {str(e)}")
        
        return triggers
    
    async def _perform_predictive_analysis(self, monitoring_data: Dict[str, Any]) -> Dict[str, Any]:
        """Выполнение предсказательного анализа с системой обучения"""
        predictive_analysis = {
            'predictions': [],
            'confidence_scores': {},
            'recommended_preventive_actions': []
        }
        
        try:
            if not self.connected_learning_engine:
                predictive_analysis['error'] = 'Learning engine not connected'
                return predictive_analysis
            
            # Извлечение симптомов из текущих данных мониторинга
            current_symptoms = self._extract_symptoms_from_monitoring(monitoring_data)
            
            # Получение рекомендаций от системы обучения
            for symptoms_group in self._group_symptoms(current_symptoms):
                recommendation = await self.connected_learning_engine.get_recommended_solution(
                    symptoms_group, monitoring_data
                )
                
                if recommendation:
                    predictive_analysis['predictions'].append({
                        'predicted_problem': recommendation.get('problem_type'),
                        'confidence': recommendation.get('confidence_score'),
                        'symptoms_detected': symptoms_group,
                        'recommended_solutions': recommendation.get('recommended_solutions', [])
                    })
                    
                    predictive_analysis['confidence_scores'][recommendation.get('problem_type')] = \
                        recommendation.get('confidence_score', 0)
            
            # Генерация превентивных действий
            high_confidence_predictions = [
                p for p in predictive_analysis['predictions'] 
                if p.get('confidence', 0) > 0.7
            ]
            
            for prediction in high_confidence_predictions:
                for solution in prediction.get('recommended_solutions', []):
                    predictive_analysis['recommended_preventive_actions'].append({
                        'action': solution,
                        'predicted_problem': prediction['predicted_problem'],
                        'confidence': prediction['confidence'],
                        'urgency': 'high' if prediction['confidence'] > 0.8 else 'medium'
                    })
        
        except Exception as e:
            predictive_analysis['error'] = str(e)
        
        return predictive_analysis
    
    def _extract_symptoms_from_monitoring(self, monitoring_data: Dict[str, Any]) -> List[str]:
        """Извлечение симптомов из данных мониторинга"""
        symptoms = []
        
        try:
            # Ресурсные симптомы
            resources = monitoring_data.get('current_metrics', {}).get('system_resources', {})
            
            if resources.get('cpu_percent', 0) > 80:
                symptoms.append('high_cpu_usage')
            
            if resources.get('memory_percent', 0) > 85:
                symptoms.append('high_memory_usage')
            
            if resources.get('disk_percent', 0) > 90:
                symptoms.append('low_disk_space')
            
            # Симптомы компонентов
            component_health = monitoring_data.get('component_health', {})
            for component, health in component_health.items():
                status = health.get('status', 'unknown')
                if status in ['stopped', 'error', 'unhealthy']:
                    symptoms.append(f'{component}_issues')
            
            # Симптомы производительности
            response_times = monitoring_data.get('current_metrics', {}).get('response_times', {})
            if response_times.get('average_ms', 0) > 5000:
                symptoms.append('slow_response_times')
        
        except Exception as e:
            self.logger.error(f"Failed to extract symptoms: {str(e)}")
        
        return symptoms
    
    def _group_symptoms(self, symptoms: List[str]) -> List[List[str]]:
        """Группировка симптомов для анализа"""
        # Простая группировка по типам
        groups = []
        
        resource_symptoms = [s for s in symptoms if any(keyword in s for keyword in ['cpu', 'memory', 'disk'])]
        if resource_symptoms:
            groups.append(resource_symptoms)
        
        service_symptoms = [s for s in symptoms if 'issues' in s]
        if service_symptoms:
            groups.append(service_symptoms)
        
        performance_symptoms = [s for s in symptoms if any(keyword in s for keyword in ['slow', 'timeout', 'latency'])]
        if performance_symptoms:
            groups.append(performance_symptoms)
        
        # Если нет групп, создаем одну общую
        if not groups and symptoms:
            groups.append(symptoms)
        
        return groups
    
    async def _quick_service_check(self) -> Dict[str, str]:
        """Быстрая проверка сервисов"""
        service_status = {}
        
        try:
            # Проверка Docker сервисов
            services = ['n8n-postgres', 'qdrant', 'n8n-redis']
            
            for service in services:
                try:
                    result = subprocess.run(
                        ['docker', 'ps', '--filter', f'name={service}', '--format', '{{.Status}}'],
                        capture_output=True, text=True, timeout=5
                    )
                    
                    service_status[service] = 'running' if 'Up' in result.stdout else 'stopped'
                except Exception:
                    service_status[service] = 'unknown'
        
        except Exception as e:
            service_status['error'] = str(e)
        
        return service_status
    
    def _quick_health_calculation(self, quick_check: Dict[str, Any]) -> float:
        """Быстрый расчет здоровья системы"""
        score = 100.0
        
        try:
            # Штрафы за использование ресурсов
            resources = quick_check.get('resource_status', {})
            
            cpu_percent = resources.get('cpu_percent', 0)
            if cpu_percent > 90:
                score -= 30
            elif cpu_percent > 80:
                score -= 15
            
            memory_percent = resources.get('memory_percent', 0)
            if memory_percent > 95:
                score -= 25
            elif memory_percent > 85:
                score -= 10
            
            disk_percent = resources.get('disk_percent', 0)
            if disk_percent > 95:
                score -= 20
            elif disk_percent > 90:
                score -= 10
            
            # Штрафы за остановленные сервисы
            services = quick_check.get('service_status', {})
            for service, status in services.items():
                if status == 'stopped':
                    score -= 15
                elif status == 'unknown':
                    score -= 5
            
            # Штрафы за критические алерты
            critical_alerts = len(quick_check.get('critical_alerts', []))
            score -= critical_alerts * 10
        
        except Exception as e:
            self.logger.error(f"Health calculation failed: {str(e)}")
        
        return max(0.0, score)
    
    def _calculate_overall_health(self, health_overview: Dict[str, Any]) -> float:
        """Расчет общего показателя здоровья"""
        return self._quick_health_calculation(health_overview)
    
    async def _get_debug_integration_status(self) -> Dict[str, str]:
        """Получение статуса интеграции отладки"""
        status = {
            'learning_engine_connected': self.connected_learning_engine is not None,
            'feedback_queue_size': len(self.debug_feedback),
            'monitoring_queue_size': len(self.monitoring_alerts),
            'adaptive_thresholds_active': len(self.adaptive_thresholds) > 0
        }
        
        return status
    
    async def _parse_response_times(self) -> Dict[str, Any]:
        """Парсинг времен ответа из логов"""
        # Заглушка - нужна реализация парсинга метрик
        return {'average_ms': 0, 'p95_ms': 0}
    
    async def _calculate_throughput(self) -> Dict[str, Any]:
        """Расчет пропускной способности"""
        # Заглушка - нужна реализация расчета пропускной способности
        return {'requests_per_second': 0}
    
    async def _calculate_error_rates(self) -> Dict[str, Any]:
        """Расчет частоты ошибок"""
        # Заглушка - нужна реализация расчета ошибок
        return {'errors_per_hour': 0}
    
    async def _calculate_current_error_rate(self) -> float:
        """Расчет текущей частоты ошибок"""
        try:
            error_log_path = Path('logs/errors/errors.log')
            if not error_log_path.exists():
                return 0.0
            
            # Подсчет ошибок за последний час
            with open(error_log_path, 'r') as f:
                lines = f.readlines()[-100:]  # Последние 100 строк
            
            # Простой подсчет - в реальной реализации нужен парсинг времени
            recent_errors = len(lines)
            return min(recent_errors * 0.6, 200)  # Примерная оценка ошибок в час
            
        except Exception as e:
            self.logger.error(f"Failed to calculate error rate: {str(e)}")
            return 0.0
    
    async def _get_current_system_state(self) -> Dict[str, Any]:
        """Получение текущего состояния системы"""
        state = {
            'uptime': (datetime.now() - datetime.fromtimestamp(psutil.boot_time())).total_seconds(),
            'load_average': list(psutil.getloadavg()) if hasattr(psutil, 'getloadavg') else [0, 0, 0],
            'active_connections': len(psutil.net_connections()),
            'running_processes': len(psutil.pids())
        }
        
        return state
    
    async def _analyze_performance_trends(self) -> Dict[str, Any]:
        """Анализ трендов производительности"""
        trends = {
            'health_trend': 'stable',
            'performance_trend': 'stable',
            'alert_frequency_trend': 'stable'
        }
        
        try:
            if len(self.monitoring_history) > 10:
                # Анализ тренда здоровья
                recent_scores = [h['health_score'] for h in list(self.monitoring_history)[-10:]]
                if len(recent_scores) >= 2:
                    if recent_scores[-1] < recent_scores[0] - 10:
                        trends['health_trend'] = 'declining'
                    elif recent_scores[-1] > recent_scores[0] + 10:
                        trends['health_trend'] = 'improving'
                
                # Анализ тренда алертов
                recent_alerts = [h['alert_count'] for h in list(self.monitoring_history)[-10:]]
                if len(recent_alerts) >= 2:
                    avg_recent = sum(recent_alerts[-5:]) / 5 if len(recent_alerts) >= 5 else recent_alerts[-1]
                    avg_older = sum(recent_alerts[-10:-5]) / 5 if len(recent_alerts) >= 10 else recent_alerts[0]
                    
                    if avg_recent > avg_older * 1.5:
                        trends['alert_frequency_trend'] = 'increasing'
                    elif avg_recent < avg_older * 0.7:
                        trends['alert_frequency_trend'] = 'decreasing'
        
        except Exception as e:
            trends['error'] = str(e)
        
        return trends


import subprocess
import sys