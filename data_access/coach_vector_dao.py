"""
Coach Vector DAO - Специализированные методы Qdrant для ChatCoach

Оптимизировано для:
- Быстрый поиск похожих эмоциональных состояний
- Semantic search по истории эволюции личности
- Similarity matching для персонализации ответов
"""
from typing import Dict, List, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class CoachVectorDAO:
    """
    DAO для работы с векторами в контексте AI Coach

    Коллекции:
    - personality_profiles: текущий профиль (1536D)
    - personality_evolution: история изменений (1536D, ~132 вектора)
    - quick_match: быстрый поиск (512D)
    """

    def __init__(self, qdrant_url: str = "http://localhost:6333"):
        self.client = QdrantClient(url=qdrant_url)
        logger.info(f"✅ CoachVectorDAO connected to Qdrant at {qdrant_url}")

    async def get_current_personality_vector(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Получить ТЕКУЩИЙ вектор личности пользователя

        Коллекция: personality_profiles
        Скорость: < 10ms
        """
        try:
            result = self.client.retrieve(
                collection_name="personality_profiles",
                ids=[user_id],
                with_payload=True,
                with_vectors=True  # Fixed: with_vectors (plural) in new Qdrant API
            )

            if result and len(result) > 0:
                point = result[0]
                logger.info(f"✅ Loaded personality vector for user {user_id}")

                return {
                    "user_id": user_id,
                    "vector": point.vector,
                    "traits": point.payload.get("traits"),
                    "summary": point.payload.get("summary"),
                    "updated_at": point.payload.get("updated_at")
                }

            logger.warning(f"⚠️ No personality vector found for user {user_id}")
            return None

        except Exception as e:
            logger.error(f"❌ Error loading personality vector for user {user_id}: {e}")
            return None

    async def search_similar_emotional_states(
        self,
        user_id: int,
        current_message_vector: List[float],
        limit: int = 10,
        score_threshold: float = 0.65
    ) -> List[Dict[str, Any]]:
        """
        Найти похожие эмоциональные состояния пользователя из истории

        Коллекция: personality_evolution (132 вектора)
        Использование: понять паттерны → релевантный ответ

        Args:
            user_id: ID пользователя
            current_message_vector: вектор текущего сообщения (1536D)
            limit: кол-во похожих состояний (default: 10, оптимизировано AI Engineer review)
            score_threshold: минимальная схожесть 0-1 (default: 0.65 для качественных результатов)

        Returns:
            List похожих моментов с контекстом
        """
        try:
            # Поиск ТОЛЬКО среди векторов ЭТОГО пользователя
            search_result = self.client.search(
                collection_name="personality_evolution",
                query_vector=current_message_vector,
                query_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="user_id",
                            match=models.MatchValue(value=user_id)
                        )
                    ]
                ),
                limit=limit,
                with_payload=True,
                score_threshold=score_threshold  # Оптимизировано: 0.65 вместо 0.5 (AI Engineer review)
            )

            similar_moments = []
            for hit in search_result:
                payload = hit.payload

                similar_moments.append({
                    "similarity_score": hit.score,
                    "snapshot_id": payload.get("snapshot_id"),
                    "created_at": payload.get("created_at"),
                    "narrative": payload.get("personality_snapshot", {}).get("narrative", ""),
                    "big_five": payload.get("personality_snapshot", {}).get("big_five", {}),
                    "trigger_question": payload.get("breakthrough_info", {}).get("trigger_question"),
                    "is_milestone": payload.get("is_milestone", False)
                })

            logger.info(f"🔍 Found {len(similar_moments)} similar states for user {user_id}")
            return similar_moments

        except Exception as e:
            logger.error(f"❌ Error searching similar states for user {user_id}: {e}")
            return []

    async def get_personality_trajectory(
        self,
        user_id: int,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Получить траекторию эволюции личности

        Коллекция: personality_evolution
        Использование: анализ трендов → "ваша открытость растет"

        Returns:
            List векторов истории, отсортированных по времени
        """
        try:
            # Загрузить ВСЕ векторы эволюции пользователя
            scroll_result = self.client.scroll(
                collection_name="personality_evolution",
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="user_id",
                            match=models.MatchValue(value=user_id)
                        )
                    ]
                ),
                limit=limit,
                with_payload=True
            )

            trajectory = []
            if scroll_result and len(scroll_result[0]) > 0:
                for point in scroll_result[0]:
                    payload = point.payload

                    # Используем created_at или updated_at (что есть)
                    timestamp = payload.get("created_at") or payload.get("updated_at")

                    trajectory.append({
                        "snapshot_id": payload.get("snapshot_id"),
                        "created_at": timestamp,
                        "big_five": payload.get("personality_snapshot", {}).get("big_five", {}) or payload.get("traits", {}).get("big_five", {}),
                        "delta_magnitude": payload.get("delta_magnitude", 0),
                        "is_milestone": payload.get("is_milestone", False)
                    })

            # Сортируем по времени (только те что имеют timestamp)
            trajectory = [t for t in trajectory if t["created_at"]]
            trajectory.sort(key=lambda x: x["created_at"])

            logger.info(f"📈 Loaded {len(trajectory)} evolution points for user {user_id}")
            return trajectory

        except Exception as e:
            logger.error(f"❌ Error loading trajectory for user {user_id}: {e}")
            return []

    async def analyze_personality_trajectory(
        self,
        user_id: int,
        window: int = 20
    ) -> Optional[Dict[str, Any]]:
        """
        Анализ трендов личности на основе истории эволюции

        Args:
            user_id: ID пользователя
            window: Сколько последних точек анализировать

        Returns:
            Dict с трендами и инсайтами

        Пример:
            {
                "trends": {
                    "openness": {"change": +0.25, "direction": "growing"},
                    "conscientiousness": {"change": -0.15, "direction": "declining"}
                },
                "insights": [
                    "Ваша открытость новому растет (+0.25)",
                    "Структурированность снижается - возможно стоит добавить планирование"
                ],
                "momentum": "positive",
                "volatility": "low"
            }
        """
        try:
            # Загружаем траекторию
            trajectory = await self.get_personality_trajectory(user_id, limit=window)

            if len(trajectory) < 2:
                logger.warning(f"⚠️ Not enough data for trajectory analysis (need 2+, got {len(trajectory)})")
                return None

            # Анализируем каждую черту Big Five
            traits = ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]
            trends = {}
            insights = []

            for trait in traits:
                # Получаем значения во времени
                values = [
                    point["big_five"].get(trait, 0.5)
                    for point in trajectory
                    if point.get("big_five")
                ]

                if len(values) < 2:
                    continue

                # Вычисляем тренд
                first_value = values[0]
                last_value = values[-1]
                change = last_value - first_value

                # Определяем направление
                if abs(change) < 0.05:
                    direction = "stable"
                elif change > 0:
                    direction = "growing"
                else:
                    direction = "declining"

                trends[trait] = {
                    "change": round(change, 2),
                    "direction": direction,
                    "current_value": round(last_value, 2),
                    "volatility": round(self._calculate_volatility(values), 2)
                }

                # Генерируем инсайты для значительных изменений
                if abs(change) >= 0.10:
                    insight = self._generate_trait_insight(trait, change, direction, last_value)
                    if insight:
                        insights.append(insight)

            # Общий momentum (положительный/отрицательный)
            total_change = sum(t["change"] for t in trends.values())
            momentum = "positive" if total_change > 0 else "negative" if total_change < 0 else "neutral"

            # Средняя волатильность
            avg_volatility = sum(t["volatility"] for t in trends.values()) / len(trends) if trends else 0
            volatility = "high" if avg_volatility > 0.15 else "low" if avg_volatility < 0.05 else "medium"

            logger.info(f"📊 Trajectory analysis: {len(insights)} insights, momentum: {momentum}")

            return {
                "trends": trends,
                "insights": insights,
                "momentum": momentum,
                "volatility": volatility,
                "data_points": len(trajectory),
                "time_span": f"{trajectory[0]['created_at'][:10]} → {trajectory[-1]['created_at'][:10]}"
            }

        except Exception as e:
            logger.error(f"❌ Error analyzing trajectory for user {user_id}: {e}")
            return None

    def _calculate_volatility(self, values: List[float]) -> float:
        """Вычислить волатильность (стандартное отклонение)"""
        if len(values) < 2:
            return 0.0

        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5

    def _generate_trait_insight(self, trait: str, change: float, direction: str, current_value: float) -> Optional[str]:
        """Сгенерировать человеческий инсайт о тренде черты"""

        trait_names = {
            "openness": "открытость новому",
            "conscientiousness": "организованность",
            "extraversion": "общительность",
            "agreeableness": "доброжелательность",
            "neuroticism": "эмоциональная нестабильность"
        }

        trait_ru = trait_names.get(trait, trait)

        # 🔥 FIX: Конвертируем delta в проценты
        change_percent = int(abs(change) * 100)

        # 🔥 FIX: Понятное описание величины
        if abs(change) > 0.30:
            magnitude = "значительно"
        elif abs(change) > 0.20:
            magnitude = "заметно"
        else:
            magnitude = "немного"

        if direction == "growing" and abs(change) >= 0.10:
            if trait == "openness":
                return f"Ваша {trait_ru} {magnitude} растет (на {change_percent}%) - вы становитесь более гибким и открытым к новым идеям"
            elif trait == "conscientiousness":
                return f"Ваша {trait_ru} {magnitude} растет (на {change_percent}%) - вы становитесь более структурированным и целенаправленным"
            elif trait == "extraversion":
                return f"Ваша {trait_ru} {magnitude} растет (на {change_percent}%) - вы становитесь более социально активным"
            elif trait == "neuroticism" and change > 0.15:
                return f"Замечаю рост эмоциональной нестабильности (на {change_percent}%) - возможно стоит обратить внимание на стресс"

        elif direction == "declining" and abs(change) >= 0.10:
            if trait == "conscientiousness":
                return f"Организованность {magnitude} снижается (на {change_percent}%) - возможно стоит добавить больше структуры"
            elif trait == "neuroticism" and change < -0.15:
                return f"Эмоциональная стабильность {magnitude} улучшается (на {change_percent}%) - отличная динамика!"
            elif trait == "openness":
                return f"Открытость новому {magnitude} снижается (на {change_percent}%) - может быть стоит добавить экспериментов?"

        return None

    async def find_similar_users(
        self,
        user_id: int,
        limit: int = 10,
        score_threshold: float = 0.75
    ) -> List[Dict[str, Any]]:
        """
        Найти похожих пользователей (similarity matching)

        Коллекция: personality_profiles
        Использование: "люди с похожим профилем находят помощь в..."

        Returns:
            List похожих пользователей с scores
        """
        try:
            # Получаем вектор текущего пользователя
            current_user = await self.get_current_personality_vector(user_id)
            if not current_user:
                return []

            # Ищем похожих
            search_result = self.client.search(
                collection_name="personality_profiles",
                query_vector=current_user["vector"],
                limit=limit + 1,  # +1 чтобы исключить себя
                score_threshold=score_threshold,
                with_payload=True
            )

            similar_users = []
            for hit in search_result:
                hit_user_id = hit.payload.get("user_id")

                # Исключаем себя
                if hit_user_id == user_id:
                    continue

                similar_users.append({
                    "user_id": hit_user_id,
                    "similarity_score": hit.score,
                    "big_five": hit.payload.get("traits", {}).get("big_five", {}),
                    "archetype": self._determine_archetype(hit.payload.get("traits", {}))
                })

            logger.info(f"👥 Found {len(similar_users)} similar users for {user_id}")
            return similar_users

        except Exception as e:
            logger.error(f"❌ Error finding similar users for {user_id}: {e}")
            return []

    def _determine_archetype(self, traits: Dict) -> str:
        """Определить архетип личности из Big Five"""
        big_five = traits.get("big_five", {})

        o = big_five.get("openness", 0.5)
        c = big_five.get("conscientiousness", 0.5)
        e = big_five.get("extraversion", 0.5)

        if o > 0.7 and e < 0.5:
            return "Мудрый Созерцатель"
        elif o > 0.7 and e > 0.6:
            return "Вдохновляющий Творец"
        elif c > 0.7:
            return "Надежный Организатор"
        elif e > 0.7:
            return "Теплый Коммуникатор"
        else:
            return "Гармоничная Личность"

    async def health_check(self) -> Dict[str, Any]:
        """Проверка подключения к Qdrant"""
        try:
            collections = self.client.get_collections()
            collection_names = [c.name for c in collections.collections]

            stats = {}
            for name in ["personality_profiles", "personality_evolution", "quick_match"]:
                if name in collection_names:
                    info = self.client.get_collection(name)
                    stats[name] = {
                        "points_count": info.points_count,
                        "status": info.status
                    }

            return {
                "status": "healthy",
                "collections": stats
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
