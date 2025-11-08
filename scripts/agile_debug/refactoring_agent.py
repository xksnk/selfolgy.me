"""
⚙️ Refactoring Agent - Саб-агент рефакторинга для швейцарской точности
Интеллектуальный рефакторинг кода с сохранением функциональности и улучшением архитектуры.
"""

import ast
import asyncio
import json
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
import logging
from dataclasses import dataclass
from enum import Enum
import shutil


class RefactoringType(Enum):
    """Типы рефакторинга"""
    EXTRACT_METHOD = "extract_method"
    EXTRACT_CLASS = "extract_class"
    INLINE_METHOD = "inline_method"
    RENAME_VARIABLE = "rename_variable"
    OPTIMIZE_IMPORTS = "optimize_imports"
    REMOVE_DEAD_CODE = "remove_dead_code"
    IMPROVE_READABILITY = "improve_readability"
    PERFORMANCE_OPTIMIZATION = "performance_optimization"
    ARCHITECTURE_IMPROVEMENT = "architecture_improvement"
    CODE_SMELL_REMOVAL = "code_smell_removal"


class RefactoringRisk(Enum):
    """Уровни риска рефакторинга"""
    SAFE = "safe"           # Безопасный - не влияет на логику
    LOW = "low"             # Низкий - минимальное влияние
    MEDIUM = "medium"       # Средний - может повлиять на поведение
    HIGH = "high"           # Высокий - значительные изменения
    CRITICAL = "critical"   # Критический - может сломать систему


@dataclass
class RefactoringOperation:
    """Операция рефакторинга"""
    operation_id: str
    refactoring_type: RefactoringType
    target_file: Path
    target_function: Optional[str]
    target_class: Optional[str]
    description: str
    changes_preview: List[str]
    risk_level: RefactoringRisk
    estimated_improvement: float  # 0.0-1.0
    dependencies_affected: List[str]
    tests_required: List[str]


class RefactoringAgent:
    """
    🎯 Интеллектуальный агент рефакторинга
    
    Принципы:
    - Швейцарская точность: минимальные изменения, максимальный эффект
    - Безопасность: всегда создавать бэкапы и валидировать изменения
    - Интеллектуальность: использовать статический анализ для принятия решений
    - Обучение: улучшать качество рефакторинга на основе результатов
    - Интеграция: работать в связке с отладчиком и мониторингом
    """
    
    def __init__(self):
        self.refactoring_start = datetime.now()
        self.refactoring_db_path = Path('data/refactoring_history.db')
        self.refactoring_db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.backup_dir = Path('backups/refactoring')
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # История рефакторинга
        self.refactoring_history = []
        
        # Настройка базы данных
        self._setup_refactoring_database()
        
        # Анализаторы кода (будут инициализированы при необходимости)
        self.code_analyzers = []
        
        self.logger = logging.getLogger(__name__)
    
    def _setup_refactoring_database(self):
        """Настройка базы данных рефакторинга"""
        conn = sqlite3.connect(self.refactoring_db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS refactoring_operations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation_id TEXT UNIQUE NOT NULL,
                refactoring_type TEXT NOT NULL,
                target_file TEXT NOT NULL,
                target_function TEXT,
                target_class TEXT,
                description TEXT NOT NULL,
                risk_level TEXT NOT NULL,
                estimated_improvement REAL,
                backup_path TEXT,
                success BOOLEAN NOT NULL,
                actual_improvement REAL,
                side_effects TEXT,  -- JSON
                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                validation_results TEXT  -- JSON
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS code_quality_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                complexity_score REAL,
                duplication_score REAL,
                readability_score REAL,
                performance_score REAL,
                total_quality_score REAL,
                measured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS refactoring_recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recommendation_id TEXT UNIQUE NOT NULL,
                target_component TEXT NOT NULL,
                refactoring_type TEXT NOT NULL,
                priority TEXT NOT NULL,
                description TEXT NOT NULL,
                estimated_effort_hours REAL,
                potential_improvement REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                applied BOOLEAN DEFAULT FALSE,
                applied_at TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    async def perform_intelligent_refactoring(self, debug_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Выполнение интеллектуального рефакторинга на основе результатов отладки
        
        Args:
            debug_results: Результаты отладки для определения областей рефакторинга
        
        Returns:
            Результаты рефакторинга
        """
        refactoring_results = {
            'timestamp': datetime.now().isoformat(),
            'analysis_phase': {},
            'refactoring_opportunities': [],
            'refactorings_applied': [],
            'quality_improvements': {},
            'risk_assessment': {},
            'performance_impact': {},
            'recommendations_for_future': []
        }
        
        try:
            # Фаза анализа кода
            print("    🔍 Analyzing code for refactoring opportunities...")
            refactoring_results['analysis_phase'] = await self._analyze_codebase_for_refactoring()
            
            # Выявление возможностей рефакторинга на основе отладки
            debug_opportunities = await self._extract_refactoring_opportunities_from_debug(debug_results)
            refactoring_results['refactoring_opportunities'] = debug_opportunities
            
            # Приоритизация рефакторинга
            prioritized_operations = await self._prioritize_refactoring_operations(debug_opportunities)
            
            # Применение безопасных рефакторингов
            for operation in prioritized_operations:
                if operation['risk_level'] in ['safe', 'low']:
                    refactor_result = await self._apply_refactoring_operation(operation)
                    
                    if refactor_result['success']:
                        refactoring_results['refactorings_applied'].append(refactor_result)
                    else:
                        refactoring_results['refactoring_opportunities'].append({
                            **operation,
                            'failed_reason': refactor_result.get('error', 'Unknown error')
                        })
            
            # Анализ улучшений качества
            refactoring_results['quality_improvements'] = await self._measure_quality_improvements()
            
            # Оценка рисков
            refactoring_results['risk_assessment'] = await self._assess_refactoring_risks(
                refactoring_results['refactorings_applied']
            )
            
            # Влияние на производительность
            refactoring_results['performance_impact'] = await self._measure_performance_impact()
            
            # Рекомендации для будущего
            refactoring_results['recommendations_for_future'] = await self._generate_future_recommendations(
                refactoring_results
            )
            
        except Exception as e:
            refactoring_results['error'] = str(e)
            self.logger.error(f"Intelligent refactoring failed: {str(e)}")
        
        return refactoring_results
    
    async def _analyze_codebase_for_refactoring(self) -> Dict[str, Any]:
        """Анализ кодовой базы для выявления возможностей рефакторинга"""
        analysis = {
            'files_analyzed': 0,
            'complexity_analysis': {},
            'duplication_analysis': {},
            'code_smells': [],
            'architecture_issues': [],
            'performance_hotspots': []
        }
        
        try:
            # Получение всех Python файлов проекта
            python_files = list(Path('.').rglob('*.py'))
            
            # Исключение виртуального окружения и других не относящихся директорий
            excluded_dirs = {'venv', '.venv', '__pycache__', '.git', 'node_modules'}
            python_files = [
                f for f in python_files 
                if not any(excluded_dir in f.parts for excluded_dir in excluded_dirs)
            ]
            
            analysis['files_analyzed'] = len(python_files)
            
            # Анализ каждого файла
            for py_file in python_files[:20]:  # Ограничение для производительности
                file_analysis = await self._analyze_file_for_refactoring(py_file)
                
                # Сбор результатов анализа
                if file_analysis.get('complexity_issues'):
                    analysis['complexity_analysis'][str(py_file)] = file_analysis['complexity_issues']
                
                if file_analysis.get('code_smells'):
                    analysis['code_smells'].extend([
                        {'file': str(py_file), **smell} for smell in file_analysis['code_smells']
                    ])
                
                if file_analysis.get('performance_issues'):
                    analysis['performance_hotspots'].extend([
                        {'file': str(py_file), **issue} for issue in file_analysis['performance_issues']
                    ])
            
            # Анализ дублирования кода
            analysis['duplication_analysis'] = await self._analyze_code_duplication(python_files)
            
            # Анализ архитектурных проблем
            analysis['architecture_issues'] = await self._analyze_architecture_issues(python_files)
            
        except Exception as e:
            analysis['error'] = str(e)
        
        return analysis
    
    async def _analyze_file_for_refactoring(self, file_path: Path) -> Dict[str, Any]:
        """Анализ отдельного файла для рефакторинга"""
        file_analysis = {
            'complexity_issues': [],
            'code_smells': [],
            'performance_issues': [],
            'readability_issues': []
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Парсинг AST
            try:
                tree = ast.parse(content)
            except SyntaxError as e:
                file_analysis['syntax_error'] = str(e)
                return file_analysis
            
            # Анализ сложности
            complexity_analyzer = ComplexityAnalyzer()
            complexity_issues = complexity_analyzer.analyze(tree)
            file_analysis['complexity_issues'] = complexity_issues
            
            # Анализ запахов кода
            smell_analyzer = CodeSmellAnalyzer()
            smells = smell_analyzer.analyze(tree, content)
            file_analysis['code_smells'] = smells
            
            # Анализ производительности
            performance_analyzer = PerformanceAnalyzer()
            performance_issues = performance_analyzer.analyze(tree, content)
            file_analysis['performance_issues'] = performance_issues
            
            # Анализ читаемости
            readability_analyzer = ReadabilityAnalyzer()
            readability_issues = readability_analyzer.analyze(tree, content)
            file_analysis['readability_issues'] = readability_issues
            
        except Exception as e:
            file_analysis['analysis_error'] = str(e)
        
        return file_analysis
    
    async def _extract_refactoring_opportunities_from_debug(self, debug_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Извлечение возможностей рефакторинга из результатов отладки"""
        opportunities = []
        
        try:
            # Анализ исправлений отладки для определения областей рефакторинга
            fixes_applied = debug_results.get('fixes_applied', [])
            
            for fix in fixes_applied:
                component = fix.get('component', '')
                fix_type = fix.get('fix_type', '')
                
                # На основе типа исправления предлагаем рефакторинг
                if fix_type == 'code_fix':
                    opportunities.append({
                        'type': RefactoringType.IMPROVE_READABILITY.value,
                        'target': component,
                        'reason': f'Multiple code fixes applied to {component}',
                        'priority': 'medium',
                        'estimated_improvement': 0.3
                    })
                
                elif fix_type == 'performance_fix':
                    opportunities.append({
                        'type': RefactoringType.PERFORMANCE_OPTIMIZATION.value,
                        'target': component,
                        'reason': f'Performance issues detected in {component}',
                        'priority': 'high',
                        'estimated_improvement': 0.5
                    })
                
                elif fix_type == 'logic_fix':
                    opportunities.append({
                        'type': RefactoringType.EXTRACT_METHOD.value,
                        'target': component,
                        'reason': f'Complex logic in {component} needs simplification',
                        'priority': 'medium',
                        'estimated_improvement': 0.4
                    })
            
            # Анализ не разрешенных проблем для архитектурного рефакторинга
            unresolved_issues = debug_results.get('unresolved_issues', [])
            
            if len(unresolved_issues) > 3:
                opportunities.append({
                    'type': RefactoringType.ARCHITECTURE_IMPROVEMENT.value,
                    'target': 'system_architecture',
                    'reason': f'{len(unresolved_issues)} unresolved issues suggest architectural problems',
                    'priority': 'high',
                    'estimated_improvement': 0.7
                })
            
            # Анализ повторяющихся проблем
            component_issue_count = defaultdict(int)
            for fix in fixes_applied:
                component_issue_count[fix.get('component', 'unknown')] += 1
            
            for component, issue_count in component_issue_count.items():
                if issue_count > 2:  # Более 2 исправлений в одном компоненте
                    opportunities.append({
                        'type': RefactoringType.CODE_SMELL_REMOVAL.value,
                        'target': component,
                        'reason': f'{issue_count} fixes in {component} suggest code quality issues',
                        'priority': 'high',
                        'estimated_improvement': 0.6
                    })
        
        except Exception as e:
            self.logger.error(f"Failed to extract refactoring opportunities: {str(e)}")
        
        return opportunities
    
    async def _prioritize_refactoring_operations(self, opportunities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Приоритизация операций рефакторинга"""
        try:
            # Расчет приоритета на основе различных факторов
            for opportunity in opportunities:
                priority_score = 0.0
                
                # Базовый приоритет
                priority_map = {'critical': 1.0, 'high': 0.8, 'medium': 0.5, 'low': 0.2}
                priority_score += priority_map.get(opportunity.get('priority', 'low'), 0.2)
                
                # Оценка улучшения
                estimated_improvement = opportunity.get('estimated_improvement', 0.0)
                priority_score += estimated_improvement
                
                # Тип рефакторинга (некоторые безопаснее других)
                refactor_type = opportunity.get('type', '')
                if refactor_type in ['optimize_imports', 'improve_readability']:
                    priority_score += 0.3  # Безопасные операции
                elif refactor_type in ['performance_optimization']:
                    priority_score += 0.5  # Высокая польза
                elif refactor_type in ['architecture_improvement']:
                    priority_score += 0.4  # Долгосрочная польза
                
                opportunity['priority_score'] = priority_score
            
            # Сортировка по приоритету
            opportunities.sort(key=lambda x: x.get('priority_score', 0), reverse=True)
            
            return opportunities
            
        except Exception as e:
            self.logger.error(f"Failed to prioritize refactoring operations: {str(e)}")
            return opportunities
    
    async def _apply_refactoring_operation(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Применение операции рефакторинга"""
        operation_id = f"refactor_{int(datetime.now().timestamp())}_{operation.get('type', 'unknown')}"
        
        result = {
            'operation_id': operation_id,
            'success': False,
            'changes_made': [],
            'backup_created': False,
            'validation_passed': False,
            'improvement_measured': 0.0,
            'side_effects': []
        }
        
        start_time = datetime.now()
        
        try:
            target_file = operation.get('target', '')
            refactor_type = operation.get('type', '')
            
            # Получение файлов для рефакторинга
            target_files = await self._resolve_target_files(target_file)
            
            if not target_files:
                result['error'] = f"No files found for target: {target_file}"
                return result
            
            # Создание бэкапа
            backup_dir = await self._create_refactoring_backup(target_files, operation_id)
            result['backup_created'] = backup_dir is not None
            result['backup_path'] = str(backup_dir) if backup_dir else None
            
            # Применение рефакторинга в зависимости от типа
            if refactor_type == RefactoringType.OPTIMIZE_IMPORTS.value:
                success = await self._optimize_imports(target_files)
            elif refactor_type == RefactoringType.IMPROVE_READABILITY.value:
                success = await self._improve_readability(target_files)
            elif refactor_type == RefactoringType.REMOVE_DEAD_CODE.value:
                success = await self._remove_dead_code(target_files)
            elif refactor_type == RefactoringType.PERFORMANCE_OPTIMIZATION.value:
                success = await self._optimize_performance(target_files)
            elif refactor_type == RefactoringType.CODE_SMELL_REMOVAL.value:
                success = await self._remove_code_smells(target_files)
            else:
                success = await self._apply_generic_refactoring(target_files, refactor_type)
            
            result['success'] = success
            
            if success:
                # Валидация изменений
                validation_result = await self._validate_refactoring(target_files)
                result['validation_passed'] = validation_result['valid']
                result['validation_details'] = validation_result
                
                if not validation_result['valid']:
                    # Откат при неудачной валидации
                    if backup_dir:
                        await self._rollback_refactoring(backup_dir, target_files)
                    result['success'] = False
                    result['rollback_performed'] = True
                else:
                    # Измерение улучшений
                    improvement = await self._measure_improvement(target_files, backup_dir)
                    result['improvement_measured'] = improvement
            
            # Сохранение результатов
            execution_time = (datetime.now() - start_time).total_seconds()
            result['execution_time'] = execution_time
            
            await self._save_refactoring_result(operation, result)
            
        except Exception as e:
            result['error'] = str(e)
            self.logger.error(f"Refactoring operation failed: {str(e)}")
        
        return result
    
    async def _resolve_target_files(self, target: str) -> List[Path]:
        """Определение файлов для рефакторинга"""
        target_files = []
        
        try:
            if target == 'system_architecture':
                # Все основные файлы системы
                main_dirs = ['selfology_bot', 'scripts']
                for main_dir in main_dirs:
                    dir_path = Path(main_dir)
                    if dir_path.exists():
                        target_files.extend(dir_path.rglob('*.py'))
            
            elif target.endswith('.py'):
                # Конкретный файл
                file_path = Path(target)
                if file_path.exists():
                    target_files.append(file_path)
            
            elif '/' in target:
                # Директория или модуль
                dir_path = Path(target)
                if dir_path.exists():
                    if dir_path.is_dir():
                        target_files.extend(dir_path.rglob('*.py'))
                    else:
                        target_files.append(dir_path)
            
            else:
                # Поиск по имени компонента
                search_patterns = [
                    f"**/{target}.py",
                    f"**/*/{ target}.py",
                    f"selfology_bot/**/{target}*.py"
                ]
                
                for pattern in search_patterns:
                    matches = list(Path('.').glob(pattern))
                    target_files.extend(matches)
                    if matches:  # Если нашли, прекращаем поиск
                        break
        
        except Exception as e:
            self.logger.error(f"Failed to resolve target files: {str(e)}")
        
        # Удаление дубликатов
        target_files = list(set(target_files))
        return target_files
    
    async def _create_refactoring_backup(self, files: List[Path], operation_id: str) -> Optional[Path]:
        """Создание бэкапа для рефакторинга"""
        try:
            backup_path = self.backup_dir / operation_id
            backup_path.mkdir(parents=True, exist_ok=True)
            
            for file_path in files:
                if file_path.exists():
                    # Сохранение структуры директорий
                    relative_path = file_path.relative_to(Path.cwd())
                    backup_file_path = backup_path / relative_path
                    backup_file_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    shutil.copy2(file_path, backup_file_path)
            
            self.logger.info(f"Refactoring backup created: {backup_path}")
            return backup_path
            
        except Exception as e:
            self.logger.error(f"Failed to create refactoring backup: {str(e)}")
            return None
    
    async def _optimize_imports(self, files: List[Path]) -> bool:
        """Оптимизация импортов"""
        try:
            success_count = 0
            
            for file_path in files:
                try:
                    # Использование isort для оптимизации импортов
                    result = subprocess.run(
                        ['python', '-m', 'isort', '--check-only', '--diff', str(file_path)],
                        capture_output=True, text=True, timeout=30
                    )
                    
                    if result.returncode != 0:  # Есть что оптимизировать
                        # Применение оптимизации
                        optimize_result = subprocess.run(
                            ['python', '-m', 'isort', str(file_path)],
                            capture_output=True, text=True, timeout=30
                        )
                        
                        if optimize_result.returncode == 0:
                            success_count += 1
                            self.logger.info(f"Optimized imports in {file_path}")
                
                except subprocess.TimeoutExpired:
                    self.logger.warning(f"Import optimization timeout for {file_path}")
                except Exception as e:
                    self.logger.error(f"Import optimization failed for {file_path}: {str(e)}")
            
            return success_count > 0
            
        except Exception as e:
            self.logger.error(f"Import optimization failed: {str(e)}")
            return False
    
    async def _improve_readability(self, files: List[Path]) -> bool:
        """Улучшение читаемости кода"""
        try:
            success_count = 0
            
            for file_path in files:
                try:
                    # Использование black для форматирования
                    result = subprocess.run(
                        ['python', '-m', 'black', '--check', str(file_path)],
                        capture_output=True, text=True, timeout=30
                    )
                    
                    if result.returncode != 0:  # Требует форматирования
                        # Применение форматирования
                        format_result = subprocess.run(
                            ['python', '-m', 'black', str(file_path)],
                            capture_output=True, text=True, timeout=30
                        )
                        
                        if format_result.returncode == 0:
                            success_count += 1
                            self.logger.info(f"Improved readability of {file_path}")
                
                except subprocess.TimeoutExpired:
                    self.logger.warning(f"Readability improvement timeout for {file_path}")
                except Exception as e:
                    self.logger.error(f"Readability improvement failed for {file_path}: {str(e)}")
            
            return success_count > 0
            
        except Exception as e:
            self.logger.error(f"Readability improvement failed: {str(e)}")
            return False
    
    async def _validate_refactoring(self, files: List[Path]) -> Dict[str, Any]:
        """Валидация результатов рефакторинга"""
        validation = {
            'valid': True,
            'syntax_valid': True,
            'imports_valid': True,
            'functionality_preserved': True,
            'performance_impact': 'neutral',
            'warnings': []
        }
        
        try:
            # Валидация синтаксиса
            for file_path in files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    ast.parse(content)
                
                except SyntaxError as e:
                    validation['valid'] = False
                    validation['syntax_valid'] = False
                    validation['syntax_errors'] = validation.get('syntax_errors', [])
                    validation['syntax_errors'].append({
                        'file': str(file_path),
                        'error': str(e)
                    })
            
            # Валидация импортов (компиляция)
            for file_path in files:
                try:
                    result = subprocess.run(
                        [sys.executable, '-m', 'py_compile', str(file_path)],
                        capture_output=True, text=True, timeout=30
                    )
                    
                    if result.returncode != 0:
                        validation['imports_valid'] = False
                        validation['valid'] = False
                        validation['import_errors'] = validation.get('import_errors', [])
                        validation['import_errors'].append({
                            'file': str(file_path),
                            'error': result.stderr
                        })
                
                except subprocess.TimeoutExpired:
                    validation['warnings'].append(f"Import validation timeout: {file_path}")
            
            # Быстрый тест функциональности (если есть тесты)
            test_result = await self._run_quick_functionality_test()
            if not test_result['success']:
                validation['functionality_preserved'] = False
                validation['valid'] = False
                validation['functionality_errors'] = test_result.get('errors', [])
        
        except Exception as e:
            validation['valid'] = False
            validation['validation_error'] = str(e)
        
        return validation
    
    async def _run_quick_functionality_test(self) -> Dict[str, Any]:
        """Быстрый тест функциональности после рефакторинга"""
        test_result = {
            'success': True,
            'tests_run': 0,
            'errors': []
        }
        
        try:
            # Попытка запуска основных тестов если они есть
            test_dirs = ['tests', 'test']
            test_files_found = False
            
            for test_dir in test_dirs:
                test_path = Path(test_dir)
                if test_path.exists():
                    test_files = list(test_path.rglob('test_*.py'))
                    if test_files:
                        test_files_found = True
                        
                        # Запуск быстрых тестов
                        result = subprocess.run(
                            ['python', '-m', 'pytest', str(test_path), '--tb=short', '-x'],  # Остановка на первой ошибке
                            capture_output=True, text=True, timeout=60
                        )
                        
                        test_result['tests_run'] = len(test_files)
                        
                        if result.returncode != 0:
                            test_result['success'] = False
                            test_result['errors'].append(result.stdout + result.stderr)
                        
                        break  # Запускаем только первую найденную тестовую директорию
            
            if not test_files_found:
                # Если нет тестов, пытаемся простую проверку импорта основных модулей
                main_modules = ['selfology_bot', 'scripts.agile_debug_system']
                
                for module in main_modules:
                    try:
                        result = subprocess.run(
                            [sys.executable, '-c', f'import {module}'],
                            capture_output=True, text=True, timeout=10
                        )
                        
                        if result.returncode != 0:
                            test_result['success'] = False
                            test_result['errors'].append(f"Import test failed for {module}: {result.stderr}")
                    
                    except subprocess.TimeoutExpired:
                        test_result['errors'].append(f"Import test timeout for {module}")
        
        except Exception as e:
            test_result['success'] = False
            test_result['errors'].append(str(e))
        
        return test_result
    
    async def _measure_improvement(self, files: List[Path], backup_dir: Optional[Path]) -> float:
        """Измерение улучшения после рефакторинга"""
        try:
            if not backup_dir:
                return 0.0
            
            # Сравнение метрик до и после
            improvement_score = 0.0
            
            for file_path in files:
                try:
                    # Текущие метрики
                    current_analysis = await self._analyze_file_for_refactoring(file_path)
                    
                    # Метрики до рефакторинга (из бэкапа)
                    backup_file = backup_dir / file_path.relative_to(Path.cwd())
                    if backup_file.exists():
                        original_analysis = await self._analyze_file_for_refactoring(backup_file)
                        
                        # Сравнение метрик
                        complexity_improvement = len(original_analysis.get('complexity_issues', [])) - \
                                               len(current_analysis.get('complexity_issues', []))
                        
                        smell_improvement = len(original_analysis.get('code_smells', [])) - \
                                          len(current_analysis.get('code_smells', []))
                        
                        # Нормализация улучшений (примерная оценка)
                        file_improvement = (complexity_improvement * 0.4 + smell_improvement * 0.3) / 10
                        improvement_score += max(0, min(1, file_improvement))
                
                except Exception as e:
                    self.logger.warning(f"Failed to measure improvement for {file_path}: {str(e)}")
            
            # Среднее улучшение по всем файлам
            if files:
                improvement_score = improvement_score / len(files)
            
            return improvement_score
            
        except Exception as e:
            self.logger.error(f"Failed to measure improvement: {str(e)}")
            return 0.0
    
    async def _rollback_refactoring(self, backup_dir: Path, files: List[Path]) -> bool:
        """Откат рефакторинга"""
        try:
            for file_path in files:
                backup_file = backup_dir / file_path.relative_to(Path.cwd())
                if backup_file.exists():
                    shutil.copy2(backup_file, file_path)
            
            self.logger.info(f"Refactoring rolled back from {backup_dir}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to rollback refactoring: {str(e)}")
            return False
    
    async def _save_refactoring_result(self, operation: Dict[str, Any], result: Dict[str, Any]):
        """Сохранение результата рефакторинга"""
        try:
            conn = sqlite3.connect(self.refactoring_db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO refactoring_operations 
                (operation_id, refactoring_type, target_file, description, 
                 risk_level, estimated_improvement, success, actual_improvement, 
                 side_effects, validation_results, backup_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result['operation_id'],
                operation.get('type', 'unknown'),
                operation.get('target', 'unknown'),
                operation.get('reason', ''),
                operation.get('risk_level', 'medium'),
                operation.get('estimated_improvement', 0.0),
                result['success'],
                result.get('improvement_measured', 0.0),
                json.dumps(result.get('side_effects', [])),
                json.dumps(result.get('validation_details', {})),
                result.get('backup_path')
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Failed to save refactoring result: {str(e)}")
    
    # Заглушки для конкретных типов рефакторинга (будут реализованы по необходимости)
    async def _remove_dead_code(self, files: List[Path]) -> bool:
        return False  # Не реализовано
    
    async def _optimize_performance(self, files: List[Path]) -> bool:
        return False  # Не реализовано
    
    async def _remove_code_smells(self, files: List[Path]) -> bool:
        return False  # Не реализовано
    
    async def _apply_generic_refactoring(self, files: List[Path], refactor_type: str) -> bool:
        return False  # Не реализовано
    
    async def _analyze_code_duplication(self, files: List[Path]) -> Dict[str, Any]:
        return {'status': 'not_implemented'}
    
    async def _analyze_architecture_issues(self, files: List[Path]) -> List[Dict[str, Any]]:
        return []
    
    async def _measure_quality_improvements(self) -> Dict[str, Any]:
        return {'status': 'not_implemented'}
    
    async def _assess_refactoring_risks(self, applied_refactorings: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {'status': 'not_implemented'}
    
    async def _measure_performance_impact(self) -> Dict[str, Any]:
        return {'status': 'not_implemented'}
    
    async def _generate_future_recommendations(self, refactoring_results: Dict[str, Any]) -> List[Dict[str, str]]:
        return []


# Анализаторы кода (упрощенные версии)
class ComplexityAnalyzer:
    """Анализатор сложности кода"""
    
    def analyze(self, tree: ast.AST) -> List[Dict[str, Any]]:
        issues = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Простой подсчет вложенности
                complexity = self._calculate_complexity(node)
                if complexity > 10:
                    issues.append({
                        'type': 'high_complexity',
                        'function': node.name,
                        'complexity_score': complexity,
                        'line': node.lineno
                    })
        
        return issues
    
    def _calculate_complexity(self, node: ast.FunctionDef) -> int:
        # Упрощенный расчет цикломатической сложности
        complexity = 1
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        
        return complexity


class CodeSmellAnalyzer:
    """Анализатор запахов кода"""
    
    def analyze(self, tree: ast.AST, content: str) -> List[Dict[str, Any]]:
        smells = []
        
        # Длинные функции
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_lines = node.end_lineno - node.lineno if hasattr(node, 'end_lineno') else 0
                if func_lines > 50:
                    smells.append({
                        'type': 'long_function',
                        'function': node.name,
                        'lines': func_lines,
                        'line': node.lineno
                    })
        
        # Много параметров
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                param_count = len(node.args.args)
                if param_count > 5:
                    smells.append({
                        'type': 'too_many_parameters',
                        'function': node.name,
                        'parameter_count': param_count,
                        'line': node.lineno
                    })
        
        return smells


class PerformanceAnalyzer:
    """Анализатор производительности"""
    
    def analyze(self, tree: ast.AST, content: str) -> List[Dict[str, Any]]:
        issues = []
        
        # Поиск неэффективных паттернов
        for node in ast.walk(tree):
            # Вложенные циклы
            if isinstance(node, (ast.For, ast.While)):
                for child in ast.walk(node):
                    if isinstance(child, (ast.For, ast.While)) and child != node:
                        issues.append({
                            'type': 'nested_loops',
                            'line': node.lineno,
                            'description': 'Potentially inefficient nested loops'
                        })
                        break
        
        return issues


class ReadabilityAnalyzer:
    """Анализатор читаемости"""
    
    def analyze(self, tree: ast.AST, content: str) -> List[Dict[str, Any]]:
        issues = []
        
        # Отсутствие документации
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if not ast.get_docstring(node):
                    issues.append({
                        'type': 'missing_docstring',
                        'function': node.name,
                        'line': node.lineno
                    })
        
        return issues


import sqlite3
import sys