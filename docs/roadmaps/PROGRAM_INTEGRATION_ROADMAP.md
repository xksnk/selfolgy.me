# ROADMAP: Интеграция блочной системы программ

## Обзор

**Цель:** Интегрировать новую блочную систему программ (ProgramRouter) с существующей инфраструктурой анализа.

### Два режима онбординга

| Режим | Цель | Логика |
|-------|------|--------|
| **🎯 Авто** | Быстро построить полный цифровой отпечаток | AI выбирает блоки из ЛЮБОЙ программы, закрывая пробелы в профиле |
| **📚 Программа** | Дать пользователю пройти то, что он хочет | Пользователь выбирает программу, проходит её полностью |

### UX Flow

```
/onboarding
    ↓
┌─────────────────────────────────────────┐
│  Как вы хотите начать?                  │
│                                         │
│  [🎯 Авто]  [📚 Выбрать программу]       │
└─────────────────────────────────────────┘
    ↓                         ↓
┌─────────────────┐    ┌─────────────────┐
│ AI анализирует  │    │ Список 29       │
│ профиль и       │    │ программ        │
│ выбирает блок   │    │ с описаниями    │
│ из любой        │    │                 │
│ программы       │    │ Пользователь    │
│                 │    │ выбирает        │
└────────┬────────┘    └────────┬────────┘
         │                      │
         ▼                      ▼
┌─────────────────────────────────────────┐
│  Блок (4-6 вопросов по одному)          │
│  → Вопрос → Ответ → Анализ → Вопрос...  │
│  → "Блок завершён!"                     │
└─────────────────────────────────────────┘
         │                      │
         ▼                      ▼
┌─────────────────┐    ┌─────────────────┐
│ AI выбирает     │    │ Следующий блок  │
│ следующий блок  │    │ ТОЙ ЖЕ          │
│ (может быть из  │    │ программы       │
│ другой          │    │ по порядку      │
│ программы!)     │    │                 │
└─────────────────┘    └─────────────────┘
```

### Авто-режим: приоритеты выбора блока

1. **Охват доменов** — если нет данных по CAREER, выбрать блок про карьеру
2. **Глубина профиля** — если IDENTITY поверхностный, углубить
3. **Энергетический баланс** — не давать HEAVY после HEAVY
4. **Актуальность** — учитывать что пользователь говорил в чате

---

## ФАЗА 1: Минимальная интеграция (MVP)

### 1.1 Новые состояния FSM
**Файл:** `selfology_controller.py`

```python
class OnboardingStates(StatesGroup):
    # Существующие
    gdpr_consent = State()
    onboarding_active = State()
    waiting_for_answer = State()

    # 🆕 Новые для программ
    choosing_mode = State()           # Выбор: авто / вручную
    choosing_program = State()        # Выбор программы из списка
    program_active = State()          # Активная программа
    waiting_program_answer = State()  # Ожидание ответа в программе
    block_transition = State()        # Переход между блоками
```

### 1.2 Изменение cmd_onboarding
**Файл:** `selfology_controller.py`

```python
async def cmd_onboarding(self, message: Message, state: FSMContext):
    # Проверяем существующую сессию
    session = await self.onboarding_orchestrator.restore_session_from_db(int(telegram_id))

    if session:
        # Есть активная сессия - спрашиваем продолжить или начать программу
        await message.answer(
            "У вас есть незавершённая сессия.\n\n"
            "Продолжить её или начать программу?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="▶️ Продолжить", callback_data="continue_session")],
                [InlineKeyboardButton(text="📚 Выбрать программу", callback_data="choose_program")]
            ])
        )
    else:
        # Новая сессия - выбор режима
        await message.answer(
            "🧠 Как вы хотите начать знакомство?\n\n"
            "**Авто-подбор** — AI выберет вопросы на основе вашего профиля\n"
            "**Программа** — структурированный путь по конкретной теме",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎯 Авто-подбор", callback_data="mode_auto")],
                [InlineKeyboardButton(text="📚 Выбрать программу", callback_data="mode_program")]
            ])
        )
        await state.set_state(OnboardingStates.choosing_mode)
```

### 1.3 Обработчики выбора режима
**Файл:** `selfology_controller.py`

```python
async def callback_mode_auto(self, callback: CallbackQuery, state: FSMContext):
    """Авто-режим - старая логика QuestionRouter"""
    result = await self.onboarding_orchestrator.start_onboarding(int(telegram.id))
    # ... показ вопроса как раньше

async def callback_mode_program(self, callback: CallbackQuery, state: FSMContext):
    """Выбор программы - показываем список"""
    programs = await self.onboarding_orchestrator.get_available_programs(int(telegram_id))

    # Формируем список кнопок (первые 10 программ + "Ещё")
    buttons = []
    for p in programs[:10]:
        buttons.append([InlineKeyboardButton(
            text=f"{p['name']} ({p['questions_count']} вопросов)",
            callback_data=f"program:{p['program_id']}"
        )])

    await callback.message.edit_text(
        "📚 Выберите программу:\n\n"
        "Каждая программа — это структурированный путь из нескольких блоков.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await state.set_state(OnboardingStates.choosing_program)

async def callback_select_program(self, callback: CallbackQuery, state: FSMContext):
    """Выбрана программа - начинаем"""
    program_id = callback.data.split(":")[1]

    result = await self.onboarding_orchestrator.start_program(
        int(telegram_id), program_id
    )

    # Сохраняем program_id в state
    await state.update_data(program_id=program_id)

    # Показываем первый вопрос программы
    await self._show_program_question(result['question'], result, callback.message)
    await state.set_state(OnboardingStates.waiting_program_answer)
```

### 1.4 Подключение анализа к ProgramRouter
**Файл:** `selfology_bot/services/onboarding/orchestrator.py`

Метод `process_program_answer`:
```python
async def process_program_answer(
    self, user_id: int, program_id: str, question_id: str, answer_text: str
) -> Dict[str, Any]:
    """
    Обработать ответ в программе — с полным анализом.

    Использует ту же логику что process_user_answer, но:
    - Сохраняет program_id и block_id в answer
    - Получает следующий вопрос через ProgramRouter
    """

    # 1. Сохраняем ответ в БД (с program_id)
    answer_id = await self.onboarding_dao.save_answer_with_program(
        user_id, question_id, answer_text, program_id
    )

    # 2. Запускаем анализ (как раньше)
    analysis_result = await self.answer_analyzer.analyze_answer(
        user_id=user_id,
        question_id=question_id,
        answer_text=answer_text,
        question_metadata=question_metadata  # Из program_questions
    )

    # 3. Создаём embeddings (как раньше)
    await self.embedding_creator.create_embeddings(
        user_id=user_id,
        answer_text=answer_text,
        analysis=analysis_result,
        program_context={"program_id": program_id, "block_id": block_id}
    )

    # 4. Обновляем личность (как раньше)
    await self.personality_extractor.update_profile(user_id, analysis_result)

    # 5. Получаем следующий вопрос через ProgramRouter
    answered_ids = await self._get_answered_question_ids(user_id, program_id)
    next_result = await self.program_router.get_next_question_in_block(
        user_id, program_id, answered_ids
    )

    return {
        "analysis": analysis_result,
        "next_question": next_result
    }
```

---

## ФАЗА 2: Полная интеграция

### 2.1 Обновление таблицы user_answers_new
```sql
ALTER TABLE selfology.user_answers_new
ADD COLUMN program_id VARCHAR(100),
ADD COLUMN block_id VARCHAR(150);

CREATE INDEX idx_answers_program ON selfology.user_answers_new(program_id);
```

### 2.2 Обновление answer_analysis
```sql
ALTER TABLE selfology.answer_analysis
ADD COLUMN program_id VARCHAR(100),
ADD COLUMN block_id VARCHAR(150),
ADD COLUMN block_type VARCHAR(20);  -- Foundation/Exploration/Integration
```

### 2.3 Метаданные вопроса из БД
**Файл:** `selfology_bot/services/onboarding/orchestrator.py`

```python
async def _get_question_metadata_from_db(self, question_id: str) -> Dict:
    """Получить метаданные вопроса из program_questions вместо JSON"""
    async with self.db_service.pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT
                journey_stage, depth_level, domain, energy_dynamic,
                complexity, emotional_weight, safety_level,
                trust_requirement, recommended_model
            FROM selfology.program_questions
            WHERE question_id = $1
        """, question_id)

        return dict(row) if row else {}
```

### 2.4 Учёт блока в AI роутинге
**Файл:** `services/chat_coach.py` (Enhanced Router)

```python
def select_model_for_question(self, question_metadata: Dict) -> str:
    """Выбор модели с учётом block_type"""

    # Из метаданных программы
    block_type = question_metadata.get('block_type')
    recommended = question_metadata.get('recommended_model')

    if recommended:
        return recommended

    # Fallback по block_type
    if block_type == 'Integration':
        return 'claude-sonnet-4'  # Интеграционные требуют качества
    elif block_type == 'Exploration':
        return 'gpt-4o'
    else:
        return 'gpt-4o-mini'
```

---

## ФАЗА 3: Прогресс и аналитика

### 3.1 Обновление прогресса в user_program_progress
```python
async def update_program_progress(self, user_id: int, program_id: str, question_id: str):
    """Обновить прогресс после ответа на вопрос"""
    async with self.db_service.pool.acquire() as conn:
        # Увеличиваем счётчик
        await conn.execute("""
            UPDATE selfology.user_program_progress
            SET
                questions_answered = questions_answered + 1,
                last_activity_at = NOW()
            WHERE user_id = $1 AND program_id = $2 AND status = 'active'
        """, user_id, program_id)

        # Пересчитываем процент
        await conn.execute("""
            UPDATE selfology.user_program_progress up
            SET completion_percentage = (
                SELECT ROUND(100.0 * up.questions_answered / COUNT(*))
                FROM selfology.program_questions pq
                WHERE pq.program_id = up.program_id
            )
            WHERE user_id = $1 AND program_id = $2
        """, user_id, program_id)
```

### 3.2 Переходы между блоками
```python
async def handle_block_transition(
    self, user_id: int, program_id: str, callback: CallbackQuery
):
    """Показать сообщение о переходе к новому блоку"""
    next_block = await self.program_router.get_next_block(user_id, program_id)

    if not next_block:
        # Программа завершена
        return await self._complete_program(user_id, program_id, callback)

    # Показываем промежуточное сообщение
    block_emoji = {"Foundation": "🌱", "Exploration": "🔍", "Integration": "🎯"}

    await callback.message.answer(
        f"✅ Блок завершён!\n\n"
        f"Следующий блок:\n"
        f"{block_emoji[next_block['type']]} **{next_block['name']}**\n"
        f"_{next_block['description']}_\n\n"
        f"Вопросов: {next_block['questions_count']}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="▶️ Продолжить", callback_data="continue_block")],
            [InlineKeyboardButton(text="⏸ Пауза", callback_data="pause_program")]
        ])
    )
```

### 3.3 Завершение программы
```python
async def _complete_program(self, user_id: int, program_id: str, target):
    """Завершить программу и показать итоги"""

    # Получаем статистику
    progress = await self.program_router.get_program_context(user_id, program_id)

    # Генерируем инсайты по программе
    insights = await self._generate_program_insights(user_id, program_id)

    await target.answer(
        f"🎉 Поздравляем! Вы завершили программу **{progress.program_name}**!\n\n"
        f"📊 Статистика:\n"
        f"• Блоков пройдено: {len(progress.blocks_completed)}\n"
        f"• Вопросов отвечено: {progress.questions_answered}\n\n"
        f"💡 Ключевые инсайты:\n{insights}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📚 Другая программа", callback_data="choose_program")],
            [InlineKeyboardButton(text="💬 Чат с коучем", callback_data="start_chat")]
        ])
    )
```

---

## ФАЗА 4: Авто-режим (BlockSelector)

### 4.1 Новый компонент: AutoBlockSelector
**Файл:** `selfology_bot/services/onboarding/auto_block_selector.py`

Выбирает следующий блок из ЛЮБОЙ программы для максимального охвата профиля.

```python
class AutoBlockSelector:
    """
    Интеллектуальный выбор блока для авто-режима.

    Цель: быстро построить полный цифровой отпечаток личности.
    """

    async def select_next_block(self, user_id: int) -> Dict[str, Any]:
        """
        Выбрать следующий блок из любой программы.

        Алгоритм:
        1. Получить текущий профиль (domain coverage)
        2. Найти "пробелы" — домены с малым количеством данных
        3. Найти блоки, которые закрывают эти пробелы
        4. Учесть энергетический баланс
        5. Выбрать оптимальный блок
        """

        # 1. Анализ текущего профиля
        profile_gaps = await self._analyze_profile_gaps(user_id)
        # Пример: {"CAREER": 0.2, "RELATIONSHIPS": 0.8, "IDENTITY": 0.5}

        # 2. Получить пройденные блоки
        completed_blocks = await self._get_completed_blocks(user_id)

        # 3. Получить все доступные блоки с их доменами
        available_blocks = await self._get_available_blocks(completed_blocks)

        # 4. Скоринг блоков
        scored_blocks = []
        for block in available_blocks:
            score = self._calculate_block_score(
                block=block,
                profile_gaps=profile_gaps,
                last_energy=await self._get_last_energy(user_id)
            )
            scored_blocks.append((block, score))

        # 5. Выбрать лучший
        scored_blocks.sort(key=lambda x: x[1], reverse=True)
        selected = scored_blocks[0][0]

        return {
            "block_id": selected["block_id"],
            "block_name": selected["name"],
            "program_name": selected["program_name"],
            "reason": self._generate_reason(selected, profile_gaps)
        }

    def _calculate_block_score(
        self,
        block: Dict,
        profile_gaps: Dict[str, float],
        last_energy: str
    ) -> float:
        """
        Скоринг блока.

        Факторы:
        - gap_coverage: насколько блок закрывает пробелы (0-1)
        - energy_balance: не HEAVY после HEAVY (0-1)
        - foundation_priority: Foundation блоки важнее для новых пользователей
        - diversity: разнообразие программ
        """
        score = 0.0

        # Покрытие пробелов (главный фактор)
        block_domain = block.get("primary_domain", "GENERAL")
        gap_value = profile_gaps.get(block_domain, 0.5)
        score += (1 - gap_value) * 0.5  # Чем меньше данных, тем выше приоритет

        # Энергетический баланс
        if last_energy == "HEAVY" and block.get("energy_dynamic") == "HEAVY":
            score -= 0.3  # Штраф за HEAVY после HEAVY
        elif last_energy == "HEAVY" and block.get("energy_dynamic") == "HEALING":
            score += 0.2  # Бонус за HEALING после HEAVY

        # Foundation приоритет для новых
        if block.get("block_type") == "Foundation":
            score += 0.1

        return score

    async def _analyze_profile_gaps(self, user_id: int) -> Dict[str, float]:
        """
        Анализ покрытия доменов в профиле.

        Возвращает: {domain: coverage} где coverage 0-1
        0 = нет данных, 1 = полное покрытие
        """
        async with self.db_pool.acquire() as conn:
            # Считаем ответы по доменам
            domain_counts = await conn.fetch("""
                SELECT
                    pq.domain,
                    COUNT(*) as answer_count
                FROM selfology.user_answers_new ua
                JOIN selfology.program_questions pq ON ua.question_json_id = pq.question_id
                WHERE ua.user_id = $1
                GROUP BY pq.domain
            """, user_id)

            # Нормализуем (5 ответов = полное покрытие)
            all_domains = [
                "IDENTITY", "RELATIONSHIPS", "CAREER", "HEALTH",
                "EMOTIONAL", "PURPOSE", "GROWTH", "FINANCES", "TIME", "TECHNOLOGY"
            ]

            coverage = {}
            counts = {r["domain"]: r["answer_count"] for r in domain_counts}

            for domain in all_domains:
                count = counts.get(domain, 0)
                coverage[domain] = min(1.0, count / 5.0)

            return coverage
```

### 4.2 Таблица для авто-режима
```sql
-- Отслеживание пройденных блоков в авто-режиме
CREATE TABLE IF NOT EXISTS selfology.user_auto_progress (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    block_id VARCHAR(150) NOT NULL,
    program_id VARCHAR(100) NOT NULL,
    completed_at TIMESTAMP DEFAULT NOW(),
    questions_answered INTEGER DEFAULT 0,

    UNIQUE(user_id, block_id)
);

CREATE INDEX idx_auto_progress_user ON selfology.user_auto_progress(user_id);
```

### 4.3 Интеграция в Orchestrator
```python
async def start_auto_onboarding(self, user_id: int) -> Dict[str, Any]:
    """Начать авто-онбординг — AI выбирает блок"""

    # Выбираем блок
    selection = await self.auto_block_selector.select_next_block(user_id)

    # Показываем пользователю что выбрано
    return {
        "mode": "auto",
        "block": selection,
        "message": f"Для вас подобран блок: {selection['block_name']}\n"
                   f"Из программы: {selection['program_name']}\n"
                   f"Причина: {selection['reason']}"
    }

async def get_next_auto_block(self, user_id: int) -> Dict[str, Any]:
    """Получить следующий блок в авто-режиме"""

    # Сохраняем текущий блок как пройденный
    await self._save_auto_progress(user_id, current_block_id)

    # Выбираем следующий
    return await self.auto_block_selector.select_next_block(user_id)
```

### 4.4 Пример работы авто-режима

```
Пользователь: /onboarding → Авто

AI анализирует профиль:
  - IDENTITY: 0.0 (нет данных)
  - CAREER: 0.0 (нет данных)
  - RELATIONSHIPS: 0.0 (нет данных)

AI выбирает: "Здесь и сейчас" из "Подумать о жизни"
Причина: Foundation блок для начала, охватывает IDENTITY

→ 4 вопроса блока
→ Блок завершён!

AI анализирует:
  - IDENTITY: 0.6 (есть данные)
  - CAREER: 0.0 (пробел!)
  - RELATIONSHIPS: 0.2

AI выбирает: "Где я сейчас" из "Подумать о карьере"
Причина: Закрывает пробел в CAREER

→ 5 вопросов блока
→ ...
```

---

## Затронутые файлы

| Файл | Изменения |
|------|-----------|
| `selfology_controller.py` | Новые состояния FSM, обработчики выбора программы |
| `orchestrator.py` | Методы process_program_answer, update_program_progress |
| `program_router.py` | Уже создан ✅ |
| `onboarding_dao.py` | Методы save_answer_with_program |
| `answer_analyzer.py` | Передача program_context |
| `embedding_creator.py` | Добавление program_id в payload |
| `services/chat_coach.py` | Учёт block_type в роутинге |

---

## План выполнения

| Этап | Задачи | Оценка |
|------|--------|--------|
| **MVP** | FSM + выбор режима + базовый flow | 2-3 часа |
| **Анализ** | Подключение AnswerAnalyzer к программам | 1-2 часа |
| **Прогресс** | Учёт прогресса, переходы блоков | 1-2 часа |
| **Авто-подбор** | AI выбор программы | 1 час |
| **Тесты** | E2E тест полного flow | 1 час |
| **Итого** | | **6-9 часов** |

---

## Риски и митигации

| Риск | Митигация |
|------|-----------|
| Старые сессии не совместимы | Флаг `session_type: 'program' / 'classic'` |
| Потеря данных при рестарте | program_id в БД, восстановление из user_program_progress |
| Долгий анализ блокирует UX | Background tasks как сейчас |
