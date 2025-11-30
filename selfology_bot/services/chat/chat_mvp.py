"""
ChatMVP - Минимальный AI-коуч чат по архитектуре из исследований.

Принципы:
1. Структура сессии: Foundation → Exploration → Integration
2. Без смешивания программ
3. Адаптивные переходы при сопротивлении
4. Персонализация на основе профиля личности
5. AI генерирует ответы, не шаблоны
6. КОУЧ ЗНАЕТ ВСЁ О ПОЛЬЗОВАТЕЛЕ - загружает digital_personality перед ответом
"""

import logging
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

from .session_manager import SessionManager, SessionState, BlockType, DepthLevel
from .user_dossier_service import UserDossierService, UserDossier
from .dossier_validator import DossierValidator

logger = logging.getLogger(__name__)


@dataclass
class UserKnowledge:
    """
    ВСЕ знания о пользователе для AI коуча.

    Загружается из digital_personality и user_answers_v2 перед каждым ответом.
    """
    user_id: int

    # Из digital_personality (10 слоёв)
    identity: List[Dict] = field(default_factory=list)       # Кто я: "журналист", "хочу страдать"
    interests: List[Dict] = field(default_factory=list)      # Блог, рисование, программирование
    goals: List[Dict] = field(default_factory=list)          # Медиа компания, друзья каждые выходные
    barriers: List[Dict] = field(default_factory=list)       # "Не могу ценить хорошее"
    relationships: List[Dict] = field(default_factory=list)  # Отношения с людьми
    values: List[Dict] = field(default_factory=list)         # Позитивный взгляд, помощь людям
    current_state: List[Dict] = field(default_factory=list)  # Сейчас: ведет блоги, ищет направление
    skills: List[Dict] = field(default_factory=list)         # Навыки
    experiences: List[Dict] = field(default_factory=list)    # Значимый опыт
    health: List[Dict] = field(default_factory=list)         # Здоровье

    # Последние ответы для контекста
    recent_answers: List[Dict] = field(default_factory=list)  # Последние 5-10 ответов

    # Метаданные
    total_answers: int = 0
    completeness_score: float = 0.0

    def to_prompt_context(self) -> str:
        """
        Сформировать контекст для AI промпта.

        Коуч должен знать ВСЁ перед ответом!
        """
        sections = []

        # Идентичность
        if self.identity:
            identity_items = [f"- {item.get('description', item)}" for item in self.identity[:5]]
            sections.append(f"КТО Я:\n" + "\n".join(identity_items))

        # Интересы
        if self.interests:
            interests_items = [f"- {item.get('activity', item)}" for item in self.interests[:5]]
            sections.append(f"ИНТЕРЕСЫ:\n" + "\n".join(interests_items))

        # Цели
        if self.goals:
            goals_items = [f"- {item.get('goal', item)}" for item in self.goals[:5]]
            sections.append(f"ЦЕЛИ:\n" + "\n".join(goals_items))

        # Барьеры (важно для коучинга!)
        if self.barriers:
            barriers_items = [f"- {item.get('barrier', item)}" for item in self.barriers[:5]]
            sections.append(f"БАРЬЕРЫ (что мешает):\n" + "\n".join(barriers_items))

        # Ценности
        if self.values:
            values_items = [f"- {item.get('value', item)}" for item in self.values[:5]]
            sections.append(f"ЦЕННОСТИ:\n" + "\n".join(values_items))

        # Текущее состояние
        if self.current_state:
            state_items = [f"- {item.get('activity', item)}" for item in self.current_state[:3]]
            sections.append(f"СЕЙЧАС:\n" + "\n".join(state_items))

        # Последние ответы
        if self.recent_answers:
            answers_text = []
            for ans in self.recent_answers[:3]:
                q = ans.get('question', '')[:50]
                a = ans.get('answer', '')[:100]
                answers_text.append(f"Q: {q}...\nA: {a}...")
            sections.append(f"ПОСЛЕДНИЕ ОТВЕТЫ:\n" + "\n".join(answers_text))

        return "\n\n".join(sections) if sections else "Данных о пользователе пока нет."


def get_trait_value(trait_data, default: float = 0.5) -> float:
    """Извлечь числовое значение трейта (поддержка dict и float форматов)"""
    if trait_data is None:
        return default
    if isinstance(trait_data, dict):
        return float(trait_data.get("score", default))
    if isinstance(trait_data, (int, float)):
        return float(trait_data)
    return default


@dataclass
class ChatResponse:
    """Ответ чата"""
    success: bool
    message: str
    question: Optional[Dict[str, Any]] = None
    block_info: Optional[Dict[str, Any]] = None
    session_summary: Optional[Dict[str, Any]] = None
    ai_response: Optional[str] = None
    needs_program_selection: bool = False
    available_programs: List[Dict] = None
    resistance_options: Optional[Dict] = None


class ChatMVP:
    """
    MVP чат-коуч по архитектуре из исследований.

    Флоу:
    1. Пользователь выбирает программу
    2. Проходит Foundation блок (обязательно)
    3. Проходит Exploration блоки (гибкий порядок)
    4. Integration блок (в конце)
    """

    def __init__(self, cluster_router, db_pool=None, ai_client=None, redis_client=None):
        """
        Args:
            cluster_router: ClusterRouter для доступа к вопросам
            db_pool: Пул подключений к БД (ОБЯЗАТЕЛЬНО для загрузки личности!)
            ai_client: AI клиент для генерации ответов (опционально)
            redis_client: Redis для кэширования досье (опционально)
        """
        self.cluster_router = cluster_router
        self.db_pool = db_pool
        self.ai_client = ai_client
        self.redis_client = redis_client
        self.session_manager = SessionManager(cluster_router)

        # UserDossierService для AI-резюме личности
        self.dossier_service = UserDossierService(
            db_pool=db_pool,
            redis_client=redis_client,
            ai_client=ai_client
        )

        # DossierValidator для коррекций и check-in
        self.dossier_validator = DossierValidator(
            dossier_service=self.dossier_service,
            db_pool=db_pool
        )

        # Кэш знаний о пользователях (legacy, для fallback)
        self._knowledge_cache: Dict[int, UserKnowledge] = {}

        logger.info("🤖 ChatMVP initialized with UserDossierService + DossierValidator")

    async def load_user_knowledge(self, user_id: int) -> UserKnowledge:
        """
        ГЛАВНЫЙ МЕТОД: Загрузить ВСЕ знания о пользователе перед ответом.

        Коуч должен знать:
        - Кто пользователь (identity)
        - Что его интересует (interests)
        - К чему стремится (goals)
        - Что мешает (barriers) - КРИТИЧНО для коучинга!
        - Что ценит (values)
        - Где сейчас (current_state)
        - Последние ответы (recent_answers)
        """
        # Проверяем кэш (обновляем раз в 5 минут)
        if user_id in self._knowledge_cache:
            cached = self._knowledge_cache[user_id]
            # TODO: добавить проверку времени кэша
            return cached

        knowledge = UserKnowledge(user_id=user_id)

        if not self.db_pool:
            logger.warning(f"⚠️ No db_pool - cannot load knowledge for user {user_id}")
            return knowledge

        try:
            async with self.db_pool.acquire() as conn:
                # 1. Загружаем digital_personality (10 слоёв)
                row = await conn.fetchrow("""
                    SELECT identity, interests, goals, barriers, relationships,
                           values, current_state, skills, experiences, health,
                           total_answers_analyzed, completeness_score
                    FROM selfology.digital_personality
                    WHERE user_id = $1
                """, user_id)

                if row:
                    # Парсим JSONB поля
                    for field in ['identity', 'interests', 'goals', 'barriers',
                                  'relationships', 'values', 'current_state',
                                  'skills', 'experiences', 'health']:
                        data = row[field]
                        if data:
                            # Может быть строка JSON или уже объект
                            if isinstance(data, str):
                                try:
                                    data = json.loads(data)
                                except json.JSONDecodeError:
                                    data = []
                            setattr(knowledge, field, data if isinstance(data, list) else [])

                    knowledge.total_answers = row['total_answers_analyzed'] or 0
                    knowledge.completeness_score = float(row['completeness_score'] or 0)

                    logger.info(f"✅ Loaded digital personality for user {user_id}: {knowledge.total_answers} answers")

                # 2. Загружаем последние ответы для контекста
                answers = await conn.fetch("""
                    SELECT ua.question_id, ua.answer_text, ua.cluster_id, ua.answered_at
                    FROM selfology.user_answers_v2 ua
                    WHERE ua.user_id = $1
                    ORDER BY ua.answered_at DESC
                    LIMIT 10
                """, user_id)

                if answers:
                    for ans in answers:
                        # Получаем текст вопроса
                        question = self.cluster_router.get_question(ans['question_id'])
                        question_text = question['text'] if question else ans['question_id']

                        knowledge.recent_answers.append({
                            'question': question_text,
                            'answer': ans['answer_text'],
                            'cluster_id': ans['cluster_id'],
                            'answered_at': ans['answered_at'].isoformat() if ans['answered_at'] else None
                        })

                    logger.info(f"✅ Loaded {len(answers)} recent answers for user {user_id}")

        except Exception as e:
            logger.error(f"❌ Failed to load knowledge for user {user_id}: {e}")

        # Кэшируем
        self._knowledge_cache[user_id] = knowledge
        return knowledge

    async def get_user_dossier(self, user_id: int, force_regenerate: bool = False) -> UserDossier:
        """
        Получить AI-сгенерированное досье пользователя.

        РЕКОМЕНДУЕМЫЙ МЕТОД вместо load_user_knowledge!

        Преимущества:
        - ~500 токенов вместо 10K+ при загрузке всех данных
        - AI анализирует и выделяет главное
        - Кэшируется в Redis (1 час)
        - Включает style_hints на основе Big Five

        Args:
            user_id: ID пользователя
            force_regenerate: Принудительно перегенерировать

        Returns:
            UserDossier с AI-резюме
        """
        return await self.dossier_service.get_dossier(user_id, force_regenerate)

    async def start_chat(self, user_id: int) -> ChatResponse:
        """
        Начать чат - показать выбор программы или продолжить текущую.
        """
        session = self.session_manager.get_or_create_session(user_id)

        # Если программа уже выбрана - продолжаем
        if session.program_id:
            return await self.get_next_step(user_id)

        # Иначе - показываем выбор программ
        programs = self.cluster_router.get_all_programs()

        return ChatResponse(
            success=True,
            message="Выберите программу для работы:",
            needs_program_selection=True,
            available_programs=programs
        )

    async def select_program(self, user_id: int, program_id: str) -> ChatResponse:
        """
        Пользователь выбрал программу.
        """
        session = self.session_manager.start_program(user_id, program_id)

        if not session:
            return ChatResponse(
                success=False,
                message="Не удалось выбрать программу. Возможно, вы уже в процессе другой программы."
            )

        # Получаем приветственное сообщение для программы
        welcome = self._generate_program_welcome(session)

        return ChatResponse(
            success=True,
            message=welcome,
            session_summary=self.session_manager.get_session_summary(user_id)
        )

    async def get_next_step(self, user_id: int) -> ChatResponse:
        """
        Получить следующий шаг (вопрос или смену блока).
        """
        session = self.session_manager.get_or_create_session(user_id)

        if not session.program_id:
            return await self.start_chat(user_id)

        # Получаем следующий вопрос
        question = self.session_manager.get_next_question(user_id)

        if question:
            # Получаем информацию о текущем блоке
            block_info = None
            if session.current_block_id:
                block_info = self.session_manager._get_block_info(session, session.current_block_id)

            return ChatResponse(
                success=True,
                message=question['text'],
                question=question,
                block_info=block_info,
                session_summary=self.session_manager.get_session_summary(user_id)
            )

        # Все вопросы пройдены - программа завершена
        return await self._finish_program(user_id)

    async def process_message(
        self,
        user_id: int,
        message: str,
        personality: Optional[Dict] = None,
        use_dossier: bool = True
    ) -> ChatResponse:
        """
        Обработать сообщение пользователя.

        ВАЖНО: Коуч ЗНАЕТ ВСЁ о пользователе через досье!

        Args:
            user_id: ID пользователя
            message: Текст сообщения
            personality: Профиль личности (deprecated)
            use_dossier: Использовать AI-досье (True) или сырые данные (False)
        """
        session = self.session_manager.get_or_create_session(user_id)

        if not session.program_id:
            return await self.start_chat(user_id)

        # ⭐ ГЛАВНОЕ: Загружаем ДОСЬЕ - AI-резюме личности (~500 токенов)
        dossier = None
        knowledge = None

        if use_dossier:
            dossier = await self.get_user_dossier(user_id)
            logger.info(f"📋 Loaded dossier for user {user_id}: "
                        f"goals={len(dossier.top_goals)}, barriers={len(dossier.top_barriers)}, "
                        f"patterns={len(dossier.patterns)}")
        else:
            # Fallback: загружаем сырые данные
            knowledge = await self.load_user_knowledge(user_id)
            logger.info(f"🧠 Loaded raw knowledge for user {user_id}: {knowledge.total_answers} answers")

        # 🔍 Проверяем на коррекцию досье и необходимость check-in
        validation_result = await self.dossier_validator.process_message(
            user_id, message, dossier
        )

        response_prefix = ""
        if validation_result['correction_detected']:
            # Пользователь исправил коуча
            response_prefix = validation_result['response_prefix']
            logger.info(f"🔍 Correction detected for user {user_id}: "
                       f"{validation_result['correction'].correction_type.value}")
            # Досье уже инвалидировано в process_message

        # Проверяем на сопротивление
        if self._detect_resistance(message):
            return await self._handle_resistance(user_id, message)

        # Записываем ответ
        if session.current_question_id:
            self.session_manager.record_answer(user_id, session.current_question_id, message)
            # Инвалидируем досье (будет перегенерировано после 5 ответов)
            await self.dossier_service.invalidate_dossier(user_id)

        # Генерируем AI ответ с ДОСЬЕ или знаниями
        ai_response = await self._generate_ai_response(
            user_id, message, session,
            knowledge=knowledge,
            dossier=dossier
        )

        # Добавляем prefix если была коррекция
        if response_prefix and ai_response:
            ai_response = response_prefix + ai_response

        # Сохраняем ответ коуча для контекста следующих коррекций
        if ai_response:
            self.dossier_validator.set_last_coach_message(user_id, ai_response)

        # Получаем следующий вопрос
        next_step = await self.get_next_step(user_id)

        # Комбинируем AI ответ с следующим вопросом
        if ai_response and next_step.success:
            combined_message = f"{ai_response}\n\n{next_step.message}"
            return ChatResponse(
                success=True,
                message=combined_message,
                ai_response=ai_response,
                question=next_step.question,
                block_info=next_step.block_info,
                session_summary=next_step.session_summary
            )

        return next_step

    def _detect_resistance(self, message: str) -> bool:
        """
        Детектировать сопротивление в сообщении.

        Признаки сопротивления:
        - "не хочу об этом"
        - "давай о другом"
        - "сложно отвечать"
        - слишком короткие ответы на глубокие вопросы
        """
        resistance_markers = [
            'не хочу', 'не готов', 'сложно', 'тяжело',
            'давай о другом', 'пропустить', 'пропустим',
            'не знаю', 'не могу ответить', 'трудно сказать'
        ]

        message_lower = message.lower()
        return any(marker in message_lower for marker in resistance_markers)

    async def _handle_resistance(self, user_id: int, message: str) -> ChatResponse:
        """
        Обработать сопротивление пользователя.

        По архитектуре из исследований:
        - Предложить перейти в другой Exploration блок
        - Или сделать паузу
        """
        resistance_info = self.session_manager.handle_resistance(user_id)

        # Формируем сообщение
        response_text = "Понимаю, что это непростая тема. "

        if resistance_info['alternatives']:
            response_text += "Хочешь перейти к другой теме?\n\n"
            for alt in resistance_info['alternatives']:
                response_text += f"• {alt['block_name']}\n"
            response_text += "\nИли можем сделать паузу и вернуться позже."
        else:
            response_text += "Можем сделать паузу и вернуться к этому позже."

        return ChatResponse(
            success=True,
            message=response_text,
            resistance_options=resistance_info,
            session_summary=self.session_manager.get_session_summary(user_id)
        )

    async def switch_block(self, user_id: int, block_id: str) -> ChatResponse:
        """
        Переключиться на другой блок (адаптивный переход).
        """
        success = self.session_manager.switch_to_block(user_id, block_id)

        if success:
            return await self.get_next_step(user_id)

        return ChatResponse(
            success=False,
            message="Не удалось переключиться на этот блок. Возможно, сначала нужно пройти основной блок."
        )

    async def _generate_ai_response(
        self,
        user_id: int,
        user_message: str,
        session: SessionState,
        knowledge: Optional[UserKnowledge] = None,
        dossier: Optional[UserDossier] = None
    ) -> Optional[str]:
        """
        Генерировать AI ответ С ДОСЬЕ или ЗНАНИЯМИ о пользователе.

        Приоритет:
        1. dossier - AI-резюме (~500 токенов, рекомендуется)
        2. knowledge - сырые данные (fallback)
        """
        # Если нет AI клиента - используем шаблонный ответ
        if not self.ai_client:
            return self._generate_template_response(user_message, knowledge, dossier, session)

        # Формируем промпт с ДОСЬЕ или знаниями
        prompt = self._build_ai_prompt(user_message, knowledge, dossier, session)

        try:
            response = await self.ai_client.generate(prompt)
            return response
        except Exception as e:
            logger.error(f"AI generation failed: {e}")
            return self._generate_template_response(user_message, knowledge, dossier, session)

    def _generate_template_response(
        self,
        user_message: str,
        knowledge: Optional[UserKnowledge],
        dossier: Optional[UserDossier],
        session: SessionState
    ) -> str:
        """
        Генерировать шаблонный ответ с учётом досье или знаний.

        Приоритет: dossier → knowledge → общий ответ
        """
        message_lower = user_message.lower()
        response_parts = []

        # Приоритет 1: Используем досье
        if dossier and (dossier.top_goals or dossier.top_barriers):
            # Если пользователь говорит о целях
            if any(word in message_lower for word in ['цель', 'хочу', 'мечта', 'план']):
                if dossier.top_goals:
                    goal = dossier.top_goals[0][:50]
                    response_parts.append(f"Это связано с твоей целью \"{goal}\"?")

            # Если говорит о проблемах - связываем с барьерами
            elif any(word in message_lower for word in ['сложно', 'трудно', 'проблема', 'не могу']):
                if dossier.top_barriers:
                    barrier = dossier.top_barriers[0][:50]
                    response_parts.append(f"Похоже это связано с тем, что \"{barrier}\".")

            # Если есть паттерны - упоминаем
            elif dossier.patterns:
                pattern = dossier.patterns[0][:50]
                response_parts.append(f"Замечаю связь с паттерном: \"{pattern}\".")

        # Приоритет 2: Используем raw knowledge
        elif knowledge:
            if any(word in message_lower for word in ['цель', 'хочу', 'мечта', 'план']):
                if knowledge.goals:
                    goal = knowledge.goals[0].get('goal', '')
                    if goal:
                        response_parts.append(f"Это связано с твоей целью \"{goal[:50]}\"?")

            elif any(word in message_lower for word in ['сложно', 'трудно', 'проблема', 'не могу']):
                if knowledge.barriers:
                    barrier = knowledge.barriers[0].get('barrier', '')
                    if barrier:
                        response_parts.append(f"Похоже это связано с тем, что \"{barrier[:50]}\".")

            elif any(word in message_lower for word in ['работа', 'блог', 'проект', 'делаю']):
                if knowledge.current_state:
                    activity = knowledge.current_state[0].get('activity', '')
                    if activity:
                        response_parts.append(f"Как это связано с тем, что ты {activity}?")

        # Если ничего не нашли - общий ответ
        if not response_parts:
            if len(user_message) > 200:
                return "Интересное наблюдение. Что ещё приходит в голову?"
            elif len(user_message) < 30:
                return "Можешь рассказать подробнее?"
            else:
                return "Понимаю. Продолжим?"

        return " ".join(response_parts)

    def _build_ai_prompt(
        self,
        user_message: str,
        knowledge: Optional[UserKnowledge],
        dossier: Optional[UserDossier],
        session: SessionState
    ) -> str:
        """
        Построить промпт для AI коуча с ДОСЬЕ или знаниями.

        Приоритет: dossier (~500 токенов) → knowledge (fallback)
        """
        # Получаем контекст - приоритет досье
        if dossier:
            user_context = dossier.to_prompt_context()
            style_hints = dossier.style_hints
        elif knowledge:
            user_context = knowledge.to_prompt_context()
            style_hints = {}
        else:
            user_context = "Данных о пользователе пока нет."
            style_hints = {}

        # Формируем style instructions
        style_instructions = ""
        if style_hints:
            style_parts = [f"- {k}: {v}" for k, v in style_hints.items()]
            style_instructions = "\n".join(style_parts)

        prompt = f"""Ты AI-коуч в психологическом приложении Selfology.

=== ДОСЬЕ ПОЛЬЗОВАТЕЛЯ (AI-резюме) ===
{user_context}

=== КАК ОБЩАТЬСЯ (на основе Big Five) ===
{style_instructions if style_instructions else "Стандартный стиль общения"}

=== КОНТЕКСТ СЕССИИ ===
Программа: {session.program_name or 'не выбрана'}
Этап: {session.journey_stage.value}
Глубина: {session.current_depth.value}

=== СООБЩЕНИЕ ПОЛЬЗОВАТЕЛЯ ===
"{user_message}"

=== ПРАВИЛА КОУЧА ===
1. Ты ЗНАЕШЬ этого человека - упоминай конкретные факты из досье
2. СВЯЗЫВАЙ ответ с целями, барьерами, паттернами пользователя
3. Если есть ПРОТИВОРЕЧИЯ в досье - можешь мягко указать на них
4. Если пользователь говорит о проблеме - свяжи с его барьерами
5. Если о целях - свяжи с его целями
6. Адаптируй стиль под указанные выше рекомендации

=== ФОРМАТ ОТВЕТА ===
- Начни с отражения/эмпатии
- Упомяни что-то КОНКРЕТНОЕ из досье (цель, барьер, паттерн)
- Задай один углубляющий вопрос
- 2-4 предложения, без эмодзи

Ответ:"""

        return prompt

    def _generate_program_welcome(self, session: SessionState) -> str:
        """Приветственное сообщение при старте программы"""
        return f"""Отлично, начинаем программу "{session.program_name}"!

Эта программа поможет тебе глубже понять себя через серию вопросов.

Правила:
- Отвечай честно и развёрнуто
- Если какой-то вопрос сложен - скажи, и мы перейдём к другой теме
- Нет правильных или неправильных ответов

Готов начать?"""

    async def _finish_program(self, user_id: int) -> ChatResponse:
        """Завершение программы"""
        summary = self.session_manager.get_session_summary(user_id)

        message = f"""Поздравляю! Ты прошёл программу "{summary['program_name']}"!

Статистика:
- Отвечено вопросов: {summary['answered_questions']}/{summary['total_questions']}
- Пройдено блоков: {summary['completed_blocks']}/{summary['total_blocks']}
- Сообщений в сессии: {summary['messages_count']}

Хочешь начать новую программу или сделать перерыв?"""

        return ChatResponse(
            success=True,
            message=message,
            session_summary=summary,
            needs_program_selection=True,
            available_programs=self.cluster_router.get_all_programs()
        )

    def reset_chat(self, user_id: int) -> ChatResponse:
        """Сбросить чат и начать заново"""
        self.session_manager.reset_session(user_id)
        return ChatResponse(
            success=True,
            message="Сессия сброшена. Выбери программу для начала."
        )

    def get_status(self, user_id: int) -> ChatResponse:
        """Получить статус текущей сессии"""
        summary = self.session_manager.get_session_summary(user_id)
        return ChatResponse(
            success=True,
            message=f"Прогресс: {summary['completion_percent']}%",
            session_summary=summary
        )
