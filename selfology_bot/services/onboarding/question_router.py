"""
QuestionRouter - Умный выбор вопросов

Алгоритм "Умный Микс":
1. Психологический Градиент (безопасность)
2. Мозаичное Картирование (охват доменов)
3. Адаптивный Детектив (персонализация)
4. Энергетический Серфинг (управление состоянием)
5. Все вместе = оптимальный баланс охвата/интереса/безопасности
"""

import logging
import random
from typing import Dict, List, Any, Optional
from enum import Enum
import sys
from pathlib import Path

# Добавляем путь к Question Core
sys.path.append(str(Path(__file__).parent.parent.parent.parent / "intelligent_question_core"))

from intelligent_question_core.api.core_api import SelfologyQuestionCore
from core.error_collector import error_collector

logger = logging.getLogger(__name__)

class RouterStrategy(Enum):
    """Стратегии роутинга для разных этапов"""
    ENTRY = "entry"           # Безопасное начало
    EXPLORATION = "exploration"  # Охват доменов
    DEEPENING = "deepening"      # Углубление
    BALANCING = "balancing"      # Энергетический баланс
    FOLLOWUP = "followup"        # Контекстный уточняющий вопрос

class QuestionRouter:
    """
    Умный роутер вопросов с алгоритмом "Умный Микс"
    
    Комбинирует 4 подхода:
    - Градиентное углубление (безопасность)
    - Мозаичное картирование (охват)  
    - Адаптивная персонализация (интерес)
    - Энергетический серфинг (состояние)
    """
    
    def __init__(self, question_core: SelfologyQuestionCore, onboarding_dao=None):
        """
        Инициализация роутера

        Args:
            question_core: Инициализированное ядро вопросов
            onboarding_dao: DAO для работы с БД (опционально)
        """
        self.core = question_core
        self.onboarding_dao = onboarding_dao
        self.last_events = []  # События последнего вызова select_next_question

        # Основные домены для мозаичного картирования
        self.core_domains = [
            "IDENTITY", "RELATIONSHIPS", "WORK", "EMOTIONS",
            "MONEY", "HEALTH", "CREATIVITY", "SPIRITUALITY"
        ]

        # Правила безопасности
        self.safety_rules = {
            "max_heavy_per_session": 2,
            "no_heavy_after_heavy": True,
            "always_end_with_healing": True,
            "min_trust_for_shadow": 4
        }

        # 💙 Системный вопрос о контексте (3 формулировки)
        self.CONTEXT_STORY_QUESTION = {
            "id": "system_context_story",
            "type": "system",
            "text": "Если хотите, расскажите что-то важное о себе — то, что обычно не попадает в анкеты, но помогло бы мне лучше вас понять. Это может быть что угодно или ничего — как вам комфортнее 💙",
            "classification": {
                "domain": "SYSTEM",
                "depth_level": "META",
                "energy_dynamic": "OPENING"
            },
            "psychology": {
                "complexity": 3,
                "emotional_weight": 2,
                "insight_potential": 5,
                "trust_requirement": 3,
                "safety_level": 4
            },
            "variants": {
                "gentle": "Иногда помогает рассказать о том, что важно для вас. Но только если чувствуете готовность 💙",
                "neutral": "Если хотите, расскажите что-то важное о себе — то, что обычно не попадает в анкеты, но помогло бы мне лучше вас понять. Это может быть что угодно или ничего — как вам комфортнее 💙",
                "casual": "Может, появилось что-то новое, чем хотите поделиться? Или всё по-прежнему — тоже нормально 😊"
            }
        }

        logger.info("🎯 QuestionRouter initialized with Smart Mix algorithm")

    def _track_event(self, event_type: str, **kwargs):
        """Отслеживание событий роутера для аналитики"""
        event = {"type": event_type, **kwargs}
        self.last_events.append(event)

    async def select_first_question(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Выбрать первый вопрос (всегда безопасный и вдохновляющий)

        Args:
            user_id: ID пользователя

        Returns:
            Данные первого вопроса или None
        """
        try:
            logger.info(f"🚀 Selecting FIRST question for user {user_id}")

            # Упрощенный выбор первого вопроса - берем любой безопасный
            candidates = self.core.search_questions(min_safety=3)
            logger.info(f"🔍 Found {len(candidates)} safe candidates")

            if not candidates:
                # Последний fallback - вообще любые
                candidates = self.core.search_questions()
                logger.warning(f"⚠️ Using any questions: {len(candidates)}")

            if not candidates:
                logger.error(f"❌ No questions available at all!")
                return None

            # ✅ Фильтруем flagged вопросы из БД
            filtered = await self._filter_flagged_questions(candidates)

            if not filtered:
                logger.warning(f"⚠️ All first questions are flagged")
                return candidates[0]  # Берем любой если все помечены

            # Выбираем случайный из подходящих
            selected = random.choice(filtered)

            logger.info(f"✅ First question selected: {selected['id']} ({selected['classification']['domain']})")
            return selected

        except Exception as e:
            logger.error(f"❌ Error selecting first question for user {user_id}: {e}")
            await error_collector.collect(
                error=e,
                service="QuestionRouter",
                component="select_first_question",
                user_id=user_id
            )
            return None
    
    async def select_next_question(self, user_id: int, session_history: List[Dict], session_id: int = None) -> Optional[Dict[str, Any]]:
        """
        Выбрать следующий вопрос используя алгоритм "Умный Микс"

        Args:
            user_id: ID пользователя
            session_history: История ответов в текущей сессии
            session_id: ID сессии для загрузки AI insights (опционально)

        Returns:
            Следующий вопрос или None если сессия должна завершиться
        """
        try:
            # Очищаем события предыдущего вызова
            self.last_events = []

            logger.info(f"🎯 Selecting NEXT question for user {user_id} (history: {len(session_history)})")

            # Загружаем ВСЕ отвеченные вопросы пользователя из ВСЕХ сессий (не только текущей!)
            if self.onboarding_dao:
                asked_question_ids = set(await self.onboarding_dao.get_user_answered_questions(user_id))
                logger.info(f"🚫 Excluding {len(asked_question_ids)} already asked questions (from ALL sessions)")
                logger.info(f"🔍 DEBUG: system_context_story in asked_questions = {'system_context_story' in asked_question_ids}")
            else:
                # Fallback: только из текущей сессии если DAO недоступен
                asked_question_ids = set()
                for item in session_history:
                    question = item.get('question', {})
                    if 'id' in question:
                        asked_question_ids.add(question['id'])
                logger.info(f"🚫 Excluding {len(asked_question_ids)} already asked questions (current session only)")

            # ✅ КРИТИЧНО: Добавляем пропущенные вопросы из ТЕКУЩЕЙ сессии (они есть в памяти но не в БД)
            skipped_in_session = 0
            for item in session_history:
                question = item.get('question', {})
                answer = item.get('answer', {})
                if question.get('id') and answer.get('skipped'):
                    asked_question_ids.add(question['id'])
                    skipped_in_session += 1

            if skipped_in_session > 0:
                logger.info(f"⏭️ Added {skipped_in_session} skipped questions from current session to exclusion list")

            # ✨ НОВОЕ: Загружаем AI insights из БД
            ai_insights = []
            if session_id and self.onboarding_dao:
                try:
                    ai_insights = await self.onboarding_dao.get_session_analysis_insights(session_id)
                    if ai_insights:
                        logger.info(f"🧠 Loaded {len(ai_insights)} AI insights for personalization")
                except Exception as e:
                    logger.warning(f"⚠️ Could not load AI insights: {e}")

            # Анализируем историю сессии (с AI insights)
            session_analysis = self._analyze_session_history(session_history, ai_insights)
            session_analysis['asked_question_ids'] = asked_question_ids  # Добавляем в анализ

            # 💙 ПРОВЕРКА: Нужно ли показать системный вопрос о контексте?
            # Проверяем только если его еще не задавали В ТЕКУЩЕЙ СЕССИИ (не глобально!)
            system_context_in_current_session = any(
                item.get('question', {}).get('id') == 'system_context_story'
                for item in session_history
            )
            if not system_context_in_current_session:
                if self._should_show_context_story(session_analysis):
                    variant_key = self._select_context_story_variant(session_analysis)
                    context_question = self._create_context_story_question(variant_key)

                    self._track_event("context_story_shown", variant=variant_key, question_count=session_analysis.get("question_count"))
                    logger.info(f"💙 Showing context story question (variant: {variant_key})")

                    return context_question

            # Определяем стратегию на основе прогресса
            strategy = self._determine_strategy(session_analysis)
            self._track_event("strategy_selected", strategy=strategy.value, question_count=len(session_history))

            # Получаем кандидатов по стратегии
            candidates = self._get_candidates_by_strategy(strategy, session_analysis)
            self._track_event("candidates_found", strategy=strategy.value, candidate_count=len(candidates))

            # Фильтруем уже заданные вопросы
            candidates = [q for q in candidates if q['id'] not in asked_question_ids]
            logger.info(f"📋 After filtering duplicates: {len(candidates)} candidates remain")

            # ✅ Применяем правила безопасности (включая фильтрацию flagged вопросов)
            safe_candidates = await self._apply_safety_rules(candidates, session_analysis)

            # Финальная персонализация
            final_question = self._personalize_selection(safe_candidates, session_analysis)

            # 🚨 АВАРИЙНЫЙ FALLBACK - если все стратегии провалились
            if not final_question:
                logger.warning(f"🚨 No candidates found - using emergency fallback (any question)")
                self._track_event("fallback_used", reason="no_candidates", strategy=strategy.value)
                all_questions = self.core.search_questions()  # Берем ВСЕ вопросы
                # Фильтруем уже заданные вопросы
                available_questions = [q for q in all_questions if q['id'] not in asked_question_ids]
                if available_questions:
                    final_question = available_questions[0]  # Первый доступный
                    logger.info(f"🆘 Emergency fallback: selected {final_question['id']}")
                else:
                    logger.error(f"❌ CRITICAL: All questions already asked!")

            if final_question:
                logger.info(f"✅ Next question selected: {final_question['id']} (strategy: {strategy.value})")
            else:
                logger.error(f"❌ CRITICAL: No questions available at all!")

            return final_question

        except Exception as e:
            logger.exception(f"❌ Error selecting next question for user {user_id}: {e}")
            await error_collector.collect(
                error=e,
                service="QuestionRouter",
                component="select_next_question",
                user_id=user_id,
                context={"history_length": len(session_history), "session_id": session_id}
            )
            return None
    
    def _analyze_session_history(self, history: List[Dict], ai_insights: List[Dict] = None) -> Dict[str, Any]:
        """
        Анализ истории сессии для принятия решений

        Args:
            history: История вопросов и ответов
            ai_insights: AI анализ ответов (опционально)

        Returns:
            Анализ сессии
        """
        if not history:
            return {
                "question_count": 0,
                "domains_covered": set(),
                "depth_progression": [],
                "energy_levels": [],
                "heavy_question_count": 0,
                "last_energy": None,
                "domain_balance": {},
                "engagement_level": 1.0,
                "ai_insights": [],
                "last_special_situation": None,
                "domain_interest_scores": {}
            }

        domains_covered = set()
        depth_levels = []
        energy_levels = []
        heavy_count = 0

        for item in history:
            question = item.get('question', {})
            classification = question.get('classification', {})

            domain = classification.get('domain')
            depth = classification.get('depth_level')
            energy = classification.get('energy_dynamic')

            if domain:
                domains_covered.add(domain)
            if depth:
                depth_levels.append(depth)
            if energy:
                energy_levels.append(energy)
                if energy == "HEAVY":
                    heavy_count += 1

        # Баланс доменов
        domain_counts = {}
        for domain in domains_covered:
            domain_counts[domain] = sum(1 for item in history
                                      if item.get('question', {}).get('classification', {}).get('domain') == domain)

        # ✨ НОВОЕ: Анализ интересов на основе AI insights
        domain_interest_scores = {}
        last_special_situation = None

        if ai_insights:
            # Считаем "интересность" каждого домена
            for insight in ai_insights:
                domain = insight.get('domain')
                if domain:
                    if domain not in domain_interest_scores:
                        domain_interest_scores[domain] = {'quality': 0, 'emotion': 0, 'count': 0}

                    # Качество ответа
                    domain_interest_scores[domain]['quality'] += insight.get('quality_score', 0)
                    # Эмоциональность
                    if insight.get('emotional_state') in ['excited', 'passionate', 'deeply_moved', 'hopeful']:
                        domain_interest_scores[domain]['emotion'] += 1
                    domain_interest_scores[domain]['count'] += 1

            # Усредняем баллы
            for domain in domain_interest_scores:
                count = domain_interest_scores[domain]['count']
                domain_interest_scores[domain]['avg_quality'] = domain_interest_scores[domain]['quality'] / count
                domain_interest_scores[domain]['emotion_rate'] = domain_interest_scores[domain]['emotion'] / count

            # Последняя спецситуация (для follow-up)
            if ai_insights:
                last_special_situation = ai_insights[-1].get('special_situation')

        return {
            "question_count": len(history),
            "domains_covered": domains_covered,
            "depth_progression": depth_levels,
            "energy_levels": energy_levels,
            "heavy_question_count": heavy_count,
            "last_energy": energy_levels[-1] if energy_levels else None,
            "domain_balance": domain_counts,
            "engagement_level": self._calculate_engagement(history, ai_insights),
            "ai_insights": ai_insights or [],
            "last_special_situation": last_special_situation,
            "domain_interest_scores": domain_interest_scores
        }
    
    def _determine_strategy(self, analysis: Dict[str, Any]) -> RouterStrategy:
        """
        Определить стратегию роутинга на основе анализа

        Args:
            analysis: Анализ сессии

        Returns:
            Стратегия для выбора следующего вопроса
        """
        count = analysis["question_count"]
        domains_covered = len(analysis["domains_covered"])
        last_energy = analysis["last_energy"]
        last_special_situation = analysis.get("last_special_situation")

        # ✨ НОВЫЙ ПРИОРИТЕТ: Follow-up при кризисе или прорыве
        if last_special_situation in ['crisis', 'breakthrough']:
            logger.info(f"📊 Strategy: FOLLOWUP (after {last_special_situation})")
            return RouterStrategy.FOLLOWUP

        # Энергетический баланс (второй приоритет)
        if last_energy == "HEAVY":
            logger.info("📊 Strategy: BALANCING (after heavy question)")
            return RouterStrategy.BALANCING

        # Начальное исследование (1-3 вопроса)
        if count <= 3:
            logger.info("📊 Strategy: ENTRY (early questions)")
            return RouterStrategy.ENTRY

        # Мозаичное картирование (4-8 вопросов, мало доменов)
        if count <= 8 and domains_covered < 4:
            logger.info("📊 Strategy: EXPLORATION (domain mapping)")
            return RouterStrategy.EXPLORATION

        # Углубление (много вопросов, хорошее покрытие доменов)
        logger.info("📊 Strategy: DEEPENING (going deeper)")
        return RouterStrategy.DEEPENING
    
    def _get_candidates_by_strategy(self, strategy: RouterStrategy, analysis: Dict[str, Any]) -> List[Dict]:
        """
        Получить кандидатов по выбранной стратегии
        
        Args:
            strategy: Стратегия роутинга
            analysis: Анализ сессии
            
        Returns:
            Список кандидатов
        """
        candidates = []
        
        try:
            if strategy == RouterStrategy.ENTRY:
                # Безопасные начальные вопросы
                candidates = self.core.search_questions(
                    energy="OPENING",
                    depth_level="SURFACE",
                    min_safety=4
                )
                if not candidates:
                    candidates = self.core.search_questions(
                        energy="NEUTRAL", 
                        depth_level="SURFACE"
                    )
                
            elif strategy == RouterStrategy.EXPLORATION:
                # Разные домены, которые еще не покрыты
                uncovered_domains = set(self.core_domains) - analysis["domains_covered"]
                if uncovered_domains:
                    for domain in list(uncovered_domains)[:3]:  # Максимум 3 новых домена
                        domain_questions = self.core.search_questions(
                            domain=domain,
                            depth_level="CONSCIOUS"
                        )
                        candidates.extend(domain_questions)
                else:
                    # Все основные домены покрыты, берем средние вопросы
                    candidates = self.core.search_questions(
                        depth_level="CONSCIOUS"
                    )
                    
            elif strategy == RouterStrategy.DEEPENING:
                # Углубляем в уже затронутых доменах
                covered_domains = list(analysis["domains_covered"])[:2]  # Топ-2 домена
                for domain in covered_domains:
                    deep_questions = self.core.search_questions(
                        domain=domain,
                        depth_level="EDGE"
                    )
                    candidates.extend(deep_questions)
                    
            elif strategy == RouterStrategy.BALANCING:
                # После HEAVY - только спокойные вопросы
                candidates = self.core.search_questions(
                    energy="NEUTRAL",
                    depth_level="SURFACE",
                    min_safety=4
                )

            elif strategy == RouterStrategy.FOLLOWUP:
                # ✨ НОВОЕ: Контекстный follow-up вопрос
                # Берем домен последнего вопроса с crisis/breakthrough
                if analysis.get("ai_insights"):
                    last_insight = analysis["ai_insights"][-1]
                    last_domain = last_insight.get('domain')
                    last_situation = analysis.get("last_special_situation")

                    if last_domain:
                        if last_situation == 'crisis':
                            # При кризисе - поддерживающие вопросы
                            candidates = self.core.search_questions(
                                domain=last_domain,
                                energy="HEALING",
                                depth_level="CONSCIOUS"
                            )
                            logger.info(f"🆘 Follow-up after crisis in {last_domain}")
                        elif last_situation == 'breakthrough':
                            # При прорыве - углубляющие вопросы
                            candidates = self.core.search_questions(
                                domain=last_domain,
                                depth_level="EDGE"
                            )
                            logger.info(f"🌟 Follow-up after breakthrough in {last_domain}")

                # Fallback если нет insights
                if not candidates:
                    candidates = self.core.search_questions(depth_level="CONSCIOUS")

        except Exception as e:
            logger.error(f"❌ Error getting candidates for strategy {strategy}: {e}")
            # Не используем await здесь т.к. метод синхронный - логируем синхронно
            # Fallback - любые безопасные вопросы
            candidates = self.core.search_questions(min_safety=3)
        
        # КРИТИЧНЫЙ FALLBACK - если все равно нет кандидатов
        if not candidates:
            logger.warning(f"🚨 No candidates for {strategy.value} - using emergency fallback")
            candidates = self.core.search_questions()  # Любые вопросы
        
        logger.info(f"📊 Strategy {strategy.value}: {len(candidates)} candidates found")
        return candidates
    
    async def _apply_safety_rules(self, candidates: List[Dict], analysis: Dict[str, Any]) -> List[Dict]:
        """
        Применить правила психологической безопасности

        Args:
            candidates: Кандидаты для выбора
            analysis: Анализ сессии

        Returns:
            Отфильтрованные безопасные кандидаты
        """
        safe_candidates = []

        for question in candidates:
            classification = question.get('classification', {})
            energy = classification.get('energy_dynamic')
            depth = classification.get('depth_level')

            # Правило: не более 2 HEAVY за сессию
            if (energy == "HEAVY" and
                analysis['heavy_question_count'] >= self.safety_rules['max_heavy_per_session']):
                continue

            # Правило: не HEAVY после HEAVY
            if (energy == "HEAVY" and
                analysis['last_energy'] == "HEAVY" and
                self.safety_rules['no_heavy_after_heavy']):
                continue

            # Правило: SHADOW только при высоком доверии
            if (depth == "SHADOW" and
                analysis.get('engagement_level', 0) < self.safety_rules['min_trust_for_shadow']):
                continue

            safe_candidates.append(question)

        # ✅ Фильтруем flagged вопросы из БД
        final_candidates = await self._filter_flagged_questions(safe_candidates)

        logger.info(f"🛡️ Safety filter: {len(candidates)} → {len(final_candidates)} candidates")
        return final_candidates
    
    def _personalize_selection(self, candidates: List[Dict], analysis: Dict[str, Any]) -> Optional[Dict]:
        """
        Финальная персонализация выбора

        Args:
            candidates: Отфильтрованные кандидаты
            analysis: Анализ сессии

        Returns:
            Финальный выбранный вопрос
        """
        if not candidates:
            return None

        if len(candidates) == 1:
            return candidates[0]

        # ✨ УЛУЧШЕННАЯ ЛОГИКА: учитываем интересы пользователя
        domain_scores = {}
        domain_interest_scores = analysis.get('domain_interest_scores', {})

        for question in candidates:
            domain = question.get('classification', {}).get('domain')
            if not domain:
                continue

            # Базовая оценка: чем меньше вопросов, тем выше приоритет
            domain_count = analysis['domain_balance'].get(domain, 0)
            base_score = 10 - domain_count

            # ✨ НОВОЕ: Бонус за интерес пользователя
            interest_bonus = 0
            if domain in domain_interest_scores:
                scores = domain_interest_scores[domain]
                # Высокое качество ответов = интересная тема (+3)
                if scores.get('avg_quality', 0) > 0.7:
                    interest_bonus += 3
                elif scores.get('avg_quality', 0) > 0.5:
                    interest_bonus += 1.5

                # Эмоциональные ответы = вовлекающая тема (+2)
                if scores.get('emotion_rate', 0) > 0.5:
                    interest_bonus += 2
                elif scores.get('emotion_rate', 0) > 0.3:
                    interest_bonus += 1

            final_score = base_score + interest_bonus

            if domain not in domain_scores or final_score > domain_scores[domain]['score']:
                domain_scores[domain] = {
                    'score': final_score,
                    'base_score': base_score,
                    'interest_bonus': interest_bonus,
                    'question': question
                }

        if domain_scores:
            # Выбираем домен с наивысшим приоритетом
            best_domain = max(domain_scores.keys(), key=lambda d: domain_scores[d]['score'])
            selected = domain_scores[best_domain]['question']

            logger.info(
                f"🎯 Personalized selection: domain {best_domain} "
                f"(base={domain_scores[best_domain]['base_score']:.1f}, "
                f"interest={domain_scores[best_domain]['interest_bonus']:.1f}, "
                f"total={domain_scores[best_domain]['score']:.1f})"
            )
            return selected

        # Fallback - случайный выбор
        return random.choice(candidates)
    
    def _calculate_engagement(self, history: List[Dict], ai_insights: List[Dict] = None) -> float:
        """
        Рассчитать уровень вовлеченности пользователя

        Args:
            history: История ответов
            ai_insights: AI анализ ответов (опционально)

        Returns:
            Уровень вовлеченности (0-5)
        """
        if not history:
            return 1.0

        # Базовый расчет по длине ответов
        total_length = 0
        answer_count = 0

        for item in history:
            answer_text = item.get('answer', {})
            if isinstance(answer_text, dict):
                answer_text = answer_text.get('answer', '')
            if answer_text:
                total_length += len(answer_text)
                answer_count += 1

        if answer_count == 0:
            return 1.0

        avg_length = total_length / answer_count

        # Базовая оценка по длине
        if avg_length < 10:
            base_score = 1.0
        elif avg_length < 50:
            base_score = 2.5
        elif avg_length < 100:
            base_score = 4.0
        else:
            base_score = 5.0

        # ✨ НОВОЕ: Улучшаем оценку на основе AI анализа
        if ai_insights and len(ai_insights) > 0:
            # Считаем средние показатели качества
            total_quality = 0
            total_confidence = 0
            has_breakthrough = False
            strong_emotions = 0

            for insight in ai_insights:
                total_quality += insight.get('quality_score', 0)
                total_confidence += insight.get('confidence_score', 0)

                # Прорывы и сильные эмоции повышают вовлеченность
                if insight.get('special_situation') == 'breakthrough':
                    has_breakthrough = True

                emotional_state = (insight.get('emotional_state') or '').lower()
                if emotional_state in ['excited', 'passionate', 'deeply_moved', 'hopeful']:
                    strong_emotions += 1

            avg_quality = total_quality / len(ai_insights)
            avg_confidence = total_confidence / len(ai_insights)

            # Корректируем базовую оценку
            ai_bonus = 0

            # Бонус за качество ответов (макс +1.0)
            if avg_quality > 0.7:
                ai_bonus += 0.5
            elif avg_quality > 0.5:
                ai_bonus += 0.3

            # Бонус за уверенность (макс +0.5)
            if avg_confidence > 0.7:
                ai_bonus += 0.3
            elif avg_confidence > 0.5:
                ai_bonus += 0.2

            # Бонус за прорывы и эмоции (макс +0.5)
            if has_breakthrough:
                ai_bonus += 0.3
            if strong_emotions > len(ai_insights) * 0.3:  # >30% ответов эмоциональны
                ai_bonus += 0.2

            final_score = min(5.0, base_score + ai_bonus)
            logger.debug(f"📊 Engagement: base={base_score:.1f}, AI bonus={ai_bonus:.1f}, final={final_score:.1f}")
            return final_score

        return base_score

    def _should_show_context_story(self, session_analysis: Dict) -> bool:
        """
        Проверка нужно ли показать системный вопрос о контексте

        Показываем если:
        - Вопросы 1-5: engagement >= 3.0 ИЛИ emotional_answers >= 1
        - Вопрос 6: ОБЯЗАТЕЛЬНО (если ещё не показывали)

        Args:
            session_analysis: Анализ текущей сессии

        Returns:
            True если нужно показать вопрос
        """
        question_count = session_analysis.get("question_count", 0)
        engagement = session_analysis.get("engagement_level", 0)

        # Считаем эмоциональные ответы
        emotional_count = 0
        ai_insights = session_analysis.get("ai_insights", [])
        for insight in ai_insights:
            emotional = insight.get("emotional_state", "")
            if emotional and emotional != "neutral":
                emotional_count += 1

        logger.info(f"🔍 Context story check: Q{question_count}, engagement={engagement:.1f}, emotions={emotional_count}")

        # Вопросы 1-5: показываем если готов
        if 1 <= question_count <= 5:
            ready = (question_count >= 3 and engagement >= 3.0) or (emotional_count >= 1)
            if ready:
                logger.info(f"💙 Context story ready: Q{question_count}, engagement={engagement:.1f}, emotions={emotional_count}")
                return True
            else:
                logger.info(f"⏸️ Context story NOT ready: Q{question_count}, engagement={engagement:.1f} < 3.0, emotions={emotional_count} < 1")

        # Вопрос 6: ОБЯЗАТЕЛЬНО показываем
        elif question_count == 6:
            logger.info(f"💙 Context story MANDATORY at Q6")
            return True

        # После вопроса 6 - не показываем
        else:
            logger.info(f"⏭️ Context story skipped: Q{question_count} > 6")

        return False

    def _select_context_story_variant(self, session_analysis: Dict) -> str:
        """
        Выбрать формулировку системного вопроса по состоянию пользователя

        Args:
            session_analysis: Анализ текущей сессии

        Returns:
            Ключ варианта: 'gentle', 'neutral', 'casual'
        """
        engagement = session_analysis.get("engagement_level", 0)

        # Считаем эмоциональные ответы и пропуски
        emotional_count = 0
        ai_insights = session_analysis.get("ai_insights", [])
        for insight in ai_insights:
            emotional = insight.get("emotional_state", "")
            if emotional and emotional != "neutral":
                emotional_count += 1

        # Подсчёт пропусков из истории
        skip_count = 0
        # TODO: добавить подсчёт пропусков когда будет доступна информация

        # Формулировка 3: закрытый/тревожный (gentle)
        if engagement < 2.5 or emotional_count == 0 or skip_count >= 2:
            logger.info(f"💙 Context variant: GENTLE (engagement={engagement:.1f}, emotions={emotional_count}, skips={skip_count})")
            return "gentle"

        # Формулировка 2: открытый/активный (casual)
        elif engagement > 3.5 and emotional_count >= 2:
            logger.info(f"💙 Context variant: CASUAL (engagement={engagement:.1f}, emotions={emotional_count})")
            return "casual"

        # Формулировка 1: средний/сдержанный (neutral) - дефолт
        else:
            logger.info(f"💙 Context variant: NEUTRAL (engagement={engagement:.1f}, emotions={emotional_count})")
            return "neutral"

    def _create_context_story_question(self, variant_key: str) -> Dict[str, Any]:
        """
        Создать системный вопрос о контексте с выбранной формулировкой

        Args:
            variant_key: Ключ варианта ('gentle', 'neutral', 'casual')

        Returns:
            Объект вопроса для отображения
        """
        question = self.CONTEXT_STORY_QUESTION.copy()
        question["text"] = question["variants"][variant_key]
        question["selected_variant"] = variant_key

        return question

    async def _filter_flagged_questions(self, questions: List[Dict]) -> List[Dict]:
        """
        Фильтровать вопросы с флагом "на доработку"

        Args:
            questions: Список вопросов

        Returns:
            Отфильтрованный список без flagged вопросов
        """
        # Если DAO не подключен, возвращаем все вопросы
        if not self.onboarding_dao:
            logger.warning("⚠️ OnboardingDAO not available - cannot filter flagged questions")
            return questions

        try:
            # Получаем set ID помеченных вопросов из БД
            flagged_ids = await self.onboarding_dao.get_flagged_question_ids()

            if not flagged_ids:
                # Нет помеченных вопросов - возвращаем все
                return questions

            # Фильтруем помеченные вопросы
            filtered = [q for q in questions if q['id'] not in flagged_ids]

            if len(filtered) < len(questions):
                removed_count = len(questions) - len(filtered)
                logger.info(f"🚩 Filtered out {removed_count} flagged questions")
                self._track_event("flagged_filtered", count=removed_count, total=len(questions))

            return filtered

        except Exception as e:
            logger.error(f"❌ Error filtering flagged questions: {e}")
            await error_collector.collect(
                error=e,
                service="QuestionRouter",
                component="_filter_flagged_questions",
                context={"questions_count": len(questions)}
            )
            # В случае ошибки - возвращаем все вопросы (безопасный fallback)
            return questions