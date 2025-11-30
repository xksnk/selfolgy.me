"""
SessionManager - Управление сессией чата по архитектуре из исследований.

Архитектура сессии:
1. Foundation блок (обязательно сначала) - установка контакта
2. Exploration блоки (гибкий порядок) - исследование
3. Integration блок (в конце) - интеграция инсайтов

Правила:
- НЕ смешивать программы в одной сессии
- Адаптивные переходы при сопротивлении
- Глубина: SURFACE → CONSCIOUS → EDGE → SHADOW → CORE
"""

import logging
from enum import Enum
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


class BlockType(Enum):
    """Тип блока по архитектуре исследования"""
    FOUNDATION = "foundation"      # Обязательное основание
    EXPLORATION = "exploration"    # Гибкий порядок
    INTEGRATION = "integration"    # Якорь в конце


class DepthLevel(Enum):
    """Уровни глубины по модели Роджерса"""
    SURFACE = "surface"          # Сообщение фактов
    CONSCIOUS = "conscious"      # Описание чувств
    EDGE = "edge"                # Выявление паттернов
    SHADOW = "shadow"            # Смысловое присвоение
    CORE = "core"                # Трансформационное озарение


class JourneyStage(Enum):
    """Этап путешествия пользователя"""
    ENTRY = "entry"              # Вход
    EXPLORATION = "exploration"  # Исследование
    DEEPENING = "deepening"      # Углубление
    INTEGRATION = "integration"  # Интеграция
    CLOSING = "closing"          # Закрытие


@dataclass
class BlockProgress:
    """Прогресс по блоку"""
    block_id: str
    block_name: str
    block_type: BlockType
    total_questions: int
    answered_questions: int = 0
    is_completed: bool = False
    skipped: bool = False


@dataclass
class SessionState:
    """Состояние сессии пользователя"""
    user_id: int
    session_id: str

    # Текущая программа (не меняется в сессии!)
    program_id: Optional[str] = None
    program_name: Optional[str] = None

    # Текущий блок
    current_block_id: Optional[str] = None
    current_block_type: Optional[BlockType] = None

    # Текущий вопрос в блоке
    current_question_id: Optional[str] = None
    current_question_index: int = 0

    # Прогресс по блокам
    blocks_progress: Dict[str, BlockProgress] = field(default_factory=dict)

    # Глубина и этап
    current_depth: DepthLevel = DepthLevel.SURFACE
    journey_stage: JourneyStage = JourneyStage.ENTRY

    # Отвеченные вопросы (для отслеживания)
    answered_question_ids: List[str] = field(default_factory=list)

    # Метаданные сессии
    started_at: datetime = field(default_factory=datetime.now)
    messages_count: int = 0
    resistance_detected: bool = False

    # Флаги состояния
    foundation_completed: bool = False
    all_exploration_completed: bool = False
    integration_available: bool = False


class SessionManager:
    """
    Менеджер сессий чата.

    Отвечает за:
    - Создание и восстановление сессий
    - Отслеживание прогресса по блокам
    - Определение следующего блока/вопроса
    - Обработку адаптивных переходов
    """

    def __init__(self, cluster_router):
        """
        Args:
            cluster_router: ClusterRouter для доступа к программам и вопросам
        """
        self.cluster_router = cluster_router
        self._sessions: Dict[int, SessionState] = {}  # user_id -> session

        logger.info("📋 SessionManager initialized")

    def get_or_create_session(self, user_id: int) -> SessionState:
        """Получить или создать сессию для пользователя"""
        if user_id not in self._sessions:
            session_id = f"session_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self._sessions[user_id] = SessionState(
                user_id=user_id,
                session_id=session_id
            )
            logger.info(f"📋 Created new session for user {user_id}: {session_id}")
        return self._sessions[user_id]

    def start_program(self, user_id: int, program_id: str) -> Optional[SessionState]:
        """
        Начать программу для пользователя.

        Правило: нельзя менять программу внутри сессии!
        """
        session = self.get_or_create_session(user_id)

        # Если программа уже выбрана - нельзя менять
        if session.program_id and session.program_id != program_id:
            logger.warning(f"⚠️ User {user_id} trying to change program mid-session")
            return None

        # Получаем данные программы
        program = self.cluster_router.get_program(program_id)
        if not program:
            logger.error(f"❌ Program {program_id} not found")
            return None

        session.program_id = program_id
        session.program_name = program['name']

        # Загружаем блоки программы
        clusters = self.cluster_router.get_program_clusters(program_id)
        for cluster in clusters:
            block_type = self._determine_block_type(cluster)
            session.blocks_progress[cluster['id']] = BlockProgress(
                block_id=cluster['id'],
                block_name=cluster['name'],
                block_type=block_type,
                total_questions=len(cluster.get('questions', []))
            )

        logger.info(f"✅ Started program '{program['name']}' for user {user_id}")
        return session

    def _determine_block_type(self, cluster: Dict) -> BlockType:
        """
        Определить тип блока по метаданным.

        По умолчанию:
        - Первый блок = Foundation
        - Последний блок = Integration
        - Остальные = Exploration
        """
        metadata = cluster.get('metadata', {})

        # Если явно указано в метаданных
        block_type_str = metadata.get('block_type', '').lower()
        if 'foundation' in block_type_str:
            return BlockType.FOUNDATION
        elif 'integration' in block_type_str:
            return BlockType.INTEGRATION
        elif 'exploration' in block_type_str:
            return BlockType.EXPLORATION

        # По умолчанию - Exploration
        return BlockType.EXPLORATION

    def get_next_block(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Получить следующий блок по архитектуре.

        Порядок:
        1. Foundation блоки (обязательно сначала)
        2. Exploration блоки (гибкий порядок)
        3. Integration блоки (после всех Exploration)
        """
        session = self.get_or_create_session(user_id)

        if not session.program_id:
            logger.warning(f"⚠️ User {user_id} has no program selected")
            return None

        # Проверяем Foundation блоки
        foundation_blocks = [
            bp for bp in session.blocks_progress.values()
            if bp.block_type == BlockType.FOUNDATION and not bp.is_completed
        ]
        if foundation_blocks:
            block = foundation_blocks[0]
            return self._get_block_info(session, block.block_id)

        session.foundation_completed = True

        # Проверяем Exploration блоки
        exploration_blocks = [
            bp for bp in session.blocks_progress.values()
            if bp.block_type == BlockType.EXPLORATION and not bp.is_completed
        ]
        if exploration_blocks:
            # Можно выбирать в любом порядке, берём первый непройденный
            block = exploration_blocks[0]
            return self._get_block_info(session, block.block_id)

        session.all_exploration_completed = True
        session.integration_available = True

        # Проверяем Integration блоки
        integration_blocks = [
            bp for bp in session.blocks_progress.values()
            if bp.block_type == BlockType.INTEGRATION and not bp.is_completed
        ]
        if integration_blocks:
            block = integration_blocks[0]
            return self._get_block_info(session, block.block_id)

        # Все блоки пройдены
        logger.info(f"✅ All blocks completed for user {user_id}")
        return None

    def _get_block_info(self, session: SessionState, block_id: str) -> Dict[str, Any]:
        """Получить информацию о блоке для отображения"""
        cluster = self.cluster_router.get_cluster(block_id)
        progress = session.blocks_progress.get(block_id)

        return {
            'block_id': block_id,
            'block_name': cluster['name'] if cluster else 'Unknown',
            'block_type': progress.block_type.value if progress else 'exploration',
            'total_questions': progress.total_questions if progress else 0,
            'answered_questions': progress.answered_questions if progress else 0,
            'description': cluster.get('description', '') if cluster else ''
        }

    def get_next_question(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Получить следующий вопрос в текущем блоке.

        Возвращает None если:
        - Нет выбранной программы
        - Текущий блок завершён (нужен следующий блок)
        """
        session = self.get_or_create_session(user_id)

        if not session.current_block_id:
            # Нужно выбрать блок
            next_block = self.get_next_block(user_id)
            if not next_block:
                return None
            session.current_block_id = next_block['block_id']
            session.current_question_index = 0

        # Получаем следующий неотвеченный вопрос в блоке
        question = self.cluster_router.get_question_in_cluster(
            session.current_block_id,
            session.answered_question_ids
        )

        if question:
            session.current_question_id = question['id']
            return question

        # Блок завершён
        if session.current_block_id in session.blocks_progress:
            session.blocks_progress[session.current_block_id].is_completed = True

        session.current_block_id = None
        session.current_question_id = None

        # Пробуем получить следующий блок
        return self.get_next_question(user_id)

    def record_answer(self, user_id: int, question_id: str, answer_text: str) -> bool:
        """Записать ответ пользователя"""
        session = self.get_or_create_session(user_id)

        if question_id not in session.answered_question_ids:
            session.answered_question_ids.append(question_id)
            session.messages_count += 1

            # Обновляем прогресс блока
            if session.current_block_id and session.current_block_id in session.blocks_progress:
                session.blocks_progress[session.current_block_id].answered_questions += 1

            logger.info(f"📝 Recorded answer for user {user_id}, question {question_id}")
            return True

        return False

    def handle_resistance(self, user_id: int) -> Dict[str, Any]:
        """
        Обработать сопротивление пользователя.

        По архитектуре из исследований:
        - Предложить перейти в другой Exploration блок
        - Или сделать паузу
        """
        session = self.get_or_create_session(user_id)
        session.resistance_detected = True

        # Находим альтернативные Exploration блоки
        alternatives = [
            bp for bp in session.blocks_progress.values()
            if bp.block_type == BlockType.EXPLORATION
            and not bp.is_completed
            and bp.block_id != session.current_block_id
        ]

        return {
            'resistance_detected': True,
            'alternatives': [
                {'block_id': bp.block_id, 'block_name': bp.block_name}
                for bp in alternatives[:3]  # Максимум 3 альтернативы
            ],
            'can_pause': True,
            'message': "Хочешь перейти в другое место диалога? Вернёмся к этому позже."
        }

    def switch_to_block(self, user_id: int, block_id: str) -> bool:
        """
        Переключиться на другой блок (при сопротивлении).

        Правило: можно переключаться только между Exploration блоками!
        """
        session = self.get_or_create_session(user_id)

        if block_id not in session.blocks_progress:
            logger.warning(f"⚠️ Block {block_id} not in user's program")
            return False

        block_progress = session.blocks_progress[block_id]

        # Нельзя переключиться на Foundation (он должен быть пройден)
        if block_progress.block_type == BlockType.FOUNDATION and not session.foundation_completed:
            logger.warning("⚠️ Cannot skip Foundation block")
            return False

        # Нельзя переключиться на Integration до завершения Exploration
        if block_progress.block_type == BlockType.INTEGRATION and not session.all_exploration_completed:
            logger.warning("⚠️ Cannot jump to Integration before Exploration")
            return False

        # Помечаем текущий блок как пропущенный (но не завершённый)
        if session.current_block_id and session.current_block_id in session.blocks_progress:
            session.blocks_progress[session.current_block_id].skipped = True

        session.current_block_id = block_id
        session.current_question_index = 0
        session.current_question_id = None

        logger.info(f"🔄 User {user_id} switched to block {block_id}")
        return True

    def get_session_summary(self, user_id: int) -> Dict[str, Any]:
        """Получить сводку по сессии"""
        session = self.get_or_create_session(user_id)

        total_questions = sum(bp.total_questions for bp in session.blocks_progress.values())
        answered_questions = sum(bp.answered_questions for bp in session.blocks_progress.values())
        completed_blocks = sum(1 for bp in session.blocks_progress.values() if bp.is_completed)

        return {
            'user_id': user_id,
            'session_id': session.session_id,
            'program_id': session.program_id,
            'program_name': session.program_name,
            'current_block_id': session.current_block_id,
            'total_questions': total_questions,
            'answered_questions': answered_questions,
            'completion_percent': round(answered_questions / total_questions * 100) if total_questions > 0 else 0,
            'total_blocks': len(session.blocks_progress),
            'completed_blocks': completed_blocks,
            'foundation_completed': session.foundation_completed,
            'integration_available': session.integration_available,
            'journey_stage': session.journey_stage.value,
            'current_depth': session.current_depth.value,
            'messages_count': session.messages_count
        }

    def reset_session(self, user_id: int) -> SessionState:
        """Сбросить сессию (начать заново)"""
        if user_id in self._sessions:
            del self._sessions[user_id]
        return self.get_or_create_session(user_id)
