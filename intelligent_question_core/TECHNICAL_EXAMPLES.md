# 🔧 ТЕХНИЧЕСКИЕ ПРИМЕРЫ И WORKFLOW ПАТТЕРНЫ

## 🎯 Конкретные примеры использования Intelligent Question Core

---

## 📋 ПРИМЕР 1: Полный цикл работы с пользователем

### **Инициализация системы:**

```python
from intelligent_question_core.api.core_api import SelfologyQuestionCore

# Загружаем ядро (один раз при старте)
core = SelfologyQuestionCore("intelligent_question_core/data/selfology_intelligent_core.json")

# Инициализируем пользователя
user_id = 12345
user_profile = {
    "trust_level": 1,        # начинаем с минимального доверия
    "energy_level": 0.0,     # нейтральная энергия
    "session_count": 0,
    "depth_tolerance": "CONSCIOUS",
    "preferred_domains": [],  # пока неизвестно
    "communication_style": "unknown"
}

user_vector = create_initial_personality_vector()  # все значения 0.0
```

### **Выбор первого вопроса:**

```python
# Первый вопрос - безопасный и открывающий
first_questions = core.search_questions(
    journey_stage="ENTRY",     # этап входа
    energy="OPENING",          # дающий энергию
    min_safety=5,             # максимально безопасный
    complexity_max=2          # простой для понимания
)

# Берем случайный из безопасных или самый популярный
selected_question = first_questions[0]

print(f"Первый вопрос: {selected_question['text']}")
# Пример: "Если бы ваша жизнь была фильмом, какой сейчас жанр?"
```

### **Обработка первого ответа:**

```python
user_answer = "Наверное, комедия положений, но иногда превращается в триллер"

# Анализ через рекомендованную модель
recommended_model = selected_question["processing_hints"]["recommended_model"]

answer_analysis = {
    "emotional_state": "mixed_positive",     # смешанный позитив
    "openness": 0.7,                        # довольно открытый ответ
    "creativity": 0.8,                      # высокая креативность в метафоре
    "anxiety_markers": 0.4,                 # умеренная тревожность ("триллер")
    "humor_as_defense": 0.6,                # использует юмор как защиту
    "self_awareness": 0.6,                  # осознает переходы состояний
    "resistance": 0.1                       # низкое сопротивление
}

# Обновляем вектор личности
user_vector["creativity"] += 0.8 * 0.1
user_vector["openness"] += 0.7 * 0.1  
user_vector["anxiety"] += 0.4 * 0.1
user_vector["humor_as_defense"] += 0.6 * 0.1
user_vector["self_awareness"] += 0.6 * 0.1

# Обновляем профиль пользователя
user_profile["trust_level"] = min(5, user_profile["trust_level"] + 0.2)  # доверие растет
user_profile["energy_level"] += 0.3  # OPENING вопрос дал энергию
user_profile["preferred_domains"].append("IDENTITY")  # показал интерес к самопониманию
```

### **Выбор второго вопроса:**

```python
# Ищем связанные вопросы
connected_questions = core.find_connected_questions(
    selected_question["id"],
    connection_type="thematic_cluster"  # тематически близкие
)

# Фильтруем по обновленному профилю пользователя  
suitable_questions = [
    q for q in connected_questions
    if (q["psychology"]["trust_requirement"] <= user_profile["trust_level"] and
        q["psychology"]["safety_level"] >= 3)
]

# Или исследуем креативность (раз показал высокие показатели)
creativity_questions = core.search_questions(
    domain="CREATIVITY",
    energy="PROCESSING",       # можем углубиться после успешного начала
    trust_requirement_max=2    # пока доверие низкое
)

# Выбираем лучший вариант
if suitable_questions:
    next_question = suitable_questions[0]
else:
    next_question = creativity_questions[0]

print(f"Второй вопрос: {next_question['text']}")
# Пример: "Что зажигает вас настолько, что забываете про время?"
```

---

## 📋 ПРИМЕР 2: Работа с сопротивлением

```python
def handle_user_resistance(user_answer, current_question, user_profile):
    """Обработка сопротивления или дискомфорта пользователя"""
    
    # Детектируем признаки сопротивления
    resistance_indicators = [
        "не знаю", "сложно сказать", "неважно", "без разницы",
        "предпочитаю не говорить", "а что вы думаете"
    ]
    
    resistance_score = sum(1 for indicator in resistance_indicators 
                          if indicator in user_answer.lower()) / len(resistance_indicators)
    
    if resistance_score > 0.3:  # высокое сопротивление
        print("🛡️ Обнаружено сопротивление - адаптируемся")
        
        # 1. Снижаем интенсивность
        easier_questions = core.search_questions(
            energy="NEUTRAL",           # нейтральная энергетика
            complexity_max=2,           # простые вопросы
            safety_level_min=4,         # высокая безопасность
            trust_requirement_max=user_profile["trust_level"]
        )
        
        # 2. Возвращаемся к более поверхностным темам
        surface_questions = core.search_questions(
            depth_level="SURFACE",
            journey_stage="WARMING"
        )
        
        # 3. Или переключаемся на позитивные темы
        positive_questions = core.search_questions(
            domain="CREATIVITY",        # обычно приятная тема
            energy="OPENING"           # дает энергию
        )
        
        # Выбираем стратегию
        strategy_questions = easier_questions + surface_questions + positive_questions
        return strategy_questions[0]  # берем первый подходящий
    
    else:
        # Сопротивления нет - продолжаем по плану
        return select_next_by_connections(current_question, user_profile)
```

---

## 📋 ПРИМЕР 3: Энергетическое управление сессией

```python
def manage_session_energy(session_state, questions_asked):
    """Отслеживание и управление энергетикой сессии"""
    
    # Подсчитываем текущую энергию сессии
    total_energy = 0.0
    energy_history = []
    
    for question in questions_asked:
        energy_impact = get_energy_impact(question["classification"]["energy_dynamic"])
        total_energy += energy_impact
        energy_history.append(total_energy)
    
    print(f"📊 Энергетика сессии: {total_energy:.2f}")
    
    # Проверяем критические состояния
    if total_energy < -2.0:
        print("🚨 КРИТИЧНО: Энергия упала слишком низко!")
        
        # ОБЯЗАТЕЛЬНЫЕ восстанавливающие вопросы
        healing_questions = core.search_questions(
            energy="HEALING",
            min_safety=5,
            complexity_max=2
        )
        
        return {
            "action": "immediate_healing",
            "questions": healing_questions[:3],
            "reasoning": "Восстановление энергии критически важно"
        }
    
    elif total_energy < -1.0:
        print("⚠️ Энергия понижена - нужна поддержка")
        
        # Поддерживающие вопросы
        support_questions = core.search_questions(
            energy=["NEUTRAL", "OPENING"],
            safety_level_min=4
        )
        
        return {
            "action": "energy_support", 
            "questions": support_questions[:2],
            "reasoning": "Поддержка энергетического состояния"
        }
    
    elif total_energy > 1.5:
        print("✨ Высокая энергия - можно углубляться")
        
        # Можно задавать более сложные вопросы
        deeper_questions = core.search_questions(
            depth_level=["EDGE", "SHADOW"],
            energy="PROCESSING"
        )
        
        return {
            "action": "deepen_exploration",
            "questions": deeper_questions,
            "reasoning": "Пользователь энергичен и готов к глубокой работе"
        }
    
    else:
        print("⚖️ Энергия в норме - продолжаем исследование")
        return {"action": "continue_normal_flow"}

def get_energy_impact(energy_type):
    """Получить числовое воздействие типа энергетики"""
    energy_values = {
        "OPENING": +0.4,      # дает энергию
        "NEUTRAL": 0.0,       # нейтрально
        "PROCESSING": -0.1,   # слегка забирает (мышление)
        "HEAVY": -0.6,        # сильно забирает
        "HEALING": +0.5       # восстанавливает
    }
    return energy_values.get(energy_type, 0.0)
```

---

## 📋 ПРИМЕР 4: Адаптация под тип личности

```python
def personalize_question_selection(user_vector, base_question_pool):
    """Персонализация выбора вопросов под тип личности"""
    
    personalized_pool = []
    
    # Для аналитического типа
    if user_vector["analytical_thinking"] > 0.6:
        # Предпочитают структурированные, логичные вопросы
        analytical_questions = [
            q for q in base_question_pool
            if q["classification"]["question_type"] in ["DIRECT", "SCALING"]
            and q["psychology"]["complexity"] >= 3
        ]
        personalized_pool.extend(analytical_questions)
    
    # Для эмоционального типа
    if user_vector["emotional_intelligence"] > 0.6:
        # Предпочитают вопросы про чувства и отношения
        emotional_questions = [
            q for q in base_question_pool  
            if q["classification"]["domain"] in ["EMOTIONS", "RELATIONSHIPS"]
            and q["classification"]["energy_dynamic"] != "HEAVY"
        ]
        personalized_pool.extend(emotional_questions)
    
    # Для креативного типа
    if user_vector["creativity"] > 0.6:
        # Предпочитают проективные и метафорические вопросы
        creative_questions = [
            q for q in base_question_pool
            if q["classification"]["question_type"] == "PROJECTIVE"
            or q["classification"]["domain"] == "CREATIVITY"
        ]
        personalized_pool.extend(creative_questions)
    
    # Для тревожного типа
    if user_vector["anxiety"] > 0.6:
        # Избегаем стрессовых тем, больше поддержки
        anxiety_safe_questions = [
            q for q in base_question_pool
            if q["psychology"]["safety_level"] >= 4
            and q["classification"]["energy_dynamic"] in ["OPENING", "HEALING", "NEUTRAL"]
            and q["classification"]["domain"] not in ["TRAUMA", "PAST"]  # избегаем болезненных тем
        ]
        personalized_pool = anxiety_safe_questions  # заменяем, не добавляем
    
    return personalized_pool if personalized_pool else base_question_pool
```

---

## 📋 ПРИМЕР 5: Построение тематических маршрутов

```python
def create_thematic_journey(starting_domain, user_profile, target_depth="EDGE"):
    """Создание целенаправленного маршрута по теме"""
    
    # Пример: исследование темы RELATIONSHIPS
    relationship_journey = []
    
    # 1. Начинаем с безопасного уровня
    entry_questions = core.search_questions(
        domain="RELATIONSHIPS",
        depth_level="CONSCIOUS", 
        energy="OPENING"
    )
    relationship_journey.extend(entry_questions[:2])
    
    # 2. Переходим к исследованию
    exploration_questions = core.search_questions(
        domain="RELATIONSHIPS",
        depth_level="CONSCIOUS",
        energy="PROCESSING"  
    )
    relationship_journey.extend(exploration_questions[:3])
    
    # 3. Углубляемся (если пользователь готов)
    if user_profile["trust_level"] >= 3:
        deeper_questions = core.search_questions(
            domain="RELATIONSHIPS", 
            depth_level="EDGE",
            energy="PROCESSING"
        )
        relationship_journey.extend(deeper_questions[:2])
    
    # 4. ОБЯЗАТЕЛЬНО завершаем поддержкой
    healing_questions = core.search_questions(
        domain="RELATIONSHIPS",
        energy="HEALING",
        min_safety=4
    )
    relationship_journey.extend(healing_questions[:1])
    
    return relationship_journey

# Использование:
journey = create_thematic_journey("RELATIONSHIPS", user_profile)
print(f"Создан маршрут из {len(journey)} вопросов по отношениям")
```

---

## 📋 ПРИМЕР 6: Работа с графом связей

```python
def explore_connections_intelligently(current_question_id, exploration_strategy="balanced"):
    """Умное исследование связей между вопросами"""
    
    current_question = core.get_question(current_question_id)
    all_connections = core.find_connected_questions(current_question_id)
    
    if exploration_strategy == "deepening":
        # Ищем углубляющие связи
        deep_connections = [
            conn for conn in all_connections
            if conn["connection_info"]["type"] == "depth_progression"
        ]
        return deep_connections
        
    elif exploration_strategy == "broadening":
        # Ищем тематически близкие
        broad_connections = [
            conn for conn in all_connections  
            if conn["connection_info"]["type"] == "thematic_cluster"
        ]
        return broad_connections
        
    elif exploration_strategy == "healing":
        # Ищем энергетически балансирующие
        healing_connections = [
            conn for conn in all_connections
            if conn["connection_info"]["type"] == "energy_balance"
            and conn["classification"]["energy_dynamic"] == "HEALING"
        ]
        return healing_connections
    
    else:  # balanced
        # Смешанная стратегия - по силе связи
        return sorted(all_connections, 
                     key=lambda x: x["connection_info"]["strength"], 
                     reverse=True)[:3]

# Пример использования:
# После глубокого вопроса про отношения ищем исцеляющие
healing_options = explore_connections_intelligently("q_187", "healing")
```

---

## 📋 ПРИМЕР 7: Обработка специальных случаев

### **Случай A: Пользователь избегает темы**

```python
def handle_topic_avoidance(avoided_domain, user_profile):
    """Когда пользователь избегает определенную тему"""
    
    print(f"👤 Пользователь избегает домен: {avoided_domain}")
    
    # Стратегии обхода сопротивления:
    
    # 1. Через смежные темы
    if avoided_domain == "RELATIONSHIPS":
        # Подходим через CREATIVITY или WORK
        bridge_questions = core.search_questions(
            domain=["CREATIVITY", "WORK"],
            keyword_contains=["люди", "команда", "общение"]  # связанные темы
        )
    
    # 2. Через более легкий уровень глубины
    elif avoided_domain == "PAST":
        # Избегает прошлое - начинаем с SURFACE
        gentle_past_questions = core.search_questions(
            domain="PAST",
            depth_level="SURFACE",     # поверхностный уровень
            energy="NEUTRAL"           # без эмоциональной нагрузки
        )
    
    # 3. Через позитивную энергетику
    else:
        positive_approach = core.search_questions(
            domain=avoided_domain,
            energy="OPENING",          # позитивная подача
            safety_level_min=4
        )
    
    return bridge_questions or gentle_past_questions or positive_approach
```

### **Случай B: Пользователь готов к прорыву**

```python
def facilitate_breakthrough(user_id, readiness_indicators):
    """Когда пользователь готов к глубокой работе"""
    
    # Признаки готовности:
    if (readiness_indicators["trust_level"] >= 4 and
        readiness_indicators["session_count"] >= 5 and  
        readiness_indicators["previous_depth_tolerance"] >= "EDGE"):
        
        # Ищем прорывные вопросы
        breakthrough_questions = core.search_questions(
            journey_stage="BREAKTHROUGH",
            depth_level=["SHADOW", "CORE"],
            trust_requirement_max=readiness_indicators["trust_level"]
        )
        
        # ОБЯЗАТЕЛЬНО планируем поддержку
        healing_backup = core.search_questions(
            energy="HEALING",
            domain=breakthrough_questions[0]["classification"]["domain"],  # та же тема
            min_safety=5
        )
        
        return {
            "breakthrough_question": breakthrough_questions[0],
            "healing_backup": healing_backup[:2],
            "warning": "Подготовьте эмоциональную поддержку"
        }
```

---

## 📋 ПРИМЕР 8: Создание персонализированного AI коуча

```python
def create_ai_coach_personality(user_vector):
    """Адаптация стиля AI коуча под пользователя"""
    
    coach_style = {
        "tone": "neutral",
        "directness": 0.5,
        "emotional_support": 0.5,
        "structure_level": 0.5,
        "metaphor_usage": 0.5
    }
    
    # Адаптируем под тип пользователя
    if user_vector["anxiety"] > 0.6:
        coach_style.update({
            "tone": "gentle_supportive",
            "emotional_support": 0.9,
            "directness": 0.3,        # мягче подходим
            "structure_level": 0.8    # больше структуры для безопасности
        })
    
    if user_vector["analytical_thinking"] > 0.7:
        coach_style.update({
            "structure_level": 0.9,   # максимум структуры
            "directness": 0.8,        # прямые вопросы
            "metaphor_usage": 0.2     # минимум метафор
        })
    
    if user_vector["creativity"] > 0.7:
        coach_style.update({
            "metaphor_usage": 0.9,    # максимум метафор
            "structure_level": 0.3,   # минимум структуры
            "tone": "inspiring"       # вдохновляющий тон
        })
    
    # Применяем стиль к выбору вопросов
    if coach_style["metaphor_usage"] > 0.6:
        question_preference = core.search_questions(question_type="PROJECTIVE")
    else:
        question_preference = core.search_questions(question_type="DIRECT")
    
    return coach_style, question_preference
```

---

## 🔧 ОБРАБОТКА ОШИБОК И EDGE CASES

### **Случай 1: Нет подходящих вопросов**

```python
def handle_no_suitable_questions(user_profile, current_context):
    """Когда поиск не дал результатов"""
    
    # Fallback стратегия: расширяем критерии поиска
    
    # 1. Убираем ограничение по домену
    broader_search = core.search_questions(
        min_safety=user_profile["trust_level"],
        energy=["NEUTRAL", "OPENING"]  # безопасная энергетика
    )
    
    if broader_search:
        return broader_search[0]
    
    # 2. Снижаем требования к доверию
    trust_relaxed = core.search_questions(
        trust_requirement_max=max(1, user_profile["trust_level"] - 1),
        min_safety=4
    )
    
    if trust_relaxed:
        return trust_relaxed[0]
    
    # 3. Emergency fallback - всегда безопасные вопросы
    emergency_questions = core.search_questions(
        journey_stage="ENTRY",
        energy="OPENING", 
        min_safety=5
    )
    
    return emergency_questions[0] if emergency_questions else create_generic_question()
```

### **Случай 2: Технические проблемы с ядром**

```python
def handle_core_errors():
    """Обработка технических ошибок ядра"""
    
    try:
        # Проверяем доступность ядра
        test_question = core.get_question("q_001")
        if not test_question:
            raise Exception("Core data corrupted")
            
    except FileNotFoundError:
        print("❌ Файл ядра не найден")
        return fallback_to_basic_questions()
        
    except json.JSONDecodeError:
        print("❌ Поврежденные данные ядра")
        return fallback_to_basic_questions()
        
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return fallback_to_basic_questions()

def fallback_to_basic_questions():
    """Аварийный набор вопросов если ядро недоступно"""
    return [
        {"text": "Как дела?", "energy": "OPENING", "safety": 5},
        {"text": "Что вас радует в жизни?", "energy": "OPENING", "safety": 5}, 
        {"text": "Какие у вас планы?", "energy": "NEUTRAL", "safety": 4}
    ]
```

---

## 📊 МЕТРИКИ И АНАЛИТИКА

### **Отслеживайте эффективность ядра:**

```python
class CoreAnalytics:
    """Аналитика использования ядра"""
    
    def track_question_effectiveness(self, question_id, user_response_quality):
        """Отслеживаем какие вопросы работают лучше"""
        
        question = core.get_question(question_id)
        
        effectiveness_metrics = {
            "question_id": question_id,
            "domain": question["classification"]["domain"],
            "depth": question["classification"]["depth_level"], 
            "energy": question["classification"]["energy_dynamic"],
            
            "user_engagement": user_response_quality["length"] + user_response_quality["emotional_depth"],
            "insight_generation": count_insights_in_response(user_response_quality["text"]),
            "follow_up_questions": user_response_quality["questions_from_user"],
            "emotional_safety": 1.0 - user_response_quality["distress_level"]
        }
        
        # Сохраняем для оптимизации
        save_effectiveness_data(effectiveness_metrics)
    
    def get_most_effective_questions(self, domain=None, user_type=None):
        """Получить самые эффективные вопросы"""
        
        # На основе накопленной статистики
        effective_questions = load_effectiveness_stats()
        
        if domain:
            effective_questions = [q for q in effective_questions if q["domain"] == domain]
        
        if user_type:
            # Фильтруем по типу пользователя (аналитический, эмоциональный, etc)
            effective_questions = [q for q in effective_questions if q["user_type"] == user_type]
        
        return sorted(effective_questions, key=lambda x: x["overall_score"], reverse=True)
```

---

## 🎓 ОБУЧЕНИЕ И АДАПТАЦИЯ

### **Как система должна обучаться:**

```python
def learn_from_interactions(user_interactions_batch):
    """Обучение на основе взаимодействий с пользователями"""
    
    learning_insights = {
        "most_effective_sequences": [],
        "problematic_transitions": [],
        "user_type_preferences": {},
        "energy_flow_optimizations": {}
    }
    
    # Анализируем успешные сессии
    successful_sessions = [s for s in user_interactions_batch if s["outcome"] == "positive"]
    
    for session in successful_sessions:
        # Извлекаем успешные паттерны
        question_sequence = session["questions_asked"]
        user_satisfaction = session["satisfaction_score"]
        
        # Находим эффективные связи
        for i in range(len(question_sequence) - 1):
            current_q = question_sequence[i]
            next_q = question_sequence[i + 1]
            
            transition_effectiveness = session["question_ratings"][i + 1]
            
            if transition_effectiveness > 4.0:  # высокая оценка
                learning_insights["most_effective_sequences"].append({
                    "from": current_q["id"],
                    "to": next_q["id"],
                    "user_type": session["user_vector_snapshot"],
                    "effectiveness": transition_effectiveness
                })
    
    # Применяем обучение к ядру (обновляем веса связей)
    update_connection_weights(learning_insights)
```

---

## 🚀 ГОТОВЫЕ TEMPLATES ДЛЯ БЫСТРОГО СТАРТА

### **Template 1: Быстрая оценка личности (15 минут)**

```python
quick_assessment_template = [
    core.search_questions(domain="IDENTITY", energy="OPENING")[0],      # кто вы
    core.search_questions(domain="EMOTIONS", energy="NEUTRAL")[0],      # эмоциональность  
    core.search_questions(domain="RELATIONSHIPS", energy="OPENING")[0], # отношения
    core.search_questions(domain="WORK", energy="NEUTRAL")[0],          # работа
    core.search_questions(domain="FUTURE", energy="OPENING")[0],        # планы
    core.search_questions(energy="HEALING")[0]                          # завершение
]
```

### **Template 2: Глубокая работа (60+ минут)**

```python
deep_work_template = {
    "preparation": core.search_questions(journey_stage="WARMING", energy="OPENING")[:3],
    "exploration": core.search_questions(journey_stage="EXPLORING", depth_level="CONSCIOUS")[:8], 
    "deepening": core.search_questions(journey_stage="DEEPENING", depth_level="EDGE")[:5],
    "integration": core.search_questions(journey_stage="INTEGRATION", energy="HEALING")[:2]
}
```

### **Template 3: Кризисная поддержка**

```python
crisis_support_template = [
    core.search_questions(energy="HEALING", min_safety=5)[0],           # немедленная поддержка
    core.search_questions(domain="HEALTH", energy="NEUTRAL")[0],        # заземление  
    core.search_questions(domain="CREATIVITY", energy="OPENING")[0],    # ресурс
    core.search_questions(domain="FUTURE", energy="OPENING")[0]         # надежда
]
```

---

## 💡 ПРОФЕССИОНАЛЬНЫЕ СОВЕТЫ

### **1. Начинайте с малого:**
- Первые 5-10 пользователей - используйте простые шаблоны
- Изучайте реакции на разные типы вопросов
- Настраивайте алгоритмы на основе обратной связи

### **2. Мониторьте безопасность:**
- Ведите лог всех HEAVY вопросов и реакций
- Отслеживайте пользователей после глубоких сессий
- Имейте план действий при кризисных ситуациях

### **3. Оптимизируйте производительность:**
- Кешируйте результаты частых поисков
- Предзагружайте связанные вопросы
- Используйте рекомендации моделей для экономии

### **4. Развивайте систему:**
- Добавляйте новые типы связей по мере необходимости
- Расширяйте классификацию доменов
- Обновляйте энергетические правила на основе опыта

---

## ✅ ЧЕКЛИСТ ГОТОВНОСТИ СИСТЕМЫ

Перед запуском убедитесь:

- [ ] Ядро корректно загружается
- [ ] Поиск вопросов работает
- [ ] Граф связей доступен
- [ ] Энергетические правила применяются
- [ ] Есть fallback для всех edge cases
- [ ] Настроен мониторинг безопасности
- [ ] Подготовлены шаблоны для разных сценариев
- [ ] Протестирована интеграция с AI моделями

---

🧠 **Intelligent Question Core предоставляет вам все инструменты для создания максимально эффективной и безопасной системы анализа личности. Используйте его мудро!** ✨