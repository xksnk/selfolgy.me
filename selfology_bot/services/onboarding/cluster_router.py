"""
ClusterRouter - Роутер вопросов на основе кластерной структуры.

Кластер = неразрывный блок вопросов, который нужно пройти до конца.

Три режима:
1. Умный AI - автоматический подбор кластеров для построения цифрового отпечатка
2. Выбор программы - пользователь выбирает программу из 29 доступных
3. Закончить кластеры - показать и завершить незаконченные кластеры

Источник данных: JSON файлы (не БД)
- selfology_programs_v2.json - 29 программ, 190 кластеров, 674 вопроса
- cluster_sequence_v1.json - порядок кластеров для умного режима
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class OnboardingMode(Enum):
    """Режимы онбординга"""
    SMART_AI = "smart_ai"           # Автоматический подбор кластеров
    PROGRAM = "program"             # Выбор конкретной программы
    FINISH_CLUSTERS = "finish"      # Завершить незаконченные кластеры


@dataclass
class ClusterContext:
    """Контекст текущего кластера для пользователя"""
    user_id: int
    cluster_id: str
    cluster_name: str
    program_id: str
    program_name: str
    questions: List[Dict]
    current_question_index: int
    total_questions: int
    block_metadata: Dict


class ClusterRouter:
    """
    Роутер для навигации по кластерам вопросов.

    Загружает данные из JSON, предоставляет методы для:
    - Получения списка программ
    - Выбора следующего кластера (умный/ручной)
    - Навигации по вопросам внутри кластера
    - Отслеживания незаконченных кластеров
    """

    def __init__(self, data_dir: str = None):
        """
        Инициализация роутера.

        Args:
            data_dir: Путь к директории с JSON файлами
        """
        if data_dir is None:
            data_dir = Path(__file__).parent.parent.parent.parent / "intelligent_question_core" / "data"
        else:
            data_dir = Path(data_dir)

        self.data_dir = data_dir

        # Загружаем данные
        self.programs: Dict[str, Dict] = {}          # program_id -> program data
        self.clusters: Dict[str, Dict] = {}          # cluster_id -> cluster data
        self.questions: Dict[str, Dict] = {}         # question_id -> question data
        self.smart_sequence: List[Dict] = []         # Порядок для умного режима

        self._load_data()

        logger.info(f"🎯 ClusterRouter initialized: {len(self.programs)} programs, {len(self.clusters)} clusters, {len(self.questions)} questions")

    def _load_data(self):
        """Загрузить данные из JSON файлов"""

        # 1. Загружаем программы
        programs_file = self.data_dir / "selfology_programs_v2.json"
        if not programs_file.exists():
            raise FileNotFoundError(f"Programs file not found: {programs_file}")

        with open(programs_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        for program in data.get('programs', []):
            program_id = program['id']
            self.programs[program_id] = {
                'id': program_id,
                'name': program['name'],
                'blocks': []
            }

            for block in program.get('blocks', []):
                cluster_id = block['id']

                # Сохраняем кластер
                cluster_data = {
                    'id': cluster_id,
                    'name': block['name'],
                    'description': block.get('description', ''),
                    'type': block.get('type', 'Exploration'),
                    'sequence': block.get('sequence', 0),
                    'program_id': program_id,
                    'program_name': program['name'],
                    'metadata': block.get('block_metadata', {}),
                    'questions': []
                }

                # Метаданные блока для classification
                block_meta = block.get('block_metadata', {})

                # Сохраняем вопросы
                for q in block.get('questions', []):
                    question_id = q['id']
                    # Извлекаем значения из block_metadata
                    complexity_range = block_meta.get('base_complexity_range', [1, 2])
                    emotional_range = block_meta.get('base_emotional_weight_range', [1, 2])
                    safety_min = block_meta.get('base_safety_minimum', 4)

                    question_data = {
                        'id': question_id,
                        'text': q['text'],
                        'position': q.get('position', 0),
                        'position_in_block': q.get('position_in_block', 0),
                        'format': q.get('format', 'both'),
                        'cluster_id': cluster_id,
                        'program_id': program_id,
                        # classification для совместимости с answer_analyzer
                        'classification': {
                            'domain': self._infer_domain_from_program(program_id),
                            'depth_level': block_meta.get('base_depth_range', ['SURFACE'])[0],
                            'energy_dynamic': block_meta.get('base_energy_dynamic', 'NEUTRAL'),
                            'journey_stage': block_meta.get('base_journey_stage', 'ENTRY')
                        },
                        # psychology для совместимости с answer_analyzer
                        'psychology': {
                            'complexity': (complexity_range[0] + complexity_range[-1]) / 2 if complexity_range else 1.5,
                            'emotional_weight': (emotional_range[0] + emotional_range[-1]) / 2 if emotional_range else 1.5,
                            'insight_potential': 3,  # Средний потенциал
                            'trust_requirement': 2,  # Низкое требование доверия для ENTRY
                            'safety_level': safety_min
                        },
                        'block_metadata': block_meta
                    }
                    self.questions[question_id] = question_data
                    cluster_data['questions'].append(question_data)

                # Сортируем вопросы по позиции
                cluster_data['questions'].sort(key=lambda x: x['position_in_block'])

                self.clusters[cluster_id] = cluster_data
                self.programs[program_id]['blocks'].append(cluster_id)

        logger.info(f"📚 Loaded {len(self.programs)} programs, {len(self.clusters)} clusters, {len(self.questions)} questions")

        # 2. Загружаем порядок для умного режима
        sequence_file = self.data_dir / "cluster_sequence_v1.json"
        if sequence_file.exists():
            with open(sequence_file, 'r', encoding='utf-8') as f:
                seq_data = json.load(f)
                self.smart_sequence = seq_data.get('sequence', [])
            logger.info(f"🎯 Loaded smart sequence: {len(self.smart_sequence)} clusters")
        else:
            logger.warning(f"⚠️ Smart sequence file not found: {sequence_file}")

    def _infer_domain_from_program(self, program_id: str) -> str:
        """
        Определить психологический домен на основе ID программы.

        Маппинг программ к доменам для answer_analyzer.
        """
        # Маппинг по ключевым словам в program_id
        domain_mapping = {
            'zhizni': 'IDENTITY',           # Подумать о жизни
            'sebya': 'IDENTITY',            # Изучить себя
            'kariera': 'WORK',              # Карьера
            'biznes': 'WORK',               # Бизнес
            'zdorove': 'BODY',              # Здоровье
            'telo': 'BODY',                 # Тело
            'otnosheniya': 'RELATIONSHIPS', # Отношения
            'semi': 'RELATIONSHIPS',        # Семья
            'lyubov': 'RELATIONSHIPS',      # Любовь
            'strahi': 'FEARS',              # Страхи
            'trevoga': 'EMOTIONS',          # Тревога
            'emotsi': 'EMOTIONS',           # Эмоции
            'tsennost': 'VALUES',           # Ценности
            'smysl': 'VALUES',              # Смыслы
            'tsel': 'GOALS',                # Цели
            'mechta': 'FUTURE',             # Мечты
            'proshloe': 'PAST',             # Прошлое
            'detstvo': 'PAST',              # Детство
            'tvorchestvo': 'CREATIVITY',    # Творчество
            'duhovnost': 'SPIRITUALITY',    # Духовность
            'rost': 'GROWTH',               # Рост
            'razvitie': 'GROWTH',           # Развитие
        }

        program_id_lower = program_id.lower()
        for keyword, domain in domain_mapping.items():
            if keyword in program_id_lower:
                return domain

        return 'IDENTITY'  # По умолчанию

    # =========================================================================
    # ПОЛУЧЕНИЕ ДАННЫХ
    # =========================================================================

    def get_all_programs(self) -> List[Dict[str, Any]]:
        """
        Получить список всех программ.

        Returns:
            Список программ с базовой информацией
        """
        result = []
        for program_id, program in self.programs.items():
            blocks = [self.clusters[bid] for bid in program['blocks'] if bid in self.clusters]
            total_questions = sum(len(b['questions']) for b in blocks)

            result.append({
                'id': program_id,
                'name': program['name'],
                'blocks_count': len(blocks),
                'questions_count': total_questions
            })

        return result

    def get_program(self, program_id: str) -> Optional[Dict[str, Any]]:
        """Получить информацию о программе"""
        return self.programs.get(program_id)

    def get_cluster(self, cluster_id: str) -> Optional[Dict[str, Any]]:
        """Получить информацию о кластере"""
        return self.clusters.get(cluster_id)

    def get_question(self, question_id: str) -> Optional[Dict[str, Any]]:
        """Получить информацию о вопросе"""
        return self.questions.get(question_id)

    def get_program_clusters(self, program_id: str) -> List[Dict[str, Any]]:
        """Получить все кластеры программы"""
        program = self.programs.get(program_id)
        if not program:
            return []

        return [self.clusters[bid] for bid in program['blocks'] if bid in self.clusters]

    # =========================================================================
    # УМНЫЙ РЕЖИМ (AI)
    # =========================================================================

    def get_next_smart_cluster(self, completed_cluster_ids: List[str]) -> Optional[Dict[str, Any]]:
        """
        Получить следующий кластер для умного режима.

        Args:
            completed_cluster_ids: Список уже пройденных кластеров

        Returns:
            Следующий кластер по оптимальному порядку или None
        """
        completed_set = set(completed_cluster_ids)

        for item in self.smart_sequence:
            cluster_id = item['block_id']
            if cluster_id not in completed_set and cluster_id in self.clusters:
                cluster = self.clusters[cluster_id]
                return {
                    'cluster_id': cluster_id,
                    'cluster_name': cluster['name'],
                    'program_name': cluster['program_name'],
                    'questions_count': len(cluster['questions']),
                    'stage': item.get('stage', 'EXPLORATION'),
                    'sequence_number': item['seq']
                }

        return None  # Все кластеры пройдены

    # =========================================================================
    # РЕЖИМ ПРОГРАММЫ
    # =========================================================================

    def get_first_cluster_in_program(self, program_id: str) -> Optional[Dict[str, Any]]:
        """Получить первый кластер программы"""
        program = self.programs.get(program_id)
        if not program or not program['blocks']:
            return None

        first_cluster_id = program['blocks'][0]
        return self.clusters.get(first_cluster_id)

    def get_next_cluster_in_program(
        self,
        program_id: str,
        current_cluster_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Получить следующий кластер в программе.

        Args:
            program_id: ID программы
            current_cluster_id: ID текущего кластера

        Returns:
            Следующий кластер или None если программа завершена
        """
        program = self.programs.get(program_id)
        if not program:
            return None

        blocks = program['blocks']
        try:
            current_index = blocks.index(current_cluster_id)
            if current_index + 1 < len(blocks):
                next_cluster_id = blocks[current_index + 1]
                return self.clusters.get(next_cluster_id)
        except ValueError:
            pass

        return None  # Программа завершена

    # =========================================================================
    # НАВИГАЦИЯ ВНУТРИ КЛАСТЕРА
    # =========================================================================

    def get_cluster_questions(self, cluster_id: str) -> List[Dict[str, Any]]:
        """Получить все вопросы кластера в правильном порядке"""
        cluster = self.clusters.get(cluster_id)
        if not cluster:
            return []

        return cluster['questions']

    def get_question_in_cluster(
        self,
        cluster_id: str,
        answered_question_ids: List[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Получить следующий неотвеченный вопрос в кластере.

        Args:
            cluster_id: ID кластера
            answered_question_ids: Список уже отвеченных вопросов

        Returns:
            Следующий вопрос или None если кластер завершён
        """
        cluster = self.clusters.get(cluster_id)
        if not cluster:
            return None

        answered_set = set(answered_question_ids)

        for question in cluster['questions']:
            if question['id'] not in answered_set:
                # Добавляем метаданные блока к вопросу
                return {
                    **question,
                    'cluster_name': cluster['name'],
                    'program_name': cluster['program_name'],
                    'block_metadata': cluster['metadata'],
                    'total_in_cluster': len(cluster['questions']),
                    'position_display': f"{question['position_in_block']}/{len(cluster['questions'])}"
                }

        return None  # Кластер завершён

    def is_cluster_completed(
        self,
        cluster_id: str,
        answered_question_ids: List[str]
    ) -> bool:
        """Проверить, завершён ли кластер"""
        cluster = self.clusters.get(cluster_id)
        if not cluster:
            return True

        answered_set = set(answered_question_ids)
        cluster_question_ids = {q['id'] for q in cluster['questions']}

        return cluster_question_ids.issubset(answered_set)

    # =========================================================================
    # СТАТИСТИКА
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику по загруженным данным"""
        return {
            'programs_count': len(self.programs),
            'clusters_count': len(self.clusters),
            'questions_count': len(self.questions),
            'smart_sequence_length': len(self.smart_sequence)
        }
