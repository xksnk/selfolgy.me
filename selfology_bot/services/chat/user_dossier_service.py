"""
UserDossierService - AI-генерация резюме личности пользователя.

Принцип: Вместо загрузки ВСЕХ 72 целей и 62 барьеров в каждый промпт,
создаём AI-резюме (досье) которое обновляется после новых ответов.

Архитектура из исследований:
- Досье: 500-1000 токенов вместо 10K+
- Кэшируется в Redis (1 час TTL)
- Обновляется после 5 новых ответов
"""

import logging
import json
import hashlib
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class UserDossier:
    """
    AI-сгенерированное досье пользователя.

    Содержит:
    - who: Кто пользователь (2 предложения)
    - top_goals: Топ-3 цели с объяснением
    - top_barriers: Топ-3 барьера с гипотезой причин
    - patterns: Паттерны из ответов
    - contradictions: Противоречия (цели vs барьеры)
    - hypothesis: Психологическая динамика
    - style_hints: Как общаться (на основе Big Five)
    """
    user_id: int

    # Основное резюме
    who: str = ""                           # Кто: "Журналист 30+, ведёт блоги..."
    top_goals: List[str] = field(default_factory=list)      # Топ-3 цели
    top_barriers: List[str] = field(default_factory=list)   # Топ-3 барьера
    patterns: List[str] = field(default_factory=list)       # Паттерны
    contradictions: List[str] = field(default_factory=list) # Противоречия
    hypothesis: str = ""                    # Психологическая гипотеза

    # Стиль общения (из Big Five)
    style_hints: Dict[str, str] = field(default_factory=dict)

    # Метаданные
    generated_at: Optional[datetime] = None
    answers_count_at_generation: int = 0
    raw_data_hash: str = ""                 # Хэш данных для инвалидации

    def to_prompt_context(self) -> str:
        """
        Сформировать контекст для AI промпта.

        ~500-700 токенов вместо 10K+ при загрузке всех данных.
        """
        sections = []

        # 1. Кто
        if self.who:
            sections.append(f"КТО: {self.who}")

        # 2. Цели
        if self.top_goals:
            goals_text = "\n".join([f"• {g}" for g in self.top_goals[:3]])
            sections.append(f"ГЛАВНЫЕ ЦЕЛИ:\n{goals_text}")

        # 3. Барьеры
        if self.top_barriers:
            barriers_text = "\n".join([f"• {b}" for b in self.top_barriers[:3]])
            sections.append(f"ГЛАВНЫЕ БАРЬЕРЫ:\n{barriers_text}")

        # 4. Паттерны
        if self.patterns:
            patterns_text = "\n".join([f"• {p}" for p in self.patterns[:3]])
            sections.append(f"ПАТТЕРНЫ:\n{patterns_text}")

        # 5. Противоречия
        if self.contradictions:
            contradictions_text = "\n".join([f"• {c}" for c in self.contradictions[:2]])
            sections.append(f"ПРОТИВОРЕЧИЯ:\n{contradictions_text}")

        # 6. Гипотеза
        if self.hypothesis:
            sections.append(f"ПСИХОЛОГИЧЕСКАЯ ДИНАМИКА:\n{self.hypothesis}")

        # 7. Стиль общения
        if self.style_hints:
            style_text = ", ".join([f"{k}: {v}" for k, v in self.style_hints.items()])
            sections.append(f"КАК ОБЩАТЬСЯ: {style_text}")

        return "\n\n".join(sections) if sections else "Досье ещё не сгенерировано."


class UserDossierService:
    """
    Сервис генерации и управления досье пользователей.

    Принципы:
    1. Генерируем AI-резюме вместо загрузки всех данных
    2. Кэшируем в Redis (1 час)
    3. Обновляем после 5 новых ответов
    4. Инвалидируем при изменении данных (по хэшу)
    """

    # Промпт для генерации досье
    DOSSIER_PROMPT = """Проанализируй данные о пользователе и создай психологическое досье.

ДАННЫЕ О ПОЛЬЗОВАТЕЛЕ:

ЦЕЛИ ({goals_count} всего):
{goals}

БАРЬЕРЫ ({barriers_count} всего):
{barriers}

ЦЕННОСТИ ({values_count} всего):
{values}

ИДЕНТИЧНОСТЬ:
{identity}

ТЕКУЩЕЕ СОСТОЯНИЕ:
{current_state}

ПОСЛЕДНИЕ ОТВЕТЫ:
{recent_answers}

BIG FIVE ПРОФИЛЬ:
{big_five}

---

ФОРМАТ ДОСЬЕ (строго соблюдай!):

WHO: [Кто этот человек: профессия, возраст, ситуация - 2 предложения]

TOP_GOALS:
1. [Главная цель с объяснением почему важна]
2. [Вторая цель]
3. [Третья цель]

TOP_BARRIERS:
1. [Главный барьер с гипотезой о причине]
2. [Второй барьер]
3. [Третий барьер]

PATTERNS:
1. [Паттерн который повторяется в ответах]
2. [Ещё паттерн]
3. [Ещё паттерн]

CONTRADICTIONS:
1. [Противоречие: цель X vs барьер Y]
2. [Ещё противоречие]

HYPOTHESIS: [Психологическая динамика одним абзацем - что движет этим человеком, какой внутренний конфликт]

---

ПРАВИЛА:
- Используй КОНКРЕТИКУ из данных (цитаты!)
- НЕ выдумывай то, чего нет в данных
- Будь кратким и точным
- Фокусируйся на психологически значимом"""

    def __init__(self, db_pool=None, redis_client=None, ai_client=None):
        """
        Args:
            db_pool: AsyncPG pool для загрузки данных
            redis_client: Redis для кэширования досье
            ai_client: AI клиент для генерации (Claude/GPT-4o)
        """
        self.db_pool = db_pool
        self.redis_client = redis_client
        self.ai_client = ai_client

        # In-memory cache (fallback если нет Redis)
        self._cache: Dict[int, UserDossier] = {}

        # Настройки
        self.cache_ttl = 3600  # 1 час
        self.update_threshold = 5  # Обновлять после 5 новых ответов

        logger.info("📋 UserDossierService initialized")

    async def get_dossier(self, user_id: int, force_regenerate: bool = False) -> UserDossier:
        """
        Получить досье пользователя.

        1. Проверяем кэш (Redis/memory)
        2. Проверяем нужно ли обновить (по хэшу данных)
        3. Генерируем если нужно

        Args:
            user_id: ID пользователя
            force_regenerate: Принудительно перегенерировать

        Returns:
            UserDossier с AI-резюме
        """
        # 1. Пробуем из кэша
        if not force_regenerate:
            cached = await self._get_cached_dossier(user_id)
            if cached:
                # Проверяем актуальность
                if await self._is_dossier_valid(user_id, cached):
                    logger.debug(f"📋 Using cached dossier for user {user_id}")
                    return cached
                else:
                    logger.info(f"📋 Dossier outdated for user {user_id}, regenerating...")

        # 2. Генерируем новое досье
        dossier = await self._generate_dossier(user_id)

        # 3. Кэшируем
        await self._cache_dossier(user_id, dossier)

        return dossier

    async def invalidate_dossier(self, user_id: int):
        """Инвалидировать кэш досье (вызывать после новых ответов)"""
        cache_key = f"dossier:{user_id}"

        if self.redis_client:
            try:
                await self.redis_client.delete(cache_key)
            except Exception as e:
                logger.warning(f"Redis delete failed: {e}")

        if user_id in self._cache:
            del self._cache[user_id]

        logger.info(f"📋 Invalidated dossier for user {user_id}")

    async def _get_cached_dossier(self, user_id: int) -> Optional[UserDossier]:
        """Получить досье из кэша"""
        cache_key = f"dossier:{user_id}"

        # Сначала Redis
        if self.redis_client:
            try:
                data = await self.redis_client.get(cache_key)
                if data:
                    return self._deserialize_dossier(data)
            except Exception as e:
                logger.warning(f"Redis get failed: {e}")

        # Fallback to memory
        return self._cache.get(user_id)

    async def _cache_dossier(self, user_id: int, dossier: UserDossier):
        """Сохранить досье в кэш"""
        cache_key = f"dossier:{user_id}"

        # Redis
        if self.redis_client:
            try:
                data = self._serialize_dossier(dossier)
                await self.redis_client.setex(cache_key, self.cache_ttl, data)
            except Exception as e:
                logger.warning(f"Redis set failed: {e}")

        # Memory fallback
        self._cache[user_id] = dossier

    async def _is_dossier_valid(self, user_id: int, dossier: UserDossier) -> bool:
        """Проверить актуальность досье"""
        if not self.db_pool:
            return True

        try:
            async with self.db_pool.acquire() as conn:
                # Проверяем количество ответов
                row = await conn.fetchrow("""
                    SELECT COUNT(*) as count
                    FROM selfology.user_answers_v2
                    WHERE user_id = $1
                """, user_id)

                current_count = row['count'] if row else 0

                # Если новых ответов >= threshold - нужно обновить
                if current_count - dossier.answers_count_at_generation >= self.update_threshold:
                    return False

                # Проверяем хэш данных
                current_hash = await self._compute_data_hash(user_id)
                if current_hash != dossier.raw_data_hash:
                    return False

                return True

        except Exception as e:
            logger.warning(f"Validity check failed: {e}")
            return True  # Безопасный fallback

    async def _generate_dossier(self, user_id: int) -> UserDossier:
        """
        Сгенерировать досье через AI.

        ГЛАВНАЯ ЛОГИКА:
        1. Загружаем ВСЕ данные из digital_personality
        2. Формируем промпт
        3. Генерируем через Claude/GPT-4o
        4. Парсим результат
        """
        dossier = UserDossier(user_id=user_id)

        # Загружаем данные
        raw_data = await self._load_raw_data(user_id)

        if not raw_data or not any(raw_data.values()):
            logger.warning(f"No data for user {user_id}, returning empty dossier")
            return dossier

        # Генерируем через AI
        if self.ai_client:
            ai_dossier = await self._generate_via_ai(raw_data)
            if ai_dossier:
                dossier = ai_dossier
                dossier.user_id = user_id
        else:
            # Fallback: простое извлечение топ-N
            dossier = self._extract_simple_dossier(user_id, raw_data)

        # Добавляем метаданные
        dossier.generated_at = datetime.now()
        dossier.answers_count_at_generation = raw_data.get('answers_count', 0)
        dossier.raw_data_hash = await self._compute_data_hash(user_id)

        # Добавляем style hints из Big Five
        big_five = raw_data.get('big_five', {})
        dossier.style_hints = self._compute_style_hints(big_five)

        logger.info(f"✅ Generated dossier for user {user_id}")
        return dossier

    async def _load_raw_data(self, user_id: int) -> Dict[str, Any]:
        """Загрузить все сырые данные о пользователе"""
        data = {
            'goals': [],
            'barriers': [],
            'values': [],
            'identity': [],
            'current_state': [],
            'interests': [],
            'recent_answers': [],
            'big_five': {},
            'answers_count': 0
        }

        if not self.db_pool:
            return data

        try:
            async with self.db_pool.acquire() as conn:
                # 1. Digital personality
                row = await conn.fetchrow("""
                    SELECT identity, interests, goals, barriers, relationships,
                           values, current_state, skills, experiences, health,
                           total_answers_analyzed
                    FROM selfology.digital_personality
                    WHERE user_id = $1
                """, user_id)

                if row:
                    for field in ['goals', 'barriers', 'values', 'identity',
                                  'current_state', 'interests']:
                        field_data = row.get(field)
                        if field_data:
                            if isinstance(field_data, str):
                                try:
                                    field_data = json.loads(field_data)
                                except:
                                    field_data = []
                            data[field] = field_data if isinstance(field_data, list) else []

                    data['answers_count'] = row['total_answers_analyzed'] or 0

                # 2. Big Five
                big_five_row = await conn.fetchrow("""
                    SELECT openness, conscientiousness, extraversion,
                           agreeableness, neuroticism
                    FROM selfology.personality_profile
                    WHERE user_id = $1
                """, user_id)

                if big_five_row:
                    data['big_five'] = {
                        'openness': self._extract_score(big_five_row['openness']),
                        'conscientiousness': self._extract_score(big_five_row['conscientiousness']),
                        'extraversion': self._extract_score(big_five_row['extraversion']),
                        'agreeableness': self._extract_score(big_five_row['agreeableness']),
                        'neuroticism': self._extract_score(big_five_row['neuroticism'])
                    }

                # 3. Последние ответы
                answers = await conn.fetch("""
                    SELECT question_id, answer_text, answered_at
                    FROM selfology.user_answers_v2
                    WHERE user_id = $1
                    ORDER BY answered_at DESC
                    LIMIT 10
                """, user_id)

                data['recent_answers'] = [
                    {
                        'question_id': a['question_id'],
                        'answer': a['answer_text'][:300] if a['answer_text'] else ''
                    }
                    for a in answers
                ]

        except Exception as e:
            logger.error(f"Failed to load raw data: {e}")

        return data

    def _extract_score(self, value) -> float:
        """Извлечь числовое значение трейта"""
        if value is None:
            return 0.5
        if isinstance(value, dict):
            return float(value.get('score', 0.5))
        if isinstance(value, (int, float)):
            return float(value)
        return 0.5

    async def _generate_via_ai(self, raw_data: Dict[str, Any]) -> Optional[UserDossier]:
        """Сгенерировать досье через AI"""
        try:
            # Форматируем данные для промпта
            prompt = self.DOSSIER_PROMPT.format(
                goals_count=len(raw_data.get('goals', [])),
                goals=self._format_items(raw_data.get('goals', []), 'goal', limit=20),
                barriers_count=len(raw_data.get('barriers', [])),
                barriers=self._format_items(raw_data.get('barriers', []), 'barrier', limit=20),
                values_count=len(raw_data.get('values', [])),
                values=self._format_items(raw_data.get('values', []), 'value', limit=15),
                identity=self._format_items(raw_data.get('identity', []), 'description', limit=10),
                current_state=self._format_items(raw_data.get('current_state', []), 'activity', limit=10),
                recent_answers=self._format_answers(raw_data.get('recent_answers', [])),
                big_five=self._format_big_five(raw_data.get('big_five', {}))
            )

            # Генерируем
            response = await self.ai_client.generate(prompt)

            # Парсим результат
            return self._parse_ai_response(response)

        except Exception as e:
            logger.error(f"AI generation failed: {e}")
            return None

    def _format_items(self, items: List[Dict], key: str, limit: int = 10) -> str:
        """Форматировать список элементов для промпта"""
        if not items:
            return "Нет данных"

        lines = []
        for item in items[:limit]:
            if isinstance(item, dict):
                value = item.get(key) or item.get('description') or str(item)
            else:
                value = str(item)
            lines.append(f"- {value[:200]}")

        if len(items) > limit:
            lines.append(f"... и ещё {len(items) - limit}")

        return "\n".join(lines)

    def _format_answers(self, answers: List[Dict]) -> str:
        """Форматировать последние ответы"""
        if not answers:
            return "Нет ответов"

        lines = []
        for ans in answers[:5]:
            lines.append(f"- {ans.get('answer', '')[:200]}...")

        return "\n".join(lines)

    def _format_big_five(self, big_five: Dict[str, float]) -> str:
        """Форматировать Big Five профиль"""
        if not big_five:
            return "Профиль не определён"

        traits = {
            'openness': 'Открытость',
            'conscientiousness': 'Добросовестность',
            'extraversion': 'Экстраверсия',
            'agreeableness': 'Доброжелательность',
            'neuroticism': 'Нейротизм'
        }

        lines = []
        for key, name in traits.items():
            score = big_five.get(key, 0.5)
            level = "высокий" if score > 0.7 else "низкий" if score < 0.3 else "средний"
            lines.append(f"- {name}: {score:.2f} ({level})")

        return "\n".join(lines)

    def _parse_ai_response(self, response: str) -> Optional[UserDossier]:
        """Парсить ответ AI в UserDossier"""
        try:
            dossier = UserDossier(user_id=0)  # user_id заполнится позже

            # Парсим секции
            lines = response.split('\n')
            current_section = None

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # Определяем секцию
                if line.startswith('WHO:'):
                    dossier.who = line.replace('WHO:', '').strip()
                elif line.startswith('TOP_GOALS:'):
                    current_section = 'goals'
                elif line.startswith('TOP_BARRIERS:'):
                    current_section = 'barriers'
                elif line.startswith('PATTERNS:'):
                    current_section = 'patterns'
                elif line.startswith('CONTRADICTIONS:'):
                    current_section = 'contradictions'
                elif line.startswith('HYPOTHESIS:'):
                    dossier.hypothesis = line.replace('HYPOTHESIS:', '').strip()
                    current_section = 'hypothesis'
                elif line.startswith(('1.', '2.', '3.', '•', '-')):
                    # Элемент списка
                    item = line.lstrip('0123456789.•- ').strip()
                    if current_section == 'goals':
                        dossier.top_goals.append(item)
                    elif current_section == 'barriers':
                        dossier.top_barriers.append(item)
                    elif current_section == 'patterns':
                        dossier.patterns.append(item)
                    elif current_section == 'contradictions':
                        dossier.contradictions.append(item)
                elif current_section == 'hypothesis' and not line.startswith(('TOP', 'PATTERNS', 'CONTRADICTIONS')):
                    # Продолжение гипотезы
                    dossier.hypothesis += ' ' + line

            return dossier

        except Exception as e:
            logger.error(f"Failed to parse AI response: {e}")
            return None

    def _extract_simple_dossier(self, user_id: int, raw_data: Dict[str, Any]) -> UserDossier:
        """
        Fallback: Простое извлечение топ-N без AI.

        Используется если нет AI клиента.
        """
        dossier = UserDossier(user_id=user_id)

        # Топ-3 цели
        goals = raw_data.get('goals', [])
        for goal in goals[:3]:
            if isinstance(goal, dict):
                dossier.top_goals.append(goal.get('goal', str(goal)))
            else:
                dossier.top_goals.append(str(goal))

        # Топ-3 барьера
        barriers = raw_data.get('barriers', [])
        for barrier in barriers[:3]:
            if isinstance(barrier, dict):
                dossier.top_barriers.append(barrier.get('barrier', str(barrier)))
            else:
                dossier.top_barriers.append(str(barrier))

        # Идентичность -> who
        identity = raw_data.get('identity', [])
        if identity:
            who_parts = []
            for item in identity[:2]:
                if isinstance(item, dict):
                    who_parts.append(item.get('description', ''))
                else:
                    who_parts.append(str(item))
            dossier.who = '. '.join(filter(None, who_parts))

        return dossier

    def _compute_style_hints(self, big_five: Dict[str, float]) -> Dict[str, str]:
        """
        Вычислить подсказки по стилю общения из Big Five.

        Используется в промпте коуча для персонализации.
        """
        hints = {}

        # Openness
        openness = big_five.get('openness', 0.5)
        if openness > 0.7:
            hints['подход'] = 'творческий, философский'
        elif openness < 0.3:
            hints['подход'] = 'практичный, конкретный'

        # Conscientiousness
        conscient = big_five.get('conscientiousness', 0.5)
        if conscient > 0.7:
            hints['структура'] = 'пошаговая, организованная'
        elif conscient < 0.3:
            hints['структура'] = 'гибкая, свободная'

        # Extraversion
        extraversion = big_five.get('extraversion', 0.5)
        if extraversion > 0.7:
            hints['энергия'] = 'активная, выразительная'
        elif extraversion < 0.3:
            hints['энергия'] = 'спокойная, рефлексивная'

        # Agreeableness
        agreeableness = big_five.get('agreeableness', 0.5)
        if agreeableness > 0.7:
            hints['тон'] = 'тёплый, поддерживающий'
        elif agreeableness < 0.3:
            hints['тон'] = 'прямой, честный'

        # Neuroticism
        neuroticism = big_five.get('neuroticism', 0.5)
        if neuroticism > 0.7:
            hints['безопасность'] = 'высокая, много reassurance'
        elif neuroticism < 0.3:
            hints['безопасность'] = 'можно углубляться быстрее'

        return hints

    async def _compute_data_hash(self, user_id: int) -> str:
        """Вычислить хэш данных для отслеживания изменений"""
        if not self.db_pool:
            return ""

        try:
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT updated_at FROM selfology.digital_personality
                    WHERE user_id = $1
                """, user_id)

                if row and row['updated_at']:
                    return hashlib.md5(str(row['updated_at']).encode()).hexdigest()[:8]
        except:
            pass

        return ""

    def _serialize_dossier(self, dossier: UserDossier) -> str:
        """Сериализовать досье для Redis"""
        return json.dumps({
            'user_id': dossier.user_id,
            'who': dossier.who,
            'top_goals': dossier.top_goals,
            'top_barriers': dossier.top_barriers,
            'patterns': dossier.patterns,
            'contradictions': dossier.contradictions,
            'hypothesis': dossier.hypothesis,
            'style_hints': dossier.style_hints,
            'generated_at': dossier.generated_at.isoformat() if dossier.generated_at else None,
            'answers_count_at_generation': dossier.answers_count_at_generation,
            'raw_data_hash': dossier.raw_data_hash
        })

    def _deserialize_dossier(self, data: str) -> Optional[UserDossier]:
        """Десериализовать досье из Redis"""
        try:
            d = json.loads(data)
            dossier = UserDossier(
                user_id=d['user_id'],
                who=d.get('who', ''),
                top_goals=d.get('top_goals', []),
                top_barriers=d.get('top_barriers', []),
                patterns=d.get('patterns', []),
                contradictions=d.get('contradictions', []),
                hypothesis=d.get('hypothesis', ''),
                style_hints=d.get('style_hints', {}),
                answers_count_at_generation=d.get('answers_count_at_generation', 0),
                raw_data_hash=d.get('raw_data_hash', '')
            )

            if d.get('generated_at'):
                dossier.generated_at = datetime.fromisoformat(d['generated_at'])

            return dossier
        except:
            return None
