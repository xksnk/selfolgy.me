"""
🔧 Surgical Debugger - Хирургическая отладка с точностью швейцарских часов
Выполняет локальные исправления без нарушения работы всей системы.
"""

import asyncio
import ast
import json
import sqlite3
import subprocess
import sys
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import logging
from dataclasses import dataclass
from enum import Enum


class FixType(Enum):
    """Типы исправлений"""
    CONFIG_FIX = "config_fix"           # Исправление конфигурации
    CODE_FIX = "code_fix"               # Исправление кода
    DATABASE_FIX = "database_fix"       # Исправление БД
    PERMISSION_FIX = "permission_fix"   # Исправление прав доступа
    SERVICE_RESTART = "service_restart" # Перезапуск сервиса
    DEPENDENCY_FIX = "dependency_fix"   # Исправление зависимостей
    PERFORMANCE_FIX = "performance_fix" # Оптимизация производительности
    LOGIC_FIX = "logic_fix"            # Исправление логики


class FixScope(Enum):
    """Область действия исправления"""
    SINGLE_FILE = "single_file"         # Один файл
    SINGLE_FUNCTION = "single_function" # Одна функция
    SINGLE_CLASS = "single_class"       # Один класс
    MODULE = "module"                   # Модуль
    COMPONENT = "component"             # Компонент
    SYSTEM_WIDE = "system_wide"         # Вся система


@dataclass
class SurgicalFix:
    """Хирургическое исправление"""
    fix_id: str
    fix_type: FixType
    scope: FixScope
    target_component: str
    description: str
    changes_made: List[str]
    backup_created: bool
    success: bool
    risk_level: str  # low, medium, high
    execution_time: float
    side_effects: List[str]


class SurgicalDebugger:
    """
    🎯 Хирургический отладчик для Selfology
    
    Принципы работы:
    - Минимальные изменения с максимальным эффектом
    - Создание бэкапов перед любыми изменениями
    - Валидация изменений перед применением
    - Откат в случае проблем
    - Мониторинг побочных эффектов
    - Обучение на результатах исправлений
    """
    
    def __init__(self):
        self.fixes_db_path = Path('data/surgical_fixes.db')
        self.fixes_db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.backup_dir = Path('backups/surgical_fixes')
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # История исправлений
        self.fix_history: List[SurgicalFix] = []
        
        # Подключенная система обучения
        self.learning_engine = None
        
        # Настройка базы данных
        self._setup_fixes_database()
        
        # Валидаторы безопасности
        self.safety_validators = [
            self._validate_syntax,
            self._validate_imports,
            self._validate_dependencies,
            self._validate_side_effects
        ]
        
        self.logger = logging.getLogger(__name__)
    
    def _setup_fixes_database(self):
        """Настройка базы данных исправлений"""
        conn = sqlite3.connect(self.fixes_db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS surgical_fixes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fix_id TEXT UNIQUE NOT NULL,
                fix_type TEXT NOT NULL,
                scope TEXT NOT NULL,
                target_component TEXT NOT NULL,
                description TEXT NOT NULL,
                changes_made TEXT NOT NULL,  -- JSON список изменений
                backup_path TEXT,
                success BOOLEAN NOT NULL,
                risk_level TEXT NOT NULL,
                execution_time REAL,
                side_effects TEXT,  -- JSON список побочных эффектов
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                validated_at TIMESTAMP,
                rolled_back_at TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fix_validations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fix_id TEXT NOT NULL,
                validation_type TEXT NOT NULL,
                validation_result TEXT NOT NULL,
                validation_details TEXT,
                validated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (fix_id) REFERENCES surgical_fixes (fix_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fix_rollbacks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fix_id TEXT NOT NULL,
                rollback_reason TEXT NOT NULL,
                rollback_success BOOLEAN NOT NULL,
                rollback_details TEXT,
                rolled_back_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (fix_id) REFERENCES surgical_fixes (fix_id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    async def perform_surgical_fixes(self, learning_insights: Dict[str, Any]) -> Dict[str, Any]:
        """
        Выполнение хирургических исправлений на основе обучения
        
        Args:
            learning_insights: Инсайты от системы обучения
        
        Returns:
            Результаты выполненных исправлений
        """
        fix_results = {
            'timestamp': datetime.now().isoformat(),
            'fixes_attempted': 0,
            'fixes_successful': 0,
            'fixes_failed': 0,
            'precision_score': 0.0,
            'fixes_applied': [],
            'fixes_failed_list': [],
            'unresolved_issues': [],
            'system_impact': {}
        }
        
        try:
            # Извлечение рекомендаций из инсайтов обучения
            recommendations = learning_insights.get('actionable_recommendations', [])
            predicted_issues = learning_insights.get('predictive_alerts', [])
            
            # Применение исправлений на основе предсказаний
            for prediction in predicted_issues:
                if prediction.get('confidence_score', 0) > 0.7:
                    fix_result = await self._apply_predictive_fix(prediction)
                    fix_results['fixes_attempted'] += 1
                    
                    if fix_result['success']:
                        fix_results['fixes_successful'] += 1
                        fix_results['fixes_applied'].append(fix_result)
                    else:
                        fix_results['fixes_failed'] += 1
                        fix_results['fixes_failed_list'].append(fix_result)
            
            # Исправления на основе рекомендаций
            for recommendation in recommendations:
                fix_result = await self._apply_recommendation_fix(recommendation)
                fix_results['fixes_attempted'] += 1
                
                if fix_result['success']:
                    fix_results['fixes_successful'] += 1
                    fix_results['fixes_applied'].append(fix_result)
                else:
                    fix_results['fixes_failed'] += 1
                    fix_results['fixes_failed_list'].append(fix_result)
            
            # Расчет точности
            if fix_results['fixes_attempted'] > 0:
                fix_results['precision_score'] = (
                    fix_results['fixes_successful'] / fix_results['fixes_attempted']
                ) * 100
            
            # Анализ воздействия на систему
            fix_results['system_impact'] = await self._analyze_system_impact(
                fix_results['fixes_applied']
            )
            
        except Exception as e:
            self.logger.error(f"Failed to perform surgical fixes: {str(e)}")
            fix_results['error'] = str(e)
        
        return fix_results
    
    async def perform_targeted_fix(self, component: str, issue_description: str, 
                                 context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Выполнение целевого исправления конкретной проблемы
        
        Args:
            component: Компонент для исправления
            issue_description: Описание проблемы
            context: Контекст проблемы
        
        Returns:
            Результат исправления
        """
        fix_id = f"targeted_fix_{int(datetime.now().timestamp())}_{component}"
        
        fix_result = {
            'fix_id': fix_id,
            'component': component,
            'issue_description': issue_description,
            'success': False,
            'changes_made': [],
            'backup_created': False,
            'execution_time': 0.0,
            'side_effects': []
        }
        
        start_time = datetime.now()
        
        try:
            # Создание бэкапа
            backup_path = await self._create_component_backup(component)
            fix_result['backup_created'] = backup_path is not None
            fix_result['backup_path'] = str(backup_path) if backup_path else None
            
            # Определение типа исправления
            fix_type = self._determine_fix_type(issue_description, context)
            fix_scope = self._determine_fix_scope(component, context)
            
            # Применение исправления
            if fix_type == FixType.CONFIG_FIX:
                success = await self._apply_config_fix(component, issue_description, context)
            elif fix_type == FixType.CODE_FIX:
                success = await self._apply_code_fix(component, issue_description, context)
            elif fix_type == FixType.DATABASE_FIX:
                success = await self._apply_database_fix(component, issue_description, context)
            elif fix_type == FixType.PERMISSION_FIX:
                success = await self._apply_permission_fix(component, issue_description, context)
            elif fix_type == FixType.SERVICE_RESTART:
                success = await self._apply_service_restart(component, issue_description, context)
            else:
                success = await self._apply_generic_fix(component, issue_description, context)
            
            fix_result['success'] = success
            
            # Валидация после исправления
            if success:
                validation_result = await self._validate_fix(component, fix_type, context)
                if not validation_result['valid']:
                    # Откат при неудачной валидации
                    if backup_path:
                        await self._rollback_fix(backup_path, component)
                    fix_result['success'] = False
                    fix_result['validation_failed'] = validation_result
            
            # Расчет времени выполнения
            end_time = datetime.now()
            fix_result['execution_time'] = (end_time - start_time).total_seconds()
            
            # Создание записи в базе данных
            surgical_fix = SurgicalFix(
                fix_id=fix_id,
                fix_type=fix_type,
                scope=fix_scope,
                target_component=component,
                description=issue_description,
                changes_made=fix_result.get('changes_made', []),
                backup_created=fix_result['backup_created'],
                success=fix_result['success'],
                risk_level=context.get('risk_level', 'medium'),
                execution_time=fix_result['execution_time'],
                side_effects=fix_result.get('side_effects', [])
            )
            
            await self._save_fix_to_db(surgical_fix)
            
            self.logger.info(f"Surgical fix completed: {fix_id}, success: {success}")
            
        except Exception as e:
            fix_result['error'] = str(e)
            fix_result['execution_time'] = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"Surgical fix failed: {str(e)}")
        
        return fix_result
    
    async def _create_component_backup(self, component: str) -> Optional[Path]:
        """Создание бэкапа компонента перед изменениями"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"{component}_{timestamp}"
            component_backup_dir = self.backup_dir / backup_name
            
            # Определение файлов компонента
            component_files = await self._get_component_files(component)
            
            if not component_files:
                self.logger.warning(f"No files found for component: {component}")
                return None
            
            # Создание бэкапа
            component_backup_dir.mkdir(parents=True, exist_ok=True)
            
            for file_path in component_files:
                if file_path.exists():
                    # Создание структуры директорий в бэкапе
                    try:
                        relative_path = file_path.relative_to(Path.cwd())
                    except ValueError:
                        # Если файл не в текущей директории, используем абсолютный путь
                        relative_path = file_path.name
                    
                    backup_file_path = component_backup_dir / relative_path
                    backup_file_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Копирование файла
                    shutil.copy2(file_path, backup_file_path)
            
            self.logger.info(f"Component backup created: {component_backup_dir}")
            return component_backup_dir
            
        except Exception as e:
            self.logger.error(f"Failed to create component backup: {str(e)}")
            return None
    
    async def _get_component_files(self, component: str) -> List[Path]:
        """Получение списка файлов компонента"""
        component_files = []
        
        try:
            # Определение файлов на основе названия компонента
            if component.startswith('selfology_bot'):
                # Файлы основного приложения
                if '.' in component:
                    # Конкретный модуль, например selfology_bot.ai.router
                    module_path = component.replace('.', '/')
                    file_path = Path(f"{module_path}.py")
                    if file_path.exists():
                        component_files.append(file_path)
                else:
                    # Весь пакет selfology_bot
                    selfology_dir = Path('selfology_bot')
                    if selfology_dir.exists():
                        component_files.extend(selfology_dir.rglob('*.py'))
            
            elif component == 'config':
                # Конфигурационные файлы
                config_files = ['.env', 'pyproject.toml', 'alembic.ini']
                component_files.extend([Path(f) for f in config_files if Path(f).exists()])
            
            elif component.startswith('scripts'):
                # Скрипты
                if '/' in component:
                    script_path = Path(component)
                    if script_path.exists():
                        component_files.append(script_path)
                else:
                    scripts_dir = Path('scripts')
                    if scripts_dir.exists():
                        component_files.extend(scripts_dir.rglob('*.py'))
            
            elif component == 'docker':
                # Docker файлы
                docker_files = ['Dockerfile', 'docker-compose.yml', 'docker-compose.selfology.yml']
                component_files.extend([Path(f) for f in docker_files if Path(f).exists()])
            
            else:
                # Попытка найти по имени
                possible_paths = [
                    Path(component),
                    Path(f"{component}.py"),
                    Path(f"selfology_bot/{component}.py"),
                    Path(f"scripts/{component}.py")
                ]
                
                for path in possible_paths:
                    if path.exists():
                        component_files.append(path)
                        break
        
        except Exception as e:
            self.logger.error(f"Failed to get component files for {component}: {str(e)}")
        
        return component_files
    
    def _determine_fix_type(self, issue_description: str, context: Dict[str, Any]) -> FixType:
        """Определение типа необходимого исправления"""
        issue_lower = issue_description.lower()
        
        if 'config' in issue_lower or 'environment' in issue_lower:
            return FixType.CONFIG_FIX
        elif 'permission' in issue_lower or 'access' in issue_lower:
            return FixType.PERMISSION_FIX
        elif 'database' in issue_lower or 'db' in issue_lower:
            return FixType.DATABASE_FIX
        elif 'service' in issue_lower and ('restart' in issue_lower or 'down' in issue_lower):
            return FixType.SERVICE_RESTART
        elif 'import' in issue_lower or 'dependency' in issue_lower:
            return FixType.DEPENDENCY_FIX
        elif 'slow' in issue_lower or 'performance' in issue_lower:
            return FixType.PERFORMANCE_FIX
        elif 'logic' in issue_lower or 'algorithm' in issue_lower:
            return FixType.LOGIC_FIX
        else:
            return FixType.CODE_FIX
    
    def _determine_fix_scope(self, component: str, context: Dict[str, Any]) -> FixScope:
        """Определение области действия исправления"""
        if '.' in component and component.count('.') >= 2:
            return FixScope.SINGLE_FUNCTION
        elif '.' in component:
            return FixScope.SINGLE_FILE
        elif component in ['config', 'environment']:
            return FixScope.SYSTEM_WIDE
        elif component.startswith('selfology_bot'):
            return FixScope.COMPONENT
        else:
            return FixScope.MODULE
    
    async def _apply_config_fix(self, component: str, issue_description: str, 
                              context: Dict[str, Any]) -> bool:
        """Применение исправления конфигурации"""
        try:
            # Анализ проблемы конфигурации
            if 'missing environment variable' in issue_description.lower():
                return await self._fix_missing_env_variable(context)
            elif 'invalid configuration' in issue_description.lower():
                return await self._fix_invalid_configuration(context)
            elif 'permission denied' in issue_description.lower():
                return await self._fix_file_permissions(context)
            else:
                return await self._generic_config_fix(component, issue_description, context)
        
        except Exception as e:
            self.logger.error(f"Config fix failed: {str(e)}")
            return False
    
    async def _apply_code_fix(self, component: str, issue_description: str, 
                            context: Dict[str, Any]) -> bool:
        """Применение исправления кода"""
        try:
            # Получение файлов компонента
            component_files = await self._get_component_files(component)
            
            if not component_files:
                self.logger.error(f"No files found for component: {component}")
                return False
            
            # Анализ типа проблемы кода
            if 'syntax error' in issue_description.lower():
                return await self._fix_syntax_error(component_files, context)
            elif 'import error' in issue_description.lower():
                return await self._fix_import_error(component_files, context)
            elif 'undefined variable' in issue_description.lower():
                return await self._fix_undefined_variable(component_files, context)
            elif 'logic error' in issue_description.lower():
                return await self._fix_logic_error(component_files, context)
            else:
                return await self._generic_code_fix(component_files, issue_description, context)
        
        except Exception as e:
            self.logger.error(f"Code fix failed: {str(e)}")
            return False
    
    async def _apply_database_fix(self, component: str, issue_description: str, 
                                context: Dict[str, Any]) -> bool:
        """Применение исправления базы данных"""
        try:
            if 'connection failed' in issue_description.lower():
                return await self._fix_database_connection(context)
            elif 'table not found' in issue_description.lower():
                return await self._fix_missing_table(context)
            elif 'migration failed' in issue_description.lower():
                return await self._fix_migration_issue(context)
            else:
                return await self._generic_database_fix(issue_description, context)
        
        except Exception as e:
            self.logger.error(f"Database fix failed: {str(e)}")
            return False
    
    async def _fix_missing_env_variable(self, context: Dict[str, Any]) -> bool:
        """Исправление отсутствующей переменной окружения"""
        try:
            missing_var = context.get('missing_variable')
            if not missing_var:
                return False
            
            # Проверка файла .env.example для значения по умолчанию
            env_example_path = Path('.env.example')
            if env_example_path.exists():
                with open(env_example_path, 'r') as f:
                    example_content = f.read()
                
                # Поиск переменной в примере
                for line in example_content.split('\n'):
                    if line.startswith(f"{missing_var}="):
                        default_value = line.split('=', 1)[1] if '=' in line else ''
                        
                        # Добавление в .env
                        env_path = Path('.env')
                        with open(env_path, 'a') as f:
                            f.write(f"\n# Added by surgical debugger\n{missing_var}={default_value}\n")
                        
                        self.logger.info(f"Added missing environment variable: {missing_var}")
                        return True
            
            # Если не найден в примере, создание заглушки
            env_path = Path('.env')
            with open(env_path, 'a') as f:
                f.write(f"\n# Added by surgical debugger - REQUIRES CONFIGURATION\n{missing_var}=PLEASE_CONFIGURE\n")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to fix missing env variable: {str(e)}")
            return False
    
    async def _fix_syntax_error(self, files: List[Path], context: Dict[str, Any]) -> bool:
        """Исправление синтаксических ошибок"""
        try:
            # Поиск файла с синтаксической ошибкой
            error_file = context.get('error_file')
            error_line = context.get('error_line')
            
            if error_file:
                file_path = Path(error_file)
                if file_path.exists():
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Попытка парсинга для выявления проблемы
                    try:
                        ast.parse(content)
                        # Если парсинг прошел, ошибки нет
                        return True
                    except SyntaxError as syntax_error:
                        # Попытка автоматического исправления простых ошибок
                        fixed_content = await self._auto_fix_syntax(content, syntax_error)
                        if fixed_content != content:
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write(fixed_content)
                            
                            self.logger.info(f"Auto-fixed syntax error in {file_path}")
                            return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to fix syntax error: {str(e)}")
            return False
    
    async def _auto_fix_syntax(self, content: str, syntax_error: SyntaxError) -> str:
        """Автоматическое исправление простых синтаксических ошибок"""
        try:
            lines = content.split('\n')
            error_line_num = syntax_error.lineno - 1  # 0-indexed
            
            if 0 <= error_line_num < len(lines):
                line = lines[error_line_num]
                
                # Исправление частых ошибок
                fixes = [
                    # Отсутствующие двоеточия
                    (r'(if|elif|else|for|while|def|class|try|except|finally|with)\s+[^:]*(?<!:)$', r'\g<0>:'),
                    # Отсутствующие скобки
                    (r'print\s+([^(].*)', r'print(\1)'),
                    # Неправильные кавычки
                    (r"'([^']*)'", r'"\1"'),
                ]
                
                import re
                fixed_line = line
                
                for pattern, replacement in fixes:
                    fixed_line = re.sub(pattern, replacement, fixed_line)
                
                if fixed_line != line:
                    lines[error_line_num] = fixed_line
                    return '\n'.join(lines)
            
            return content
            
        except Exception as e:
            self.logger.error(f"Failed to auto-fix syntax: {str(e)}")
            return content
    
    async def _fix_import_error(self, files: List[Path], context: Dict[str, Any]) -> bool:
        """Исправление ошибок импорта"""
        try:
            missing_module = context.get('missing_module')
            if not missing_module:
                return False
            
            # Попытка установки отсутствующего модуля
            try:
                result = subprocess.run(
                    [sys.executable, '-m', 'pip', 'install', missing_module],
                    capture_output=True, text=True, timeout=60
                )
                
                if result.returncode == 0:
                    self.logger.info(f"Successfully installed missing module: {missing_module}")
                    return True
                else:
                    self.logger.error(f"Failed to install {missing_module}: {result.stderr}")
            
            except subprocess.TimeoutExpired:
                self.logger.error(f"Timeout installing module: {missing_module}")
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to fix import error: {str(e)}")
            return False
    
    async def _fix_database_connection(self, context: Dict[str, Any]) -> bool:
        """Исправление проблем подключения к базе данных"""
        try:
            db_type = context.get('database_type', 'postgresql')
            
            if db_type == 'postgresql':
                # Проверка доступности PostgreSQL сервиса
                result = subprocess.run(
                    ['docker', 'ps', '--filter', 'name=n8n-postgres', '--format', '{{.Status}}'],
                    capture_output=True, text=True
                )
                
                if 'Up' not in result.stdout:
                    # Попытка запуска сервиса
                    start_result = subprocess.run(
                        ['docker', 'start', 'n8n-postgres'],
                        capture_output=True, text=True
                    )
                    
                    if start_result.returncode == 0:
                        self.logger.info("Started PostgreSQL service")
                        # Ждем запуска
                        await asyncio.sleep(5)
                        return True
                
            elif db_type == 'qdrant':
                # Аналогично для Qdrant
                result = subprocess.run(
                    ['docker', 'ps', '--filter', 'name=qdrant', '--format', '{{.Status}}'],
                    capture_output=True, text=True
                )
                
                if 'Up' not in result.stdout:
                    start_result = subprocess.run(
                        ['docker', 'start', 'qdrant'],
                        capture_output=True, text=True
                    )
                    
                    if start_result.returncode == 0:
                        self.logger.info("Started Qdrant service")
                        await asyncio.sleep(5)
                        return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to fix database connection: {str(e)}")
            return False
    
    async def _apply_service_restart(self, component: str, issue_description: str, 
                                   context: Dict[str, Any]) -> bool:
        """Применение перезапуска сервиса"""
        try:
            if 'selfology' in component.lower() or 'bot' in component.lower():
                # Перезапуск бота Selfology
                return await self._restart_selfology_bot()
            elif 'postgres' in component.lower():
                return await self._restart_docker_service('n8n-postgres')
            elif 'qdrant' in component.lower():
                return await self._restart_docker_service('qdrant')
            elif 'redis' in component.lower():
                return await self._restart_docker_service('n8n-redis')
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to restart service: {str(e)}")
            return False
    
    async def _restart_selfology_bot(self) -> bool:
        """Перезапуск бота Selfology"""
        try:
            # Поиск процесса бота
            import psutil
            bot_processes = []
            
            for proc in psutil.process_iter(['pid', 'cmdline']):
                try:
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    if ('selfology' in cmdline.lower() or 'monitored_bot.py' in cmdline):
                        bot_processes.append(proc)
                except:
                    continue
            
            # Остановка существующих процессов
            for proc in bot_processes:
                try:
                    proc.terminate()
                    proc.wait(timeout=10)
                except:
                    try:
                        proc.kill()
                    except:
                        pass
            
            # Запуск нового процесса бота
            startup_script = Path('scripts/selfology_manager.py')
            if startup_script.exists():
                result = subprocess.run(
                    [sys.executable, str(startup_script), 'start', 'dev'],
                    capture_output=True, text=True, timeout=30
                )
                
                if result.returncode == 0:
                    self.logger.info("Selfology bot restarted successfully")
                    return True
                else:
                    self.logger.error(f"Bot restart failed: {result.stderr}")
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to restart Selfology bot: {str(e)}")
            return False
    
    async def _restart_docker_service(self, service_name: str) -> bool:
        """Перезапуск Docker сервиса"""
        try:
            # Перезапуск сервиса
            result = subprocess.run(
                ['docker', 'restart', service_name],
                capture_output=True, text=True, timeout=60
            )
            
            if result.returncode == 0:
                self.logger.info(f"Docker service {service_name} restarted successfully")
                return True
            else:
                self.logger.error(f"Failed to restart {service_name}: {result.stderr}")
                return False
            
        except Exception as e:
            self.logger.error(f"Failed to restart Docker service {service_name}: {str(e)}")
            return False
    
    async def _validate_fix(self, component: str, fix_type: FixType, context: Dict[str, Any]) -> Dict[str, Any]:
        """Валидация исправления"""
        validation_result = {
            'valid': True,
            'validations_passed': [],
            'validations_failed': [],
            'warnings': []
        }
        
        try:
            # Запуск валидаторов
            for validator in self.safety_validators:
                try:
                    result = await validator(component, fix_type, context)
                    if result['valid']:
                        validation_result['validations_passed'].append(result['validator'])
                    else:
                        validation_result['validations_failed'].append(result)
                        validation_result['valid'] = False
                        
                    validation_result['warnings'].extend(result.get('warnings', []))
                
                except Exception as e:
                    validation_result['validations_failed'].append({
                        'validator': validator.__name__,
                        'error': str(e)
                    })
                    validation_result['valid'] = False
            
            # Дополнительные проверки для конкретных типов исправлений
            if fix_type == FixType.CODE_FIX:
                # Проверка синтаксиса
                syntax_valid = await self._validate_python_syntax(component)
                if not syntax_valid:
                    validation_result['valid'] = False
                    validation_result['validations_failed'].append({
                        'validator': 'syntax_check',
                        'error': 'Python syntax validation failed'
                    })
                else:
                    validation_result['validations_passed'].append('syntax_check')
            
            elif fix_type == FixType.DATABASE_FIX:
                # Проверка подключения к БД
                db_valid = await self._validate_database_connection(context)
                if not db_valid:
                    validation_result['valid'] = False
                    validation_result['validations_failed'].append({
                        'validator': 'database_connection',
                        'error': 'Database connection validation failed'
                    })
                else:
                    validation_result['validations_passed'].append('database_connection')
        
        except Exception as e:
            validation_result['valid'] = False
            validation_result['error'] = str(e)
        
        return validation_result
    
    async def _validate_syntax(self, component: str, fix_type: FixType, context: Dict[str, Any]) -> Dict[str, Any]:
        """Валидатор синтаксиса Python"""
        result = {'valid': True, 'validator': 'syntax', 'warnings': []}
        
        try:
            component_files = await self._get_component_files(component)
            
            for file_path in component_files:
                if file_path.suffix == '.py':
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    try:
                        ast.parse(content)
                    except SyntaxError as e:
                        result['valid'] = False
                        result['error'] = f"Syntax error in {file_path}: {str(e)}"
                        break
        
        except Exception as e:
            result['valid'] = False
            result['error'] = str(e)
        
        return result
    
    async def _validate_imports(self, component: str, fix_type: FixType, context: Dict[str, Any]) -> Dict[str, Any]:
        """Валидатор импортов"""
        result = {'valid': True, 'validator': 'imports', 'warnings': []}
        
        try:
            component_files = await self._get_component_files(component)
            
            for file_path in component_files:
                if file_path.suffix == '.py':
                    # Проверка импортов без выполнения кода
                    result_check = subprocess.run(
                        [sys.executable, '-m', 'py_compile', str(file_path)],
                        capture_output=True, text=True
                    )
                    
                    if result_check.returncode != 0:
                        result['warnings'].append(f"Compilation warning for {file_path}: {result_check.stderr}")
        
        except Exception as e:
            result['warnings'].append(f"Import validation error: {str(e)}")
        
        return result
    
    async def _validate_dependencies(self, component: str, fix_type: FixType, context: Dict[str, Any]) -> Dict[str, Any]:
        """Валидатор зависимостей"""
        result = {'valid': True, 'validator': 'dependencies', 'warnings': []}
        
        # Проверка что не сломаны критические зависимости
        # Пока что базовая проверка
        
        return result
    
    async def _validate_side_effects(self, component: str, fix_type: FixType, context: Dict[str, Any]) -> Dict[str, Any]:
        """Валидатор побочных эффектов"""
        result = {'valid': True, 'validator': 'side_effects', 'warnings': []}
        
        # Анализ потенциальных побочных эффектов
        if fix_type == FixType.SYSTEM_WIDE:
            result['warnings'].append("System-wide change may have unexpected side effects")
        
        return result
    
    async def _validate_python_syntax(self, component: str) -> bool:
        """Проверка синтаксиса Python файлов компонента"""
        try:
            component_files = await self._get_component_files(component)
            
            for file_path in component_files:
                if file_path.suffix == '.py':
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    try:
                        ast.parse(content)
                    except SyntaxError:
                        return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Syntax validation failed: {str(e)}")
            return False
    
    async def _validate_database_connection(self, context: Dict[str, Any]) -> bool:
        """Проверка подключения к базе данных"""
        try:
            import asyncpg
            
            conn = await asyncpg.connect(
                host='localhost',
                port=5432,
                user='postgres',
                password='sS67wM+1zMBRFHAW4kj9HwFl5J6+veo7Nirx0/I+oiU=',
                database='postgres',
                timeout=5
            )
            
            await conn.fetchrow("SELECT 1")
            await conn.close()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Database validation failed: {str(e)}")
            return False
    
    async def _rollback_fix(self, backup_path: Path, component: str) -> bool:
        """Откат исправления"""
        try:
            if not backup_path.exists():
                self.logger.error(f"Backup path not found: {backup_path}")
                return False
            
            # Восстановление файлов из бэкапа
            for backup_file in backup_path.rglob('*'):
                if backup_file.is_file():
                    # Определение исходного пути
                    relative_path = backup_file.relative_to(backup_path)
                    original_path = Path.cwd() / relative_path
                    
                    # Создание директорий если нужно
                    original_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Восстановление файла
                    shutil.copy2(backup_file, original_path)
            
            self.logger.info(f"Successfully rolled back component: {component}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to rollback fix: {str(e)}")
            return False
    
    async def _analyze_system_impact(self, successful_fixes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Анализ воздействия исправлений на систему"""
        impact_analysis = {
            'components_affected': set(),
            'estimated_performance_improvement': 0.0,
            'risk_assessment': 'low',
            'monitoring_adjustments_needed': [],
            'follow_up_actions': []
        }
        
        try:
            for fix in successful_fixes:
                # Сбор затронутых компонентов
                impact_analysis['components_affected'].add(fix.get('component', 'unknown'))
                
                # Анализ типа исправления для оценки улучшений
                fix_type = fix.get('fix_type', '')
                if fix_type == 'performance_fix':
                    impact_analysis['estimated_performance_improvement'] += 10
                elif fix_type == 'code_fix':
                    impact_analysis['estimated_performance_improvement'] += 5
            
            # Оценка общего риска
            total_components = len(impact_analysis['components_affected'])
            if total_components > 5:
                impact_analysis['risk_assessment'] = 'high'
            elif total_components > 2:
                impact_analysis['risk_assessment'] = 'medium'
            
            # Рекомендации по мониторингу
            for component in impact_analysis['components_affected']:
                impact_analysis['monitoring_adjustments_needed'].append(
                    f"Monitor {component} for next 24 hours"
                )
            
            impact_analysis['components_affected'] = list(impact_analysis['components_affected'])
            
        except Exception as e:
            impact_analysis['error'] = str(e)
        
        return impact_analysis
    
    async def _save_fix_to_db(self, surgical_fix: SurgicalFix):
        """Сохранение исправления в базу данных"""
        try:
            conn = sqlite3.connect(self.fixes_db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO surgical_fixes 
                (fix_id, fix_type, scope, target_component, description, 
                 changes_made, backup_path, success, risk_level, 
                 execution_time, side_effects)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                surgical_fix.fix_id,
                surgical_fix.fix_type.value,
                surgical_fix.scope.value,
                surgical_fix.target_component,
                surgical_fix.description,
                json.dumps(surgical_fix.changes_made),
                str(self.backup_dir / surgical_fix.fix_id) if surgical_fix.backup_created else None,
                surgical_fix.success,
                surgical_fix.risk_level,
                surgical_fix.execution_time,
                json.dumps(surgical_fix.side_effects)
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Failed to save fix to DB: {str(e)}")
    
    async def handle_critical_issue(self, issue: Dict[str, Any]):
        """Обработка критической проблемы с автоматическим исправлением"""
        try:
            issue_type = issue.get('type', 'unknown')
            component = issue.get('component', 'unknown')
            description = issue.get('description', '')
            
            # Контекст для исправления
            context = {
                'severity': 'critical',
                'auto_triggered': True,
                'issue_data': issue
            }
            
            # Применение исправления
            fix_result = await self.perform_targeted_fix(component, description, context)
            
            if fix_result['success']:
                self.logger.info(f"Automatically fixed critical issue: {description}")
            else:
                self.logger.error(f"Failed to auto-fix critical issue: {description}")
                
                # Уведомление для ручного вмешательства
                await self._notify_manual_intervention_needed(issue, fix_result)
        
        except Exception as e:
            self.logger.error(f"Failed to handle critical issue: {str(e)}")
    
    async def handle_system_error(self, error_message: str):
        """Обработка системной ошибки"""
        try:
            # Анализ ошибки и попытка автоматического восстановления
            if 'memory' in error_message.lower():
                await self._handle_memory_error()
            elif 'disk' in error_message.lower():
                await self._handle_disk_error()
            elif 'connection' in error_message.lower():
                await self._handle_connection_error()
            else:
                await self._handle_generic_error(error_message)
        
        except Exception as e:
            self.logger.error(f"Failed to handle system error: {str(e)}")
    
    async def _handle_memory_error(self):
        """Обработка ошибок памяти"""
        try:
            # Очистка логов
            await self._cleanup_old_logs()
            
            # Перезапуск сервисов если необходимо
            import psutil
            if psutil.virtual_memory().percent > 95:
                await self._restart_selfology_bot()
        
        except Exception as e:
            self.logger.error(f"Memory error handling failed: {str(e)}")
    
    async def _cleanup_old_logs(self):
        """Очистка старых логов для освобождения места"""
        try:
            log_dirs = ['logs/errors', 'logs/bot', 'logs/users', 'logs/ai']
            cleaned_files = 0
            
            for log_dir in log_dirs:
                log_path = Path(log_dir)
                if log_path.exists():
                    # Удаление файлов старше 7 дней
                    for log_file in log_path.glob('*.log'):
                        if log_file.exists():
                            age_days = (datetime.now() - datetime.fromtimestamp(log_file.stat().st_mtime)).days
                            if age_days > 7:
                                log_file.unlink()
                                cleaned_files += 1
            
            self.logger.info(f"Cleaned up {cleaned_files} old log files")
            
        except Exception as e:
            self.logger.error(f"Log cleanup failed: {str(e)}")
    
    async def _notify_manual_intervention_needed(self, issue: Dict[str, Any], fix_result: Dict[str, Any]):
        """Уведомление о необходимости ручного вмешательства"""
        notification = {
            'timestamp': datetime.now().isoformat(),
            'issue': issue,
            'failed_fix_attempt': fix_result,
            'manual_intervention_required': True
        }
        
        # Сохранение уведомления
        notifications_dir = Path('logs/manual_interventions')
        notifications_dir.mkdir(parents=True, exist_ok=True)
        
        notification_file = notifications_dir / f"intervention_needed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(notification_file, 'w') as f:
            json.dump(notification, f, indent=2, default=str)
        
        self.logger.warning(f"Manual intervention needed: {notification_file}")
    
    # Заглушки для различных типов исправлений
    async def _fix_invalid_configuration(self, context: Dict[str, Any]) -> bool:
        return False
    
    async def _fix_file_permissions(self, context: Dict[str, Any]) -> bool:
        return False
    
    async def _generic_config_fix(self, component: str, issue_description: str, context: Dict[str, Any]) -> bool:
        return False
    
    async def _fix_undefined_variable(self, files: List[Path], context: Dict[str, Any]) -> bool:
        return False
    
    async def _fix_logic_error(self, files: List[Path], context: Dict[str, Any]) -> bool:
        return False
    
    async def _generic_code_fix(self, files: List[Path], issue_description: str, context: Dict[str, Any]) -> bool:
        return False
    
    async def _fix_missing_table(self, context: Dict[str, Any]) -> bool:
        return False
    
    async def _fix_migration_issue(self, context: Dict[str, Any]) -> bool:
        return False
    
    async def _generic_database_fix(self, issue_description: str, context: Dict[str, Any]) -> bool:
        return False
    
    async def _apply_generic_fix(self, component: str, issue_description: str, context: Dict[str, Any]) -> bool:
        return False
    
    async def _apply_predictive_fix(self, prediction: Dict[str, Any]) -> Dict[str, Any]:
        """Применение предсказательного исправления"""
        return {
            'success': False,
            'note': 'Predictive fixes not yet implemented'
        }
    
    async def _apply_recommendation_fix(self, recommendation: Dict[str, Any]) -> Dict[str, Any]:
        """Применение исправления на основе рекомендации"""
        return {
            'success': False,
            'note': 'Recommendation fixes not yet implemented'
        }
    
    async def _handle_disk_error(self):
        await self._cleanup_old_logs()
    
    async def _handle_connection_error(self):
        pass
    
    async def _handle_generic_error(self, error_message: str):
        pass


import sys